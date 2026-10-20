"""Tests for Context-Aware Tone and Persona Adaptation Engine."""

import pytest
from src.core.tone_processor import ToneProcessor
from src.core.translator import HybridTranslator


def test_tone_processor_honorifics():
    """Verify Japanese/novel honorifics are neatly standardized."""
    tp = ToneProcessor()

    t1 = tp.process("Renji Sama các văn phòng đã chờ đợi", source_text="Renji sama the offices")
    assert "Renji-sama" in t1

    t2 = tp.process("Cảm ơn Byakuya Sama rất nhiều", source_text="Thank you Byakuya sama")
    assert "Byakuya-sama" in t2


def test_tone_processor_rude_pronoun_refinement():
    """Verify harsh 'các người' from literal NMT is transformed to polite/friendly pronouns."""
    tp = ToneProcessor()

    # When source mentions 'both'
    t1 = tp.process("Nếu các người phải làm điều đó", source_text="If you both have to do that")
    assert "hai người" in t1
    assert "các người" not in t1

    # In polite context with 'sama' or 'please'
    t2 = tp.process("Renji-sama, các người có thể đi", source_text="Renji-sama, you may go")
    assert "các bạn" in t2 or "ngài" in t2 or "hai người" in t2
    assert "các người" not in t2


def test_tone_processor_phrasing_smoothing():
    """Verify rigid NMT idioms are polished into natural Vietnamese expressions."""
    tp = ToneProcessor()

    raw = "Văn phòng đã chờ đợi, phần đó không thể tránh khỏi."
    smoothed = tp.process(raw)
    assert "điều đó là không thể tránh khỏi" in smoothed


def test_hybrid_translator_full_context_flow():
    """Integration test verifying HybridTranslator applies default glossary and tone processing."""
    tr = HybridTranslator()

    # 1. Dialogue with honorific and idiom smoothing
    s1 = "“Renji sama..... the offices have a waiting time, that part is unavoidable.”"
    res1 = tr.translate(s1, source_lang="en", target_lang="vi")
    assert "Renji-sama" in res1
    assert "không thể tránh khỏi" in res1

    # 2. Glossary term protection: 'pocket watch' -> 'đồng hồ quả quýt'
    s2 = "He looked down at his pocket watch."
    res2 = tr.translate(s2, source_lang="en", target_lang="vi")
    assert "đồng hồ quả quýt" in res2

    # 3. Bureaucratic institution name
    s3 = "The Personnel Administration Bureau handles all procedures in Seireitei."
    res3 = tr.translate(s3, source_lang="en", target_lang="vi")
    assert "Cục Quản lý Nhân sự" in res3
    assert "Tịnh Linh Đình" in res3
