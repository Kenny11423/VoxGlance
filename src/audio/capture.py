"""Audio Capture and Ring Buffer for real-time 16kHz PCM streaming."""

import collections
import threading
from typing import Generator, Optional
import numpy as np
from loguru import logger


class AudioRingBuffer:
    """Thread-safe Ring Buffer for audio streaming chunks."""

    def __init__(self, sample_rate: int = 16000, buffer_duration_sec: float = 5.0):
        self.sample_rate = sample_rate
        self.max_samples = int(sample_rate * buffer_duration_sec)
        self._buffer = collections.deque(maxlen=self.max_samples)
        self._lock = threading.Lock()

    def append(self, samples: np.ndarray) -> None:
        """Append 1D float32 audio samples normalized between -1.0 and 1.0."""
        if samples.ndim > 1:
            samples = samples.mean(axis=1)  # Downmix to mono
        samples = samples.astype(np.float32)

        with self._lock:
            self._buffer.extend(samples.tolist())

    def get_latest(self, num_samples: int) -> np.ndarray:
        """Get the most recent num_samples from the buffer."""
        with self._lock:
            buf_len = len(self._buffer)
            if buf_len == 0:
                return np.zeros(num_samples, dtype=np.float32)
            take = min(num_samples, buf_len)
            recent = list(self._buffer)[-take:]
            arr = np.array(recent, dtype=np.float32)
            if len(arr) < num_samples:
                # Pad leading zeros if not enough samples yet
                pad = np.zeros(num_samples - len(arr), dtype=np.float32)
                arr = np.concatenate([pad, arr])
            return arr

    def clear(self) -> None:
        """Clear all buffered samples."""
        with self._lock:
            self._buffer.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)


class AudioCaptureManager:
    """Manages audio capture from system loopback or input microphone."""

    def __init__(self, sample_rate: int = 16000, chunk_ms: int = 250):
        self.sample_rate = sample_rate
        self.chunk_ms = chunk_ms
        self.chunk_samples = int(sample_rate * (chunk_ms / 1000.0))
        self.ring_buffer = AudioRingBuffer(sample_rate=sample_rate)
        self._is_running = False
        self._stream = None

    def start_stream(self, device: Optional[int] = None) -> bool:
        """Start capturing audio using sounddevice."""
        try:
            import sounddevice as sd

            def _audio_callback(indata, frames, time_info, status):
                if status:
                    logger.warning(f"Audio stream status: {status}")
                self.ring_buffer.append(indata.flatten())

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self.chunk_samples,
                device=device,
                callback=_audio_callback,
            )
            self._stream.start()
            self._is_running = True
            logger.info(f"AudioCaptureManager started (Chunk: {self.chunk_ms}ms, Rate: {self.sample_rate}Hz)")
            return True
        except Exception as e:
            logger.error(f"Failed to start sounddevice stream: {e}. Audio stream offline.")
            self._is_running = False
            return False

    def stop_stream(self) -> None:
        """Stop and close the audio stream."""
        self._is_running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        logger.info("AudioCaptureManager stopped.")

    def is_running(self) -> bool:
        return self._is_running
