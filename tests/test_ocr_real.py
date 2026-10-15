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
