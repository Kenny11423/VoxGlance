"""Zero-Latency Language Identification Engine (Unicode Script Analysis + Heuristics).

Features:
1. Sub-millisecond detection of East Asian languages (Japanese, Chinese, Korean) via Unicode blocks.
2. Latin script distinguishing (English, Vietnamese, French, German, Spanish).
3. Standard mapping to ISO 639-1 (2-letter) and Meta NLLB-200 BCP-47 language codes.
"""

from dataclasses import dataclass
import re
from typing import Dict, Optional


@dataclass
class LanguageInfo:
    """Detected language information."""
    lang_code: str  # 2-letter ISO code e.g. 'ja', 'zh', 'ko', 'en', 'vi'
    nllb_code: str  # NLLB-200 code e.g. 'jpn_Jpan', 'zho_Hans', 'kor_Hang', 'eng_Latn', 'vie_Latn'
    name: str  # Human readable name
    confidence: float = 1.0


# Standard NLLB-200 Language Mapping Table
NLLB_LANGUAGE_MAP: Dict[str, Dict[str, str]] = {
    "ja": {"nllb": "jpn_Jpan", "name": "Japanese"},
    "zh": {"nllb": "zho_Hans", "name": "Chinese (Simplified)"},
    "zh-TW": {"nllb": "zho_Hant", "name": "Chinese (Traditional)"},
    "ko": {"nllb": "kor_Hang", "name": "Korean"},
    "en": {"nllb": "eng_Latn", "name": "English"},
    "vi": {"nllb": "vie_Latn", "name": "Vietnamese"},
    "fr": {"nllb": "fra_Latn", "name": "French"},
    "de": {"nllb": "deu_Latn", "name": "German"},
    "es": {"nllb": "spa_Latn", "name": "Spanish"},
    "ru": {"nllb": "rus_Cyrl", "name": "Russian"},
}

# Regex Unicode Ranges for CJK and other major scripts
RE_HIRAGANA = re.compile(r"[\u3040-\u309F]")
RE_KATAKANA = re.compile(r"[\u30A0-\u30FF\u31F0-\u31FF]")
RE_HANGUL = re.compile(r"[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]")
RE_HANZI = re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF]")
RE_CYRILLIC = re.compile(r"[\u0400-\u04FF]")
RE_VIETNAMESE_ACCENTS = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]",
    re.IGNORECASE,
)

# Common stopwords for European languages
STOPWORDS_EN = {"the", "and", "is", "of", "to", "in", "it", "you", "that", "he", "was", "for", "on", "are", "with", "as", "at"}
STOPWORDS_FR = {"le", "la", "les", "un", "une", "des", "et", "est", "dans", "pour", "que", "qui", "sur", "avec"}
STOPWORDS_DE = {"der", "die", "das", "und", "ist", "in", "ein", "eine", "nicht", "mit", "den", "dem", "zu", "von"}
STOPWORDS_ES = {"el", "la", "los", "las", "un", "una", "y", "en", "es", "por", "que", "con", "para", "del"}


class FastLanguageDetector:
    """High-speed language identifier executing in < 0.1ms."""

    def __init__(self, default_lang: str = "en"):
        self.default_lang = default_lang

    def detect(self, text: str) -> LanguageInfo:
        """Analyze text and return detected language metadata.

        Args:
            text: Raw input text.

        Returns:
            LanguageInfo object with standard codes.
        """
        clean = text.strip()
        if not clean:
            meta = NLLB_LANGUAGE_MAP[self.default_lang]
            return LanguageInfo(self.default_lang, meta["nllb"], meta["name"], confidence=0.0)

        # 1. Check for Japanese (Hiragana or Katakana presence is definitive)
        has_hiragana = bool(RE_HIRAGANA.search(clean))
        has_katakana = bool(RE_KATAKANA.search(clean))
        if has_hiragana or has_katakana:
            meta = NLLB_LANGUAGE_MAP["ja"]
            return LanguageInfo("ja", meta["nllb"], meta["name"], confidence=0.99)

        # 2. Check for Korean (Hangul presence is definitive)
        if RE_HANGUL.search(clean):
            meta = NLLB_LANGUAGE_MAP["ko"]
            return LanguageInfo("ko", meta["nllb"], meta["name"], confidence=0.99)

        # 3. Check for Chinese (Hanzi without Kana/Hangul)
        hanzi_count = len(RE_HANZI.findall(clean))
        total_chars = max(1, len(re.sub(r"\s+", "", clean)))
        if hanzi_count > 0 and (hanzi_count / total_chars) > 0.35:
            meta = NLLB_LANGUAGE_MAP["zh"]
            return LanguageInfo("zh", meta["nllb"], meta["name"], confidence=0.95)

        # 4. Check for Cyrillic / Russian
        if RE_CYRILLIC.search(clean):
            meta = NLLB_LANGUAGE_MAP["ru"]
            return LanguageInfo("ru", meta["nllb"], meta["name"], confidence=0.98)

        # 5. Check for Vietnamese accents
        if RE_VIETNAMESE_ACCENTS.search(clean):
            meta = NLLB_LANGUAGE_MAP["vi"]
            return LanguageInfo("vi", meta["nllb"], meta["name"], confidence=0.98)

        # 6. Latin Language Distinguisher using stopword matching
        words = set(re.findall(r"\b[a-zA-Z]{2,}\b", clean.lower()))
        if words:
            score_en = len(words.intersection(STOPWORDS_EN))
            score_fr = len(words.intersection(STOPWORDS_FR))
            score_de = len(words.intersection(STOPWORDS_DE))
            score_es = len(words.intersection(STOPWORDS_ES))

            scores = [("en", score_en), ("fr", score_fr), ("de", score_de), ("es", score_es)]
            scores.sort(key=lambda x: x[1], reverse=True)

            best_lang, best_score = scores[0]
            if best_score > 0:
                meta = NLLB_LANGUAGE_MAP[best_lang]
                return LanguageInfo(best_lang, meta["nllb"], meta["name"], confidence=0.85)

        # Default fallback to English
        meta = NLLB_LANGUAGE_MAP.get(self.default_lang, NLLB_LANGUAGE_MAP["en"])
        return LanguageInfo(self.default_lang, meta["nllb"], meta["name"], confidence=0.6)

    def to_nllb_code(self, lang_code: str) -> str:
        """Convert standard 2-letter code to NLLB-200 code."""
        meta = NLLB_LANGUAGE_MAP.get(lang_code.lower())
        if meta:
            return meta["nllb"]
        return "eng_Latn"
