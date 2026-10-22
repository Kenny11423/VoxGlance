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


def test_split_sentences_function():
    """Verify sentence boundary segmentation splits correctly without breaking dialogue tags or list prefixes."""
    from src.core.translator import split_sentences

    # Multi-sentence paragraph
    sents = split_sentences("Renji-sama... unavoidable. Because there is no way...")
    assert len(sents) == 2
    assert sents[0] == "Renji-sama... unavoidable."
    assert sents[1] == "Because there is no way..."

    # Dialogue with speech tag (must not split dialogue tag)
    dial = split_sentences('"What is this?" he asked. "I do not know."')
    assert len(dial) == 2
    assert dial[0] == '"What is this?" he asked.'
    assert dial[1] == '"I do not know."'

    # Numbered list item (must not split prefix)
    num = split_sentences("1. SodoUseCaseTongq")
    assert len(num) == 1
    assert num[0] == "1. SodoUseCaseTongq"

    # Honorific abbreviations
    abbr = split_sentences("Dr. Smith went to the hospital. He was on duty.")
    assert len(abbr) == 2
    assert abbr[0] == "Dr. Smith went to the hospital."


def test_multisentence_translation_preservation():
    """Verify that multi-sentence input translates both sentences and preserves subsequent sentences."""
    tr = HybridTranslator()
    text = "Renji-sama... unavoidable. Because there is no way to do this quickly."
    res = tr.translate(text, source_lang="en", target_lang="vi")
    # Both sentences must be present in the translation
    assert "Renji-sama" in res
    assert "không thể tránh khỏi" in res or "không thể" in res
    # Second sentence must not be omitted!
    assert "bởi vì" in res.lower() or "vì" in res.lower() or "không có cách" in res.lower()


def test_novel_terms_and_kennel_smoothing():
    """Verify Bleach novel terms: Goro's pen -> chuồng, wagged tail, pricked up ears."""
    tp = ToneProcessor()

    s1 = tp.process("Iba trở về cây viết của Goro với một cái bút bên cạnh cây bút.")
    assert "chuồng của Goro" in s1
    assert "bên cạnh chiếc chuồng" in s1

    s2 = tp.process("Con chó đâm vào tai của mình và lắc đuôi một cách vui vẻ.")
    assert "vểnh tai lên nghe" in s2
    assert "hớn hở vẫy đuôi" in s2
