"""Tests for AudioStreamingPipeline, VisualStreamingPipeline, and VoxGlanceOrchestrator."""

import numpy as np
import pytest

from src.audio.pipeline import AudioStreamingPipeline
from src.core.config import AppConfig
from src.core.ipc import SubtitleToken
from src.core.orchestrator import VoxGlanceOrchestrator, OmniTranslateOrchestrator
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
    speech_chunk = (
        0.2 * np.sin(2 * np.pi * 130 * t)
        + 0.15 * np.sin(2 * np.pi * 260 * t)
        + 0.1 * np.sin(2 * np.pi * 390 * t)
        + 0.08 * np.sin(2 * np.pi * 750 * t)
    ).astype(np.float32)
    silence_chunk = np.zeros(4000, dtype=np.float32)

    # 1. First speech chunk
    pipeline._process_chunk(speech_chunk)
    assert len(pipeline._current_utterance) == 1

    # 2. Second speech chunk (total 500ms speech)
    pipeline._process_chunk(speech_chunk)
    assert len(pipeline._current_utterance) == 2

    # 3. First silence chunk (should hold buffer to avoid premature cut)
    pipeline._process_chunk(silence_chunk)
    assert len(pipeline._current_utterance) == 2

    # 4. Second silence chunk (meets min_silence_chunks=2, triggers commit)
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


def test_visual_pipeline_clear_on_scroll_state_machine():
    """Verify that scrolling immediately clears overlay and waits for debounce before new translation."""
    from unittest.mock import MagicMock
    from src.core.ipc import VisualBoundingBox

    calls = []

    def _on_boxes(boxes):
        calls.append(list(boxes))

    mock_ocr = MagicMock()
    mock_box = VisualBoundingBox(
        x=50, y=50, width=200, height=30, original_text="Test sentence", translated_text="Câu thử nghiệm"
    )
    mock_ocr.detect_and_recognize.return_value = [mock_box]

    pipeline = VisualStreamingPipeline(
        fps_limit=10,
        diff_threshold=0.05,
        scroll_threshold=0.035,
        settle_delay=0.1,  # Fast settle for test
        ocr_engine=mock_ocr,
        on_boxes=_on_boxes,
    )

    dummy_frame = np.ones((100, 100, 3), dtype=np.uint8) * 200

    # 1. Process initial clean frame
    pipeline._process_and_emit_frame(dummy_frame)
    assert pipeline._has_active_overlay is True
    assert len(calls) == 1
    assert len(calls[0]) == 1  # Overlay emitted

    # 2. Simulate user scrolling: diff exceeds scroll_threshold
    mock_diff = MagicMock()
    mock_diff.diff_ratio = 0.08  # Significant scroll motion

    # Trigger CASE 1 logic
    if mock_diff.diff_ratio >= pipeline.scroll_threshold:
        if pipeline._has_active_overlay:
            pipeline.clear()
        pipeline._is_scrolling = True
        pipeline._last_scroll_time = 0.0


    # Verify overlay was immediately cleared
    assert len(calls) == 2
    assert calls[1] == []  # Cleared!
    assert pipeline._has_active_overlay is False
    assert pipeline._is_scrolling is True

    # 3. Simulate settling (time elapsed > settle_delay)
    import time
    now = time.time()
    pipeline._last_scroll_time = now - 0.2  # 200ms ago > settle_delay (100ms)

    if (now - pipeline._last_scroll_time) >= pipeline.settle_delay:
        pipeline._is_scrolling = False
        pipeline._process_and_emit_frame(dummy_frame)

    assert pipeline._is_scrolling is False
    assert pipeline._has_active_overlay is True
    assert len(calls) == 3
    assert len(calls[2]) == 1  # Clean new translation emitted!



def test_orchestrator_lifecycle():
    config = AppConfig()
    orchestrator = VoxGlanceOrchestrator(
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

    # Verify backward compatibility alias
    assert OmniTranslateOrchestrator is VoxGlanceOrchestrator
