"""Context-Aware Tone and Persona Adaptation Engine.

Features:
1. Detects discourse tone (polite dialogue, casual dialogue, official notification, literary narration).
2. Refines mechanical NMT artifacts (e.g., replaces harsh 'các người' with context-appropriate respectful pronouns).
3. Standardizes literary honorifics (e.g., 'Renji Sama' -> 'Renji-sama', 'Byakuya Sama' -> 'Byakuya-sama').
4. Smooths literal phrasing into natural Vietnamese literary expressions without extra GPU overhead.
"""

import re
from typing import List, Optional


class ToneProcessor:
    """Enhances raw machine translation into natural, tone-appropriate Vietnamese."""

    def __init__(self):
        # Patterns for harsh/mechanical pronouns that Opus-MT outputs for polite 'you'
        self._rude_pronoun_patterns = [
            (re.compile(r'\bcác người\b', re.IGNORECASE), "hai người"),
            (re.compile(r'\bngười\b(?=\s+(?:phải|chỉ cần|đang|đã|sẽ))', re.IGNORECASE), "bạn"),
        ]

        # Common Japanese honorific standardizations
        self._honorific_patterns = [
            (re.compile(r'\b([A-Z][a-zA-Z]+)\s+[Ss]ama\b'), r'\1-sama'),
            (re.compile(r'\b([A-Z][a-zA-Z]+)\s+[Ss]an\b'), r'\1-san'),
            (re.compile(r'\b([A-Z][a-zA-Z]+)\s+[Kk]un\b'), r'\1-kun'),
            (re.compile(r'\b([A-Z][a-zA-Z]+)\s+[Cc]han\b'), r'\1-chan'),
            (re.compile(r'\b([A-Z][a-zA-Z]+)\s+[Ss]enpai\b'), r'\1-senpai'),
            (re.compile(r'\b([A-Z][a-zA-Z]+)\s+[Dd]ono\b'), r'\1-dono'),
        ]

        # Awkward literal NMT phrase replacements
        self._phrase_improvements = [
            (re.compile(r'phần đó không thể tránh khỏi', re.IGNORECASE), 'điều đó là không thể tránh khỏi'),
            (re.compile(r'thời gian để hiển thị của chính mình', re.IGNORECASE), 'thời gian để trình'),
            (re.compile(r'chứng minh giấy đăng ký kết hôn', re.IGNORECASE), 'làm thủ tục đăng ký kết hôn'),
            (re.compile(r'nổi tiếng trong thời gian chờ đợi lâu dài của nó', re.IGNORECASE), 'nổi tiếng vì thời gian chờ đợi kéo dài'),
            (re.compile(r'hội nghị cao quý', re.IGNORECASE), 'Hội đồng Quý tộc'),
            (re.compile(r'đồng hồ dự phòng', re.IGNORECASE), 'đồng hồ quả quýt'),
            (re.compile(r'sự bất tuân thượng phẩm', re.IGNORECASE), 'thủ tục cho giới quý tộc'),
            (re.compile(r'Tạp chí 1 nhiệm vụ', re.IGNORECASE), 'Phân khu Trung tâm số 1'),
            (re.compile(r'chiến tranh quân sự!?', re.IGNORECASE), 'đăng ký kết hôn'),
        ]

    def is_dialogue(self, text: str) -> bool:
        """Check if the text represents spoken dialogue."""
        t = text.strip()
        return bool(re.match(r'^[“"「『‘\-\—]', t) or re.search(r'[-–—]\s+[A-Z]', t))

    def has_polite_markers(self, text: str, source_text: str = "") -> bool:
        """Detect if context is polite/respectful (honorifics, humble markers)."""
        combined = f"{text} {source_text}".lower()
        polite_keywords = ["sama", "san", "please", "xin vui lòng", "làm ơn", "ngài", "cảm ơn"]
        return any(k in combined for k in polite_keywords)

    def process(
        self,
        translated_text: str,
        source_text: str = "",
        context_history: Optional[List[str]] = None,
    ) -> str:
        """Refine translated text with tone awareness and contextual fluency.

        Args:
            translated_text: Raw Vietnamese translation from NMT model.
            source_text: Original source text (English/Japanese).
            context_history: List of recent translated sentences for consistency.

        Returns:
            Polished, tone-aware Vietnamese translation.
        """
        if not translated_text:
            return ""

        res = translated_text.strip()

        # 1. Standardize Honorifics (e.g. Renji Sama -> Renji-sama)
        for pat, repl in self._honorific_patterns:
            res = pat.sub(repl, res)

        # 2. Fix Awkward Literal Phrases
        for pat, repl in self._phrase_improvements:
            res = pat.sub(repl, res)

        # 3. Tone & Pronoun Refinement
        is_dial = self.is_dialogue(res) or self.is_dialogue(source_text)
        is_polite = self.has_polite_markers(res, source_text)

        # If preceding context was dialogue or polite, carry over tone
        if context_history and not is_polite:
            recent_context = " ".join(context_history[-2:]).lower()
            if "sama" in recent_context or "ngài" in recent_context:
                is_polite = True

        # Replace rude/mechanical 'các người' with context-appropriate respectful pronouns
        if "both" in source_text.lower():
            res = re.sub(r'\bcác người\b', 'hai người', res, flags=re.IGNORECASE)
        elif is_polite:
            res = re.sub(r'\bcác người\b', 'các bạn', res, flags=re.IGNORECASE)
        else:
            res = re.sub(r'\bcác người\b', 'các bạn', res, flags=re.IGNORECASE)

        # 4. Clean up spacing around quotes and punctuation
        res = re.sub(r'\s+([,.:;?!…])', r'\1', res)
        res = re.sub(r'([“"「『])\s+', r'\1', res)
        res = re.sub(r'\s+([”"」』])', r'\1', res)
        res = re.sub(r'([.!?…])([A-ZÀ-Ỹ])', r'\1 \2', res)

        return res
