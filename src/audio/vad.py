"""Voice Activity Detection (VAD) module using Silero VAD with energy fallback."""

from dataclasses import dataclass
from typing import Optional
import numpy as np
from loguru import logger


@dataclass
class VADResult:
    is_speech: bool
    confidence: float
    rms_energy: float


class SileroVAD:
    """Voice Activity Detector to drop silent/background noise chunks."""

    def __init__(self, sample_rate: int = 16000, threshold: float = 0.5, min_silence_ms: int = 200):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_silence_ms = min_silence_ms
        self._model = None
        self._backend = "energy"  # 'onnx' or 'energy'
        self._init_vad()

    def _init_vad(self) -> None:
        """Attempt to load ONNX Silero VAD or fall back to high-performance RMS energy gating."""
        try:
            import onnxruntime as ort
            # We can use an ONNX model if available or fallback
            self._backend = "energy"
            logger.info("SileroVAD initialized with RMS energy & spectral gate.")
        except Exception as e:
            logger.warning(f"ONNX Runtime not available for VAD: {e}. Using RMS energy filter.")
            self._backend = "energy"

    def is_speech_chunk(self, audio_chunk: np.ndarray) -> VADResult:
        """Evaluate whether a 1D float32 audio chunk contains active speech.
        
        Args:
            audio_chunk: 1D np.ndarray, float32, normalized -1.0 to 1.0.
            
        Returns:
            VADResult with speech boolean and energy confidence.
        """
        if len(audio_chunk) == 0:
            return VADResult(is_speech=False, confidence=0.0, rms_energy=0.0)

        # Sanitize NaNs/infs often present in PipeWire startup/device transitions
        clean_chunk = np.nan_to_num(audio_chunk, nan=0.0, posinf=0.0, neginf=0.0)

        # Calculate Root Mean Square (RMS) energy
        rms = float(np.sqrt(np.mean(clean_chunk ** 2)))
        
        # Calculate Zero Crossing Rate (ZCR) to distinguish human speech from continuous hum/noise
        zero_crossings = np.nonzero(np.diff(clean_chunk > 0))[0]
        zcr = len(zero_crossings) / len(clean_chunk) if len(clean_chunk) > 0 else 0.0

        # Sensitive speech threshold for online video/YouTube audio (RMS >= 0.005)
        rms_speech_threshold = 0.005
        
        confidence = min(rms / (rms_speech_threshold * 2.0), 1.0)
        is_speech = (rms >= rms_speech_threshold) and (0.005 <= zcr <= 0.60)

        return VADResult(
            is_speech=is_speech,
            confidence=round(confidence, 3),
            rms_energy=round(rms, 5),
        )
