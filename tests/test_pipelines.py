"""Tests for AudioStreamingPipeline, VisualStreamingPipeline, and OmniTranslateOrchestrator."""

import numpy as np
import pytest

from src.audio.pipeline import AudioStreamingPipeline
from src.core.config import AppConfig
from src.core.ipc import SubtitleToken
from src.core.orchestrator import OmniTranslateOrchestrator
from src.visual.pipeline import VisualStreamingPipeline


class MockASR:
    def transcribe(self, audio):
        return [SubtitleToken(text="Hello world", is_partial=False)]


def test_audio_pipeline_stream_and_revise():
    received_tokens = []

    def _on_sub(token: SubtitleToken):
        received_tokens.append(token)

    pipeline = AudioStreamingPipeline(
        source="mock",
        sample_rate=16000,
        chunk_ms=250,
        asr=MockASR(),
        on_subtitle=_on_sub,
    )

    # Simulate 2 chunks of speech + 1 chunk of silence
    t = np.linspace(0, 0.25, 4000, endpoint=False)
    speech_chunk = (0.2 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    silence_chunk = np.zeros(4000, dtype=np.float32)

    # 1. First speech chunk
    pipeline._process_chunk(speech_chunk)
    assert len(pipeline._current_utterance) == 1

    # 2. Second speech chunk (total 500ms speech)
    pipeline._process_chunk(speech_chunk)
    assert len(pipeline._current_utterance) == 2

    # 3. Silence chunk (trigger commit)
    pipeline._process_chunk(silence_chunk)
    assert len(pipeline._current_utterance) == 0  # Committed and cleared

    pipeline.stop()


def test_visual_pipeline_lifecycle():
    received_boxes = []

    def _on_boxes(boxes):
        received_boxes.extend(boxes)

    pipeline = VisualStreamingPipeline(
        fps_limit=10,
        diff_threshold=0.05,
        on_boxes=_on_boxes,
    )

    # Start and stop lifecycle
    assert pipeline.start() is True
    assert pipeline._is_running is True
    pipeline.stop()
    assert pipeline._is_running is False


def test_orchestrator_lifecycle():
    config = AppConfig()
    orchestrator = OmniTranslateOrchestrator(
        config=config,
        overlay=None,
        audio_source="mock",
        enable_ocr=False,
        asr_engine=MockASR(),
    )

    orchestrator.start()
    assert orchestrator._is_active is True

    orchestrator.stop()
    assert orchestrator._is_active is False
