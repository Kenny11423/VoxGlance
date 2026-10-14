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
        """Load official neural Silero VAD from faster-whisper."""
        try:
            from faster_whisper.vad import get_vad_model
            self._model = get_vad_model()
            logger.info("SileroVAD initialized with neural model (AI speech-vs-music discrimination active).")
        except Exception as e:
            logger.warning(f"Could not load neural Silero VAD: {e}. Using energy fallback.")
            self._model = None

    def is_speech_chunk(self, audio_chunk: np.ndarray) -> VADResult:
        """Evaluate whether a 1D float32 audio chunk contains real human vocal speech."""
        if len(audio_chunk) == 0:
            return VADResult(is_speech=False, confidence=0.0, rms_energy=0.0)

        clean = np.nan_to_num(audio_chunk, nan=0.0, posinf=0.0, neginf=0.0)
        rms = float(np.sqrt(np.mean(clean ** 2)))

        # Absolute floor: below 0.003 is silence
        if rms < 0.003:
            return VADResult(is_speech=False, confidence=0.0, rms_energy=round(rms, 5))

        if self._model is not None:
            try:
                # Pad audio to multiple of 512 for Silero VAD
                rem = len(clean) % 512
                padded = clean if rem == 0 else np.pad(clean, (0, 512 - rem))
                probs = self._model(padded, num_samples=512)
                max_prob = float(probs.max())
                mean_prob = float(probs.mean())
                # Human speech has high instantaneous vocal probability
                is_speech = (max_prob >= self.threshold) or (mean_prob >= 0.35)
                return VADResult(
                    is_speech=is_speech,
                    confidence=round(max_prob, 3),
                    rms_energy=round(rms, 5),
                )
            except Exception as e:
                logger.debug(f"Silero VAD model inference error: {e}")

        # Fallback energy gating
        zero_crossings = np.nonzero(np.diff(clean > 0))[0]
        zcr = len(zero_crossings) / len(clean) if len(clean) > 0 else 0.0
        is_speech = (rms >= 0.015) and (0.01 <= zcr <= 0.55)
        return VADResult(
            is_speech=is_speech,
            confidence=round(min(rms / 0.03, 1.0), 3),
            rms_energy=round(rms, 5),
        )
