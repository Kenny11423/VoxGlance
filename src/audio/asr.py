import ctypes
import glob
import os
import sys
import time
from typing import Generator, List, Optional
import numpy as np
from loguru import logger

from src.core.ipc import SubtitleToken
from src.core.memory import MemoryController


def _preload_nvidia_libs() -> None:
    """Preload bundled NVIDIA CUDA/cuDNN/cuBLAS shared libraries."""
    try:
        for p in sys.path:
            if "site-packages" in p:
                for lib_dir in glob.glob(os.path.join(p, "nvidia", "*", "lib")):
                    if os.path.isdir(lib_dir):
                        if lib_dir not in os.environ.get("LD_LIBRARY_PATH", ""):
                            os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"
                        for fname in sorted(os.listdir(lib_dir)):
                            if fname.endswith(".so") or ".so." in fname:
                                try:
                                    ctypes.CDLL(os.path.join(lib_dir, fname))
                                except Exception:
                                    pass
    except Exception as e:
        logger.debug(f"Preload nvidia libs exception: {e}")


class FasterWhisperEngine:
    """Wrapper for Faster-Whisper streaming inference with VRAM guard."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cuda",
        compute_type: str = "float16",
        max_vram_mb: int = 400,
        memory_controller: Optional[MemoryController] = None,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.max_vram_mb = max_vram_mb
        self.memory_controller = memory_controller or MemoryController()
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """Load quantized Whisper model with memory verification and automatic CPU fallback."""
        if self.device == "cuda":
            _preload_nvidia_libs()
            if not self.memory_controller.can_allocate(self.max_vram_mb):
                logger.warning(
                    f"Insufficient VRAM headroom for Whisper {self.model_size} ({self.max_vram_mb}MB). "
                    f"Falling back to CPU int8 mode."
                )
                self.device = "cpu"
                self.compute_type = "int8"

        try:
            from faster_whisper import WhisperModel
            logger.info(
                f"Loading Faster-Whisper '{self.model_size}' on {self.device} "
                f"(Compute: {self.compute_type}, Max VRAM: {self.max_vram_mb}MB)..."
            )
            num_threads = min(8, os.cpu_count() or 4)
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=num_threads,
            )
            # Verify CUDA runtime libraries with a dry-run
            if self.device == "cuda":
                dummy = np.zeros(1600, dtype=np.float32)
                list(self.model.transcribe(dummy, beam_size=1)[0])
            logger.info(f"Faster-Whisper model loaded successfully on {self.device}.")
        except Exception as e:
            if self.device == "cuda":
                logger.warning(
                    f"CUDA library error ({e}). Automatically switching Faster-Whisper to CPU INT8 mode."
                )
                self.device = "cpu"
                self.compute_type = "int8"
                try:
                    num_threads = min(8, os.cpu_count() or 4)
                    self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8", cpu_threads=num_threads)
                    logger.info(f"Faster-Whisper model loaded successfully on CPU (INT8, {num_threads} threads).")
                except Exception as ex_cpu:
                    logger.warning(f"Could not load faster-whisper on CPU ({ex_cpu}). Mock fallback.")
                    self.model = None
            else:
                logger.warning(f"Could not load faster-whisper on {self.device} ({e}). Mock fallback.")
                self.model = None

    def transcribe(
        self,
        audio: np.ndarray,
        language: str = "en",
        beam_size: int = 1,
    ) -> List[SubtitleToken]:
        """Transcribe an audio array (16kHz float32 mono) into SubtitleTokens."""
        if self.model is None:
            # Fallback mock for testing without downloaded weights
            return [
                SubtitleToken(
                    text="[MOCK] Transcribed speech chunk",
                    is_partial=False,
                    confidence=0.95,
                    start_time=0.0,
                    end_time=float(len(audio) / 16000.0),
                )
            ]
        clean_audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
        if len(clean_audio) == 0:
            return []

        try:
            segments, info = self.model.transcribe(
                clean_audio,
                language=language if language != "auto" else None,
                beam_size=beam_size,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=350),
                no_speech_threshold=0.6,
                log_prob_threshold=-0.8,
                compression_ratio_threshold=2.4,
                repetition_penalty=1.2,
                no_repeat_ngram_size=3,
                word_timestamps=False,
            )

            tokens = []
            for seg in segments:
                if getattr(seg, "no_speech_prob", 0.0) > 0.6:
                    continue
                if getattr(seg, "avg_logprob", 0.0) < -0.9:
                    continue
                if getattr(seg, "compression_ratio", 1.0) > 2.4:
                    continue
                clean_seg_text = seg.text.strip()
                if not clean_seg_text:
                    continue
                tokens.append(
                    SubtitleToken(
                        text=clean_seg_text,
                        is_partial=False,
                        start_time=seg.start,
                        end_time=seg.end,
                        confidence=np.exp(seg.avg_logprob) if seg.avg_logprob else 0.8,
                    )
                )
            return tokens
        except Exception as e:
            err_msg = str(e).lower()
            if self.device == "cuda" and ("libcublas" in err_msg or "cuda" in err_msg or "cudnn" in err_msg):
                logger.warning(f"CUDA runtime transcription error ({e}). Switching to CPU INT8 mode.")
                self.device = "cpu"
                self.compute_type = "int8"
                from faster_whisper import WhisperModel
                self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                return self.transcribe(audio, language=language, beam_size=beam_size)
            logger.error(f"Error during Faster-Whisper transcription: {e}")
            return []
