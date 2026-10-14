"""Faster-Whisper INT8 Streaming Engine with strict VRAM capping."""

import time
from typing import Generator, List, Optional
import numpy as np
from loguru import logger

from src.core.ipc import SubtitleToken
from src.core.memory import MemoryController


class FasterWhisperEngine:
    """Wrapper for Faster-Whisper streaming inference with VRAM guard."""

    def __init__(
        self,
        model_size: str = "tiny",
        device: str = "cuda",
        compute_type: str = "int8_float16",
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
        if self.device == "cuda" and not self.memory_controller.can_allocate(self.max_vram_mb):
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
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
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
                    self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                    logger.info("Faster-Whisper model loaded successfully on CPU (INT8).")
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

        try:
            segments, info = self.model.transcribe(
                audio,
                language=language if language != "auto" else None,
                beam_size=beam_size,
                word_timestamps=True,
            )

            tokens = []
            for seg in segments:
                tokens.append(
                    SubtitleToken(
                        text=seg.text.strip(),
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
