"""Collision Resolver: prevents audio subtitles from overlapping OCR boxes."""

from typing import List, Tuple
from src.core.ipc import VisualBoundingBox


class CollisionResolver:
    """Calculates optimal subtitle positioning to avoid occluding on-screen text."""

    def __init__(self, bottom_margin_ratio: float = 0.85, top_margin_ratio: float = 0.10):
        self.bottom_margin_ratio = bottom_margin_ratio
        self.top_margin_ratio = top_margin_ratio
        self.is_relocated_to_top = False

    def _rectangles_intersect(
        self,
        r1: Tuple[int, int, int, int],
        r2: Tuple[int, int, int, int],
    ) -> bool:
        """Check if two rectangles (x, y, w, h) overlap."""
        x1, y1, w1, h1 = r1
        x2, y2, w2, h2 = r2
        return not (
            x1 + w1 <= x2
            or x2 + w2 <= x1
            or y1 + h1 <= y2
            or y2 + h2 <= y1
        )

    def resolve_position(
        self,
        screen_width: int,
        screen_height: int,
        sub_width: int,
        sub_height: int,
        ocr_boxes: List[VisualBoundingBox],
    ) -> Tuple[int, int, bool]:
        """Compute (x, y) for subtitle. Returns (x, y, is_relocated_to_top)."""
        # Center horizontally
        sub_x = max(0, (screen_width - sub_width) // 2)

        # Default bottom position
        default_y = int(screen_height * self.bottom_margin_ratio) - (sub_height // 2)
        bottom_rect = (sub_x, default_y, sub_width, sub_height)

        # Check collision with any active OCR box
        has_collision = False
        for box in ocr_boxes:
            box_rect = (box.x, box.y, box.width, box.height)
            if self._rectangles_intersect(bottom_rect, box_rect):
                has_collision = True
                break

        if has_collision:
            # Shift to top
            sub_y = int(screen_height * self.top_margin_ratio)
            self.is_relocated_to_top = True
        else:
            sub_y = default_y
            self.is_relocated_to_top = False

        return sub_x, sub_y, self.is_relocated_to_top
