"""Tests for CollisionResolver."""

from src.core.ipc import VisualBoundingBox
from src.ui.collision import CollisionResolver


def test_collision_no_overlap():
    resolver = CollisionResolver()
    screen_w, screen_h = 1920, 1080
    sub_w, sub_h = 600, 80

    # OCR box located at top left (100, 100)
    ocr_boxes = [
        VisualBoundingBox(x=100, y=100, width=200, height=40, original_text="Score", translated_text="Điểm")
    ]

    sub_x, sub_y, is_relocated = resolver.resolve_position(screen_w, screen_h, sub_w, sub_h, ocr_boxes)

    # Subtitle should stay at bottom
    assert is_relocated is False
    assert sub_y > 800  # near 85% of 1080 = ~918
    assert sub_x == (1920 - 600) // 2


def test_collision_with_overlap():
    resolver = CollisionResolver()
    screen_w, screen_h = 1920, 1080
    sub_w, sub_h = 600, 80

    # OCR box located right at bottom center where subtitle normally appears
    # Default sub is at x = 660, y ~ 878
    ocr_boxes = [
        VisualBoundingBox(x=700, y=880, width=300, height=50, original_text="Subtitles", translated_text="Phụ đề")
    ]

    sub_x, sub_y, is_relocated = resolver.resolve_position(screen_w, screen_h, sub_w, sub_h, ocr_boxes)

    # Subtitle should be relocated to the top
    assert is_relocated is True
    assert sub_y == int(1080 * 0.10)  # top 10%
    assert sub_x == (1920 - 600) // 2
