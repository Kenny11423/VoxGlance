"""Unit tests for Multilingual Detection, Sentence Stitching, and Glossary Protection."""

import pytest

from src.core.glossary import MultilingualGlossary
from src.core.ipc import VisualBoundingBox
from src.core.language_detector import FastLanguageDetector
from src.core.translator import HybridTranslator
from src.visual.stitcher import SmartTextStitcher


def test_language_detector_multilingual():
    """Test fast detection of Japanese, Korean, Chinese, English, and Vietnamese."""
    detector = FastLanguageDetector()

    # Japanese with Hiragana & Kanji
    ja_res = detector.detect("これはテストです。ゲームを始めましょう。")
    assert ja_res.lang_code == "ja"
    assert ja_res.nllb_code == "jpn_Jpan"

    # Korean with Hangul
    ko_res = detector.detect("안녕하세요. 게임을 시작합니다.")
    assert ko_res.lang_code == "ko"
    assert ko_res.nllb_code == "kor_Hang"

    # Chinese with Hanzi
    zh_res = detector.detect("欢迎来到这个全新的世界。")
    assert zh_res.lang_code == "zh"
    assert zh_res.nllb_code == "zho_Hans"

    # English
    en_res = detector.detect("Welcome to the dungeon. Press Start.")
    assert en_res.lang_code == "en"
    assert en_res.nllb_code == "eng_Latn"

    # Vietnamese
    vi_res = detector.detect("Chào mừng bạn đã quay trở lại trò chơi.")
    assert vi_res.lang_code == "vi"
    assert vi_res.nllb_code == "vie_Latn"


def test_smart_text_stitcher_merging():
    """Test stitching multi-line dialogue boxes into a single cohesive sentence."""
    stitcher = SmartTextStitcher()

    line1 = VisualBoundingBox(x=100, y=100, width=300, height=25, original_text="In ancient times, the", translated_text="")
    line2 = VisualBoundingBox(x=100, y=130, width=320, height=25, original_text="dragon protected the kingdom.", translated_text="")

    stitched = stitcher.stitch([line1, line2], detected_lang="en")
    assert len(stitched) == 1
    assert stitched[0].original_text == "In ancient times, the dragon protected the kingdom."
    assert stitched[0].width >= 320
    assert stitched[0].height >= 55


def test_smart_text_stitcher_cjk_no_space():
    """Test stitching Japanese text without inserting extra spaces."""
    stitcher = SmartTextStitcher()

    line1 = VisualBoundingBox(x=50, y=50, width=200, height=25, original_text="古代の伝説において、", translated_text="")
    line2 = VisualBoundingBox(x=50, y=80, width=220, height=25, original_text="竜は王国を守護していた。", translated_text="")

    stitched = stitcher.stitch([line1, line2], detected_lang="ja")
    assert len(stitched) == 1
    assert stitched[0].original_text == "古代の伝説において、竜は王国を守護していた。"


def test_glossary_term_protection():
    """Test masking and unmasking of game terms and technical names."""
    glossary = MultilingualGlossary()
    glossary.add_term("Shadowheart", "Shadowheart")
    glossary.add_term("Fireball", "Quả Cầu Lửa", domain="game")
    glossary.add_term("Transformer", "Mô hình Transformer", domain="technical")

    raw_text = "Cast Fireball on the enemy with Shadowheart."
    masked, replacements = glossary.mask_terms(raw_text)

    # Fireball and Shadowheart should be replaced with tokens
    assert "__TERM_0__" in masked
    assert "__TERM_1__" in masked
    assert "Fireball" not in masked
    assert "Shadowheart" not in masked

    # Simulated machine translation output keeping tokens
    translated_mock = "Thi triển __TERM_0__ vào kẻ địch cùng __TERM_1__."
    restored = glossary.unmask_terms(translated_mock, replacements)

    assert "Thi triển Quả Cầu Lửa vào kẻ địch cùng Shadowheart." == restored
