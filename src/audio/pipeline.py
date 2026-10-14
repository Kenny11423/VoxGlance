import concurrent.futures
import os
import queue
import subprocess
import sys
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
    """End-to-End Realtime Audio Streaming Pipeline with Non-Blocking Stream-and-Revise."""

    def __init__(
        self,
        source: str = "auto",  # 'system' (loopback), 'mic', or 'auto'
        sample_rate: int = 16000,
        chunk_ms: int = 250,
        vad: Optional[SileroVAD] = None,
        asr: Optional[FasterWhisperEngine] = None,
        translator: Optional[HybridTranslator] = None,
        on_subtitle: Optional[Callable[[SubtitleToken], None]] = None,
        min_silence_chunks: int = 2,
    ):
        self.source = source
        self.sample_rate = sample_rate
        self.chunk_ms = chunk_ms
        self.chunk_samples = int(sample_rate * (chunk_ms / 1000.0))
        self.vad = vad or SileroVAD(sample_rate=sample_rate)
        self.asr = asr or FasterWhisperEngine()
        self.translator = translator or HybridTranslator()
        self.on_subtitle = on_subtitle
        self.min_silence_chunks = min_silence_chunks

        self.ring_buffer = AudioRingBuffer(sample_rate=sample_rate, buffer_duration_sec=10.0)
        self._audio_queue: queue.Queue = queue.Queue(maxsize=24)  # 6-second queue capacity for smooth streaming
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


        self._is_running = False
        self._capture_thread: Optional[threading.Thread] = None
        self._process_thread: Optional[threading.Thread] = None
        self._capture_proc: Optional[subprocess.Popen] = None
        self._capture_manager: Optional[AudioCaptureManager] = None

        # State for Stream-and-Revise
        self._current_utterance = []
        self._silence_chunks = 0
        self._last_partial_time = 0.0
        self._last_committed_text = ""
        self._last_committed_time = 0.0


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

        # Start background processing consumer thread
        self._process_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self._process_thread.start()

        # Choose capture backend:
        # If source is 'system' or 'auto' on Linux, use PipeWire loopback capture
        if self.source in ["system", "auto"] and sys.platform.startswith("linux"):
            import shutil
            if shutil.which("pw-record"):
                target = "@DEFAULT_MONITOR@"
                logger.info(f"Using PipeWire system loopback capture (Target: {target})")
                cmd = [
                    "pw-record",
                    "--target", target,
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
                        bufsize=self.chunk_samples * 4 * 4,
                    )
                    self._capture_thread = threading.Thread(target=self._pipewire_loop, daemon=True)
                    self._capture_thread.start()
                    return True
                except Exception as e:
                    logger.warning(f"Failed to start pw-record: {e}. Falling back to sounddevice mic.")

        # Fallback to sounddevice (Microphone capture)
        logger.info("Using sounddevice microphone capture.")
        self._capture_manager = AudioCaptureManager(sample_rate=self.sample_rate, chunk_ms=self.chunk_ms)
        if self._capture_manager.start_stream():
            self._capture_thread = threading.Thread(target=self._sounddevice_loop, daemon=True)
            self._capture_thread.start()
            return True

        self._is_running = False
        return False

    def _pipewire_loop(self) -> None:
        """Fast non-blocking read from pw-record stdout into real-time audio queue."""
        bytes_per_chunk = self.chunk_samples * 4  # 4 bytes per float32

        while self._is_running and self._capture_proc and self._capture_proc.stdout:
            try:
                raw_bytes = self._capture_proc.stdout.read(bytes_per_chunk)
                if not raw_bytes or len(raw_bytes) < bytes_per_chunk:
                    time.sleep(0.005)
                    continue

                chunk = np.frombuffer(raw_bytes, dtype=np.float32)
                chunk = np.nan_to_num(chunk, nan=0.0, posinf=0.0, neginf=0.0)

                # Keep queue strictly real-time: drop stale audio if consumer is busy
                if self._audio_queue.full():
                    try:
                        self._audio_queue.get_nowait()
                    except Exception:
                        pass

                self._audio_queue.put(chunk)
            except Exception as e:
                logger.error(f"Error in pipewire read loop: {e}")
                break

    def _sounddevice_loop(self) -> None:
        """Poll audio chunks from AudioCaptureManager ring buffer."""
        while self._is_running and self._capture_manager:
            if len(self._capture_manager.ring_buffer) >= self.chunk_samples:
                chunk = self._capture_manager.ring_buffer.get_latest(self.chunk_samples)
                chunk = np.nan_to_num(chunk, nan=0.0, posinf=0.0, neginf=0.0)
                if self._audio_queue.full():
                    try:
                        self._audio_queue.get_nowait()
                    except Exception:
                        pass
                self._audio_queue.put(chunk)
            else:
                time.sleep(self.chunk_ms / 2000.0)

    def _processing_loop(self) -> None:
        """Dedicated consumer thread running VAD and ASR without blocking capture."""
        while self._is_running:
            try:
                chunk = self._audio_queue.get(timeout=0.1)
                self._process_chunk(chunk)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in audio processing loop: {e}")

    def _async_translate_and_commit(self, raw_text: str, duration_s: float) -> None:
        """Asynchronously translate committed sentence into natural Vietnamese."""
        try:
            translated = self.translator.translate(raw_text, source_lang="en", target_lang="vi")
            if translated:
                logger.info(f"✅ [Commit]: {raw_text} -> {translated}")
                if self.on_subtitle:
                    self.on_subtitle(
                        SubtitleToken(
                            text=translated,
                            is_partial=False,
                            start_time=0.0,
                            end_time=duration_s,
                        )
                    )
        except Exception as e:
            logger.warning(f"Async translation error: {e}")

    def _commit_current_utterance(self, now: float) -> None:
        """Commit buffered audio utterance, transcribe, and initiate async translation."""
        if not self._current_utterance:
            return

        audio_data = np.concatenate(self._current_utterance)
        utterance_duration_s = len(audio_data) / self.sample_rate

        # Clear buffer immediately so next audio can start accumulating
        self._current_utterance.clear()
        self._silence_chunks = 0

        # Discard microscopic blips (< 0.35s) that are just noise clicks
        if utterance_duration_s < 0.35:
            return

        tokens = self.asr.transcribe(audio_data)
        if tokens:
            raw_text = " ".join(t.text for t in tokens).strip()
            # Anti-repetition: do not repeat exact same sentence when pausing or re-segmenting
            if raw_text and (raw_text != self._last_committed_text or (now - self._last_committed_time > 3.0)):
                self._last_committed_text = raw_text
                self._last_committed_time = now
                # Submit translation to background worker so audio capture NEVER blocks
                if self._is_running and hasattr(self, "_executor") and self._executor:
                    self._executor.submit(
                        self._async_translate_and_commit, raw_text, utterance_duration_s
                    )
                else:
                    self._async_translate_and_commit(raw_text, utterance_duration_s)

    def _process_chunk(self, chunk: np.ndarray) -> None:
        """Core Stream-and-Revise state machine."""
        vad_res = self.vad.is_speech_chunk(chunk)
        now = time.time()

        if vad_res.is_speech:
            self._current_utterance.append(chunk)
            self._silence_chunks = 0
            utterance_duration_s = (len(self._current_utterance) * self.chunk_samples) / self.sample_rate

            # If continuous speech reaches 2.0s, commit cleanly to prevent lag and accumulated delay
            if utterance_duration_s >= 2.0:
                self._commit_current_utterance(now)
                return

            # Generate live partial preview every 250ms when we have at least 350ms of speech
            if utterance_duration_s >= 0.35 and (now - self._last_partial_time >= 0.25):
                audio_data = np.concatenate(self._current_utterance)
                tokens = self.asr.transcribe(audio_data)
                if tokens:
                    raw_text = " ".join(t.text for t in tokens).strip()
                    if raw_text and raw_text != self._last_committed_text:
                        # Translate immediately to Vietnamese in sub-30ms! NEVER display raw English!
                        vi_text = self.translator.translate(raw_text, source_lang="en", target_lang="vi")
                        if vi_text and self.on_subtitle:
                            self.on_subtitle(
                                SubtitleToken(
                                    text=vi_text,
                                    is_partial=True,
                                    start_time=0.0,
                                    end_time=utterance_duration_s,
                                )
                            )
                self._last_partial_time = now
        else:
            if self._current_utterance:
                self._silence_chunks += 1
                # If silence duration exceeds min_silence_chunks (2 chunks = 500ms), commit sentence
                if self._silence_chunks >= self.min_silence_chunks:
                    self._commit_current_utterance(now)
            else:
                self._silence_chunks = 0



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

        if hasattr(self, "_executor") and self._executor:
            try:
                self._executor.shutdown(wait=False)
            except Exception:
                pass

        logger.info("AudioStreamingPipeline stopped.")

