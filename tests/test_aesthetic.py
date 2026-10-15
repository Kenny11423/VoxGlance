"""Unit tests for Aesthetic Blending Engine."""

import numpy as np
import pytest

from src.core.ipc import VisualBoundingBox
from src.visual.aesthetic import (
    apply_aesthetic_styling,
    calculate_optimal_font_size,
    get_contrast_text_color,
    sample_background_color,
)


def test_sample_background_color_uniform_frame():
    """Test background color sampling from a solid colored frame."""
    # Create a 200x200 dark blue frame (B=100, G=30, R=20)
    frame = np.full((200, 200, 3), (20, 30, 100), dtype=np.uint8)
    bbox = (50, 50, 60, 20)

    sampled = sample_background_color(frame, bbox, margin=4)
    assert sampled == (20, 30, 100)


def test_sample_background_color_fallback():
    """Test fallback when frame is None or out of bounds."""
    default = (10, 20, 30)
    res = sample_background_color(None, (10, 10, 50, 20), default_color=default)
    assert res == default


def test_get_contrast_text_color():
    """Test contrast text and outline calculation."""
    # Dark background -> white text, black outline
    dark_bg = (15, 20, 30)
    text_c, outline_c = get_contrast_text_color(dark_bg)
    assert text_c == (255, 255, 255)
    assert outline_c == (10, 10, 15)

    # Light background -> dark text, white outline
    light_bg = (240, 245, 250)
    text_c, outline_c = get_contrast_text_color(light_bg)
    assert text_c == (15, 23, 42)
    assert outline_c == (255, 255, 255)


def test_calculate_optimal_font_size_short_vs_long():
    """Test that longer text automatically scales down font size to prevent overflow."""
    box_w, box_h = 160, 40

    short_text = "Attack"
    long_vietnamese_text = "Tấn công dồn dập vào điểm yếu của kẻ địch"

    size_short = calculate_optimal_font_size(short_text, box_w, box_h)
    size_long = calculate_optimal_font_size(long_vietnamese_text, box_w, box_h)

    assert size_short > size_long
    assert size_long >= 8


def test_apply_aesthetic_styling():
    """Test that apply_aesthetic_styling enriches box with colors and font size."""
    frame = np.full((100, 100, 3), (25, 45, 75), dtype=np.uint8)
    box = VisualBoundingBox(
        x=20,
        y=20,
        width=50,
        height=25,
        original_text="Save Game",
        translated_text="Lưu Trò Chơi",
    )

    styled_box = apply_aesthetic_styling(box, frame=frame)
    assert styled_box.bg_color == (25, 45, 75)
    assert styled_box.text_color == (255, 255, 255)
    assert styled_box.font_size >= 8
