"""Tests for Real Multilingual OCR Engine with ONNX Runtime."""

import numpy as np
from PIL import Image, ImageDraw
import pytest

from src.visual.ocr import FastOCREngine


def test_ocr_engine_detects_real_synthetic_text():
    """Verify that FastOCREngine detects and recognizes text rendered on image."""
    engine = FastOCREngine(confidence_threshold=0.4)

    # Create synthetic test image with two lines of clear text
    img = Image.new("RGB", (400, 150), color=(20, 24, 33))
    draw = ImageDraw.Draw(img)
    draw.text((25, 30), "START GAME", fill=(255, 255, 255))
    draw.text((25, 80), "SETTINGS", fill=(255, 255, 255))
    frame = np.array(img)

    boxes = engine.detect_and_recognize(frame)

    assert len(boxes) >= 1
    found_texts = [b.original_text.upper() for b in boxes]
    combined = " ".join(found_texts)

    assert "START" in combined or "GAME" in combined or "SETTINGS" in combined
    for b in boxes:
        assert b.confidence >= 0.4
        assert b.width > 10
        assert b.height > 5


def test_ocr_engine_handles_empty_or_blank_image():
    """Verify that blank images return empty box list without errors."""
    engine = FastOCREngine()
    blank_frame = np.zeros((200, 200, 3), dtype=np.uint8)

    boxes = engine.detect_and_recognize(blank_frame)
    assert isinstance(boxes, list)
    assert len(boxes) == 0


def test_ocr_noise_and_garbage_filtering():
    """Verify that scanline distortion, overlapping ghosts, and merged garbage are rejected."""
    from src.visual.ocr import is_noise_or_self_rendered

    # 1. Repeated character glitch (e.g., 'uuuu', 'llll')
    assert is_noise_or_self_rendered("Sauiltuuuuauueliaqiticil") is True
    assert is_noise_or_self_rendered("Dinalululululllallil") is True

    # 2. Unnaturally merged text with no spaces (>22 characters)
    assert is_noise_or_self_rendered("Batcavesangmotbenturhietlapnhientongsonaunaydetoic6theichsyethon2'I") is True
    assert is_noise_or_self_rendered("Xannuuuautavalugtlei,yuyamruniavuiate") is True

    # 3. Bracketed / markup garbage
    assert is_noise_or_self_rendered("yVm>culiviva Fiulieweiwuu>") is True

    # 4. Vietnamese text (prevent reading back overlay)
    assert is_noise_or_self_rendered("Dịch thuật trực quan thời gian thực") is True

    # 5. System logs & telemetry
    assert is_noise_or_self_rendered("src.core.orchestrator:83 - ✨ [Visual Live]") is True
    assert is_noise_or_self_rendered("4% 62°C () 6.86GB") is True

    # 6. Valid English sentences should NOT be filtered
    assert is_noise_or_self_rendered("Hello world! This is a valid sentence.") is False
    assert is_noise_or_self_rendered("Kininkai is an abbreviation for noble assembly.") is False

