"""Tests for HybridTranslator and caching behavior."""

from src.core.cache import LRUTermCache
from src.core.translator import HybridTranslator, LocalCTranslate2Translator


def test_hybrid_translator_caching():
    cache = LRUTermCache(maxsize=100)
    translator = HybridTranslator(cache=cache)

    # First translation: not in cache
    res1 = translator.translate("Attack", source_lang="en", target_lang="vi")
    assert res1 != ""
    assert cache.contains("Attack") is True

    # Seed cache with custom translation
    cache.put("Victory", "Chiến thắng vẻ vang")
    res2 = translator.translate("Victory", source_lang="en", target_lang="vi")
    assert res2 == "Chiến thắng vẻ vang"

    # Verify hit ratio increased
    stats = cache.stats()
    assert stats["hits"] >= 1


def test_translate_batch():
    """Verify batch translation produces correct results for multiple sentences simultaneously."""
    translator = HybridTranslator()
    texts = [
        "Give a detailed explanation to Rukia",
        "Without saying what, Byakuya gave this command with only a few brief words.",
        "Take care, Byakuya sama",
    ]
    results = translator.translate_batch(texts, source_lang="en", target_lang="vi")
    assert len(results) == len(texts)
    for r in results:
        assert isinstance(r, str)
        assert len(r) > 0
