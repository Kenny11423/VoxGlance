"""Smart Text Stitching Engine for Line Grouping and Sentence Reconstruction.

Features:
1. Merges fragmented multi-line OCR bounding boxes into complete grammatical sentences.
2. Respects language spacing rules (space for Latin, no-space for CJK).
3. Computes union bounding box for cohesive in-place replacement.
"""

from typing import List, Tuple
from src.core.ipc import VisualBoundingBox


class SmartTextStitcher:
    """Groups adjacent OCR lines into cohesive sentences before translation."""

    def __init__(
        self,
        line_height_multiplier: float = 1.6,
        horizontal_overlap_threshold: float = 0.2,
    ):
        self.line_height_multiplier = line_height_multiplier
        self.horizontal_overlap_threshold = horizontal_overlap_threshold

    def stitch(
        self,
        boxes: List[VisualBoundingBox],
        detected_lang: str = "en",
    ) -> List[VisualBoundingBox]:
        """Group and stitch fragmented bounding boxes into unified sentence boxes.

        Args:
            boxes: Raw bounding boxes detected by OCR.
            detected_lang: Language code ('ja', 'zh', 'ko', 'en', etc.) to guide spacing.

        Returns:
            List of merged VisualBoundingBox instances.
        """
        if not boxes:
            return []

        if len(boxes) == 1:
            return boxes

        # Sort boxes primarily by vertical position (Y), then horizontal (X)
        sorted_boxes = sorted(boxes, key=lambda b: (b.y, b.x))

        groups: List[List[VisualBoundingBox]] = []
        current_group: List[VisualBoundingBox] = [sorted_boxes[0]]

        for next_box in sorted_boxes[1:]:
            last_box = current_group[-1]

            # Check if next_box belongs to the same paragraph / dialogue block:
            # 1. Vertical distance is within reasonable line height threshold
            avg_h = (last_box.height + next_box.height) / 2.0
            vertical_gap = next_box.y - (last_box.y + last_box.height)

            # 2. Horizontal alignment check (overlap or shared column)
            overlap_x1 = max(last_box.x, next_box.x)
            overlap_x2 = min(last_box.x + last_box.width, next_box.x + next_box.width)
            horizontal_overlap = max(0, overlap_x2 - overlap_x1)
            min_w = min(last_box.width, next_box.width)

            is_vertically_adjacent = -avg_h * 0.5 <= vertical_gap <= avg_h * self.line_height_multiplier
            has_horizontal_alignment = (horizontal_overlap / max(1, min_w)) >= self.horizontal_overlap_threshold or abs(last_box.x - next_box.x) <= 35

            if is_vertically_adjacent and has_horizontal_alignment:
                current_group.append(next_box)
            else:
                groups.append(current_group)
                current_group = [next_box]

        if current_group:
            groups.append(current_group)

        # Merge each group into a single unified bounding box
        stitched_boxes: List[VisualBoundingBox] = []
        for group in groups:
            if len(group) == 1:
                stitched_boxes.append(group[0])
            else:
                merged = self._merge_group(group, detected_lang)
                stitched_boxes.append(merged)

        return stitched_boxes

    def _merge_group(
        self,
        group: List[VisualBoundingBox],
        detected_lang: str,
    ) -> VisualBoundingBox:
        """Merge multiple boxes into a single bounding box."""
        min_x = min(b.x for b in group)
        min_y = min(b.y for b in group)
        max_x = max(b.x + b.width for b in group)
        max_y = max(b.y + b.height for b in group)

        # Spacing separator: No space for CJK (Japanese, Chinese), single space for Latin/others
        sep = "" if detected_lang in ["ja", "zh", "ko"] else " "
        combined_text = sep.join(b.original_text.strip() for b in group if b.original_text.strip())

        avg_conf = sum(b.confidence for b in group) / max(1, len(group))

        return VisualBoundingBox(
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y,
            original_text=combined_text,
            translated_text="",
            confidence=avg_conf,
            timestamp=group[0].timestamp,
            detected_lang=detected_lang,
        )
