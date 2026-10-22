"""Smart Text Stitching Engine for Line Grouping and Sentence Reconstruction.

Features:
1. Merges fragmented multi-line OCR bounding boxes into complete grammatical sentences.
2. Context-aware sentence boundary detection (unfinished lines vs dialogue turns & list items).
3. De-hyphenates words broken across line wraps (e.g. 'regis-' + 'tration!' -> 'registration!').
4. Respects language spacing rules (space for Latin, no-space for CJK).
5. Computes union bounding box for cohesive in-place replacement and complete masking.
"""

import re
from typing import List, Tuple
from src.core.ipc import VisualBoundingBox


class SmartTextStitcher:
    """Groups adjacent OCR lines into cohesive sentences before translation."""

    def __init__(
        self,
        line_height_multiplier: float = 0.85,
        horizontal_overlap_threshold: float = 0.35,
        max_column_drift: int = 50,
    ):
        self.line_height_multiplier = line_height_multiplier
        self.horizontal_overlap_threshold = horizontal_overlap_threshold
        self.max_column_drift = max_column_drift

    @staticmethod
    def _is_complete_dialogue(text: str) -> bool:
        """Check if a line is a complete, self-contained dialogue quote."""
        t = text.strip()
        starts_quote = bool(re.match(r'^[“"「『‘]', t))
        ends_quote = bool(re.search(r'[”"」』’][\s.]*$', t))
        return starts_quote and ends_quote

    @classmethod
    def _is_sentence_terminator(cls, text: str) -> bool:
        """Check if a line ends with sentence-terminating punctuation or closes a dialogue."""
        t = text.strip()
        if not t:
            return True
        if cls._is_complete_dialogue(t):
            return True
        # Ignore common abbreviations ending with dot
        if re.search(r'\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|e\.g|i\.e)\.\s*$', t, re.IGNORECASE):
            return False
        # Matches ., !, ?, …, ... or CJK equivalents 。！？ followed by optional quotes/brackets
        return bool(re.search(r'([.!?…]+|[。！？])[\s"\'”’»\)\]]*$', t))

    @staticmethod
    def _is_new_block_starter(text: str) -> bool:
        """Check if a line clearly starts a new item, dialogue turn, or structural block."""
        t = text.strip()
        # Numbered list or bullet point: "1-", "2.", "3)", "4-For", "•", "-", "*"
        if re.match(r'^(?:\(?\d+[\.\-\)]\s*|[•\-\*■◆]\s+)', t):
            return True
        # Dialogue quotation starter: “ " 「 『 ‘
        if re.match(r'^[“"「『‘]', t):
            return True
        return False

    @staticmethod
    def _clean_and_join_lines(prev_text: str, next_text: str, detected_lang: str) -> str:
        """Join two consecutive lines, seamlessly unwrapping hyphenated words."""
        prev = prev_text.strip()
        nxt = next_text.strip()
        if not prev:
            return nxt
        if not nxt:
            return prev

        # De-hyphenate broken words across line wraps in Latin languages:
        # e.g., "regis-" + "tration!" -> "registration!"
        if detected_lang not in ["ja", "zh"]:
            hyphen_match = re.search(r'([a-zA-Z]+)\s*[-\u2010\u2013]\s*$', prev)
            start_match = re.match(r'^[a-zA-Z]+', nxt)
            if hyphen_match and start_match:
                prev_unhyphen = re.sub(r'\s*[-\u2010\u2013]\s*$', '', prev)
                return prev_unhyphen + nxt

        # Standard joining: No space for CJK, single space for others
        sep = "" if detected_lang in ["ja", "zh", "ko"] else " "
        return f"{prev}{sep}{nxt}"

    def stitch(
        self,
        boxes: List[VisualBoundingBox],
        detected_lang: str = "en",
    ) -> List[VisualBoundingBox]:
        """Group and stitch fragmented bounding boxes into cohesive paragraph boxes.

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

            avg_h = (last_box.height + next_box.height) / 2.0
            vertical_gap = next_box.y - (last_box.y + last_box.height)

            # Horizontal alignment check: must share the same column
            overlap_x1 = max(last_box.x, next_box.x)
            overlap_x2 = min(last_box.x + last_box.width, next_box.x + next_box.width)
            horizontal_overlap = max(0, overlap_x2 - overlap_x1)
            min_w = min(last_box.width, next_box.width)

            has_horizontal_alignment = (
                abs(last_box.x - next_box.x) <= self.max_column_drift
                or (horizontal_overlap / max(1, min_w)) >= self.horizontal_overlap_threshold
            )

            last_text = last_box.original_text.strip()
            next_text = next_box.original_text.strip()

            last_finished = self._is_sentence_terminator(last_text)
            last_is_complete_dial = self._is_complete_dialogue(last_text)
            next_is_dial_start = bool(re.match(r'^[“"「『‘]', next_text))

            # Never stitch a new bullet/numbered list item into the preceding line
            is_new_list_item = bool(re.match(r'^(?:\(?\d+[\.\-\)]\s*|[•\-\*■◆]\s+)', next_text))

            # Separation conditions:
            # 1. Complete dialogue line must not absorb the next line
            # 2. Finished sentence must not absorb a new dialogue line
            if last_is_complete_dial:
                should_merge = False
            elif next_is_dial_start and last_finished:
                should_merge = False
            else:
                # Dynamic line gap tolerance:
                # Unfinished lines get up to 1.45x height (bridges loose line wraps within clause, e.g. web novel CSS)
                # Finished lines get strict in-paragraph multiplier (0.60x) to avoid bridging paragraph breaks
                allowed_multiplier = 1.45 if not last_finished else self.line_height_multiplier
                is_vertically_adjacent = -avg_h * 0.5 <= vertical_gap <= avg_h * allowed_multiplier

                should_merge = (
                    has_horizontal_alignment
                    and is_vertically_adjacent
                    and not is_new_list_item
                )

            if should_merge:
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

        combined_text = group[0].original_text.strip()
        for b in group[1:]:
            combined_text = self._clean_and_join_lines(combined_text, b.original_text, detected_lang)

        avg_conf = sum(b.confidence for b in group) / max(1, len(group))
        line_count = len(group)
        avg_line_h = sum(getattr(b, "original_line_height", float(b.height)) for b in group) / max(1, line_count)

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
            original_line_height=avg_line_h,
            line_count=line_count,
        )
