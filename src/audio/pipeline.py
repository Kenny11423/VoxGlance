"""Audio Streaming Pipeline implementing Stream-and-Revise for YouTube-like Live Captions."""

import os
import subprocess
import threading
import time
from typing import Callable, Optional
import numpy as np
from loguru import logger

from src.audio.capture import AudioCaptureManager, AudioRingBuffer
from src.audio.vad import SileroVAD
from src.audio.asr import FasterWhisperEngine
from src.core.ipc import SubtitleToken
from src.core.translator import HybridTranslator


class AudioStreamingPipeline:
    """End-to-End Realtime Audio Streaming Pipeline with Stream-and-Revise."""

    def __init__(
        self,
        source: str = "auto",  # 'system' (loopback), 'mic', or 'auto'
        sample_rate: int = 16000,
        chunk_ms: int = 250,
        vad: Optional[SileroVAD] = None,
        asr: Optional[FasterWhisperEngine] = None,
        translator: Optional[HybridTranslator] = None,
        on_subtitle: Optional[Callable[[SubtitleToken], None]] = None,
    ):
        self.source = source
        self.sample_rate = sample_rate
        self.chunk_ms = chunk_ms
        self.chunk_samples = int(sample_rate * (chunk_ms / 1000.0))
        self.vad = vad or SileroVAD(sample_rate=sample_rate)
        self.asr = asr or FasterWhisperEngine()
        self.translator = translator or HybridTranslator()
        self.on_subtitle = on_subtitle

        self.ring_buffer = AudioRingBuffer(sample_rate=sample_rate, buffer_duration_sec=10.0)
        self._is_running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._capture_proc: Optional[subprocess.Popen] = None
        self._capture_manager: Optional[AudioCaptureManager] = None

    def _get_system_monitor_source(self) -> Optional[str]:
        """Detect the default audio sink monitor on PipeWire/PulseAudio."""
        try:
            res = subprocess.run(["pactl", "get-default-sink"], capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0 and res.stdout.strip():
                sink = res.stdout.strip()
                monitor = f"{sink}.monitor"
                return monitor
        except Exception:
            pass
        return None

    def start(self) -> bool:
        """Start capturing audio and running the stream-and-revise processing loop."""
        if self._is_running:
            return True

        self._is_running = True

        # Choose capture backend:
        # If source is 'system' or 'auto' on Linux, try PipeWire system loopback monitor
        monitor_source = self._get_system_monitor_source() if self.source in ["system", "auto"] else None

        if monitor_source and self.source != "mic":
            logger.info(f"Using PipeWire system loopback capture: {monitor_source}")
            cmd = [
                "pw-record",
                "--target", monitor_source,
                "--rate", str(self.sample_rate),
                "--channels", "1",
                "--format", "f32",
                "-",
            ]
            try:
                self._capture_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=self.chunk_samples * 4 * 10,
                )
                self._worker_thread = threading.Thread(target=self._pipewire_loop, daemon=True)
                self._worker_thread.start()
                return True
            except Exception as e:
                logger.warning(f"Failed to start pw-record: {e}. Falling back to sounddevice mic.")

        # Fallback to sounddevice (Microphone capture)
        logger.info("Using sounddevice microphone capture.")
        self._capture_manager = AudioCaptureManager(sample_rate=self.sample_rate, chunk_ms=self.chunk_ms)
        if self._capture_manager.start_stream():
            self._worker_thread = threading.Thread(target=self._sounddevice_loop, daemon=True)
            self._worker_thread.start()
            return True

        self._is_running = False
        return False

    def _pipewire_loop(self) -> None:
        """Read 16kHz float32 audio chunks directly from pw-record stdout."""
        bytes_per_chunk = self.chunk_samples * 4  # 4 bytes per float32
        current_utterance = []
        silence_chunks = 0
        last_partial_time = 0.0

        while self._is_running and self._capture_proc and self._capture_proc.stdout:
            try:
                raw_bytes = self._capture_proc.stdout.read(bytes_per_chunk)
                if not raw_bytes or len(raw_bytes) < bytes_per_chunk:
                    time.sleep(0.01)
                    continue

                chunk = np.frombuffer(raw_bytes, dtype=np.float32)
                self._process_chunk(chunk, current_utterance, silence_chunks, last_partial_time)
            except Exception as e:
                logger.error(f"Error in pipewire read loop: {e}")
                break

    def _sounddevice_loop(self) -> None:
        """Poll audio chunks from AudioCaptureManager ring buffer."""
        current_utterance = []
        silence_chunks = 0
        last_partial_time = 0.0

        while self._is_running and self._capture_manager:
            if len(self._capture_manager.ring_buffer) >= self.chunk_samples:
                chunk = self._capture_manager.ring_buffer.get_latest(self.chunk_samples)
                self._process_chunk(chunk, current_utterance, silence_chunks, last_partial_time)
            else:
                time.sleep(self.chunk_ms / 2000.0)

    def _process_chunk(
        self,
        chunk: np.ndarray,
        current_utterance: list,
        silence_chunks: int,
        last_partial_time: float,
    ) -> None:
        """Core Stream-and-Revise state machine."""
        vad_res = self.vad.is_speech_chunk(chunk)
        now = time.time()

        if vad_res.is_speech:
            current_utterance.append(chunk)
            silence_chunks = 0

            # Generate partial token every 400ms if we have at least 500ms of audio
            utterance_duration_s = (len(current_utterance) * self.chunk_samples) / self.sample_rate
            if utterance_duration_s >= 0.5 and (now - last_partial_time >= 0.4):
                audio_data = np.concatenate(current_utterance)
                tokens = self.asr.transcribe(audio_data)
                if tokens:
                    raw_text = " ".join(t.text for t in tokens).strip()
                    translated = self.translator.translate(raw_text, source_lang="en", target_lang="vi")
                    if self.on_subtitle and translated:
                        self.on_subtitle(
                            SubtitleToken(
                                text=translated,
                                is_partial=True,
                                start_time=0.0,
                                end_time=utterance_duration_s,
                            )
                        )
                last_partial_time = now
        else:
            if current_utterance:
                silence_chunks += 1
                # If silence duration exceeds 250ms (e.g. 1 chunk of 250ms), commit final text
                if silence_chunks >= 1:
                    audio_data = np.concatenate(current_utterance)
                    utterance_duration_s = len(audio_data) / self.sample_rate
                    tokens = self.asr.transcribe(audio_data)
                    if tokens:
                        raw_text = " ".join(t.text for t in tokens).strip()
                        translated = self.translator.translate(raw_text, source_lang="en", target_lang="vi")
                        if self.on_subtitle and translated:
                            self.on_subtitle(
                                SubtitleToken(
                                    text=translated,
                                    is_partial=False,
                                    start_time=0.0,
                                    end_time=utterance_duration_s,
                                )
                            )
                    # Reset buffer for next sentence
                    current_utterance.clear()
                    silence_chunks = 0

    def stop(self) -> None:
        """Stop audio pipeline and release resources."""
        self._is_running = False
        if self._capture_proc:
            try:
                self._capture_proc.terminate()
                self._capture_proc.wait(timeout=1.0)
            except Exception:
                pass
            self._capture_proc = None

        if self._capture_manager:
            self._capture_manager.stop_stream()
            self._capture_manager = None

        logger.info("AudioStreamingPipeline stopped.")
