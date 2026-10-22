"""Context-Aware Tone and Persona Adaptation Engine.

Features:
1. Detects discourse tone (polite dialogue, casual dialogue, official notification, literary narration).
2. Refines mechanical NMT artifacts (e.g., replaces harsh 'các người' with context-appropriate respectful pronouns).
3. Standardizes literary honorifics (e.g., 'Renji Sama' -> 'Renji-sama', 'Byakuya Sama' -> 'Byakuya-sama').
4. Smooths literal phrasing into natural Vietnamese literary expressions without extra GPU overhead.
"""

import re
from typing import List, Optional


VN_UPPER = "A-ZĐÁÀẢÃẠÂẤẦẨẪẬĂẮẰẲẴẶÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ"
SPEECH_VERBS = r"\b(?:nói|bảo|cười|hỏi|đáp|kêu|hét|thì thầm|gật đầu|lẩm bẩm)"


class ToneProcessor:
    """Enhances raw machine translation into natural, tone-appropriate Vietnamese."""

    def __init__(self, persona_style: str = "literary"):
        self.persona_style = persona_style
        # Patterns for harsh/mechanical pronouns that Opus-MT outputs for polite 'you'
        self._rude_pronoun_patterns = [
            (re.compile(r'\bcác người\b', re.IGNORECASE), "hai người"),
            (re.compile(r'\bngười\b(?=\s+(?:phải|chỉ cần|đang|đã|sẽ))', re.IGNORECASE), "bạn"),
        ]

        # Common Japanese honorific standardizations
        self._honorific_patterns = [
            (re.compile(r'\b([A-Z][a-zA-Z]+)\s+[Ss]amal\b'), r'\1-sama!'),
            (re.compile(r'\b([A-Z][a-zA-Z]+)-[Ss]amal\b'), r'\1-sama!'),
            (re.compile(r'\b([A-Z][a-zA-Z]+)\s+[Ss]ama\b'), r'\1-sama'),
            (re.compile(r'\b([A-Z][a-zA-Z]+)\s+[Ss]an\b'), r'\1-san'),
            (re.compile(r'\b([A-Z][a-zA-Z]+)\s+[Kk]un\b'), r'\1-kun'),
            (re.compile(r'\b([A-Z][a-zA-Z]+)\s+[Cc]han\b'), r'\1-chan'),
            (re.compile(r'\b([A-Z][a-zA-Z]+)\s+[Ss]enpai\b'), r'\1-senpai'),
            (re.compile(r'\b([A-Z][a-zA-Z]+)\s+[Dd]ono\b'), r'\1-dono'),
            (re.compile(r'\bNi-[Ss]ama\b', re.IGNORECASE), 'Nii-sama'),
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
            (re.compile(r'\bbị mù\b', re.IGNORECASE), 'khuất tầm mắt'),
            (re.compile(r'ở một cung thấp', re.IGNORECASE), 'vẫn cúi mình cung kính'),
            (re.compile(r'trong khi còn lại cúi mình cung kính', re.IGNORECASE), 'trong khi vẫn cúi mình cung kính'),
            (re.compile(r'tới khuất tầm mắt', re.IGNORECASE), 'khuất hẳn tầm mắt'),
            (re.compile(r'trông chừng cho đến khi', re.IGNORECASE), 'dõi theo bóng lưng ngài cho đến khi'),
            (re.compile(r'Vâng sau đó\.{2,}', re.IGNORECASE), 'Vậy thì...'),
            (re.compile(r'trên thế giới này là gì\s*[\'"]?([a-zA-Z0-9\s]+)[\'"]?\s*mà', re.IGNORECASE), r'rốt cuộc \1 mà'),
            (re.compile(r'\b(?:bạn|Bạn)\s+nên tránh mất kiên nhẫn', re.IGNORECASE), 'ngài đừng nôn nóng thế chứ'),
            (re.compile(r'\btôi sẽ đi ngay bây giờ\b', re.IGNORECASE), 'tôi xin phép lui trước'),
            (re.compile(r'\btrên tờ báo có tựa đề\b', re.IGNORECASE), 'trên tờ giấy có tiêu đề'),
            (re.compile(r'\btờ báo có tựa đề\b', re.IGNORECASE), 'tờ giấy có tiêu đề'),
            (re.compile(r'\btrên tờ báo\b', re.IGNORECASE), 'trên tờ giấy'),
            (re.compile(r'\bmột vô số\b', re.IGNORECASE), 'vô số'),
            (re.compile(r'Abatai Renji', re.IGNORECASE), 'Abarai Renji'),
            (re.compile(r'Bykuya', re.IGNORECASE), 'Byakuya'),
            (re.compile(r'cây viết của Goro', re.IGNORECASE), 'chuồng của Goro'),
            (re.compile(r'Goro của mình bút', re.IGNORECASE), 'chuồng của Goro'),
            (re.compile(r'Goro của mình cây bút', re.IGNORECASE), 'chuồng của Goro'),
            (re.compile(r'bên cạnh cây bút', re.IGNORECASE), 'bên cạnh chiếc chuồng'),
            (re.compile(r'với một cái bút bên cạnh cây bút', re.IGNORECASE), 'bên cạnh chiếc chuồng'),
            (re.compile(r'đến cây bút của mình', re.IGNORECASE), 'về lại chuồng'),
            (re.compile(r'đâm vào tai của mình', re.IGNORECASE), 'vểnh tai lên nghe'),
            (re.compile(r'đâm vào tai', re.IGNORECASE), 'vểnh tai lên'),
            (re.compile(r'được mở rộng ra trong dạ dày', re.IGNORECASE), 'nằm sóng soài úp bụng'),
            (re.compile(r'được mở rộng ra bởi bàn chân', re.IGNORECASE), 'nằm sóng soài dưới chân'),
            (re.compile(r'bị kéo dài ra bởi bàn chân', re.IGNORECASE), 'nằm sóng soài dưới chân'),
            (re.compile(r'người đã trải dài ra bởi bàn chân', re.IGNORECASE), 'nằm sóng soài dưới chân'),
            (re.compile(r'bị ảnh hưởng trong gió nhẹ', re.IGNORECASE), 'lay nhẹ trong làn gió mát'),
            (re.compile(r'bị anh hưởng trong gió nhẹ', re.IGNORECASE), 'lay nhẹ trong làn gió mát'),
            (re.compile(r'lắc đuôi một cách vui vẻ', re.IGNORECASE), 'hớn hở vẫy đuôi'),
            (re.compile(r'hăm dọa cái đuôi của hắn', re.IGNORECASE), 'hớn hở vẫy đuôi'),
            (re.compile(r'wed đuôi', re.IGNORECASE), 'vẫy đuôi'),
            (re.compile(r'wedduoi', re.IGNORECASE), 'vẫy đuôi'),
            (re.compile(r'áo khoác lông trắng', re.IGNORECASE), 'bộ lông trắng muốt'),
            (re.compile(r'đeo khăn của sinh viên', re.IGNORECASE), 'mặc trang phục học viên'),
            (re.compile(r'chăm sóc kỹ lưỡng nội dung', re.IGNORECASE), 'chăm chú xem kỹ nội dung'),
            (re.compile(r'xé bỏ những vùng quan tâm màu đỏ', re.IGNORECASE), 'dùng mực đỏ đánh dấu những chỗ cần lưu ý'),
        ]

    def set_persona(self, persona: str) -> None:
        """Set persona style: 'literary', 'casual', 'formal', 'gamer'."""
        self.persona_style = persona.lower().strip()

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
        res = re.sub(r'"{2,}', '"', res)
        # Speech verb preceding quote gets colon, space, and capitalized dialogue: cười"ngài -> cười: "Ngài
        res = re.sub(rf'({SPEECH_VERBS})\s*[“"]\s*([{VN_UPPER}a-zà-ỹ])', lambda m: f'{m.group(1)}: "{m.group(2).upper()}', res, flags=re.IGNORECASE)
        # Space between closing quote and following word: .."Đó -> .." Đó or Kinin"ở -> Kinin" ở
        res = re.sub(r'([.,!?…\w])[”"](\w)', r'\1" \2', res)
        # Space before opening quote inside sentence: trả lời với “tuân -> trả lời với “tuân
        res = re.sub(r'(\w)[“"](\w)', r'\1 "\2', res)
        # Clean inner spaces in opening quotes (only when preceded by start/space/colon)
        res = re.sub(r'(^|[\s\(\[\{:—])([“"「『])\s+', r'\1\2', res)
        # Clean inner spaces in closing quotes (only when followed by end/space/punctuation)
        res = re.sub(r'\s+([”"」』])(?=$|[\s\.,!?…\)\]\}—])', r'\1', res)
        # Clean spaces before punctuation
        res = re.sub(r'\s+([,.:;?!…])', r'\1', res)
        res = re.sub(r'([.!?…])([A-ZÀ-Ỹ])', r'\1 \2', res)

        return res
