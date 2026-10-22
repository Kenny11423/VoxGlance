"""Unit tests for Semantic Context Engine and Dynamic Disambiguation."""

import pytest
from src.core.context_engine import SemanticContextEngine, SemanticDomain
from src.core.translator import HybridTranslator


def test_domain_detection():
    """Verify that domain keywords correctly categorize text."""
    ce = SemanticContextEngine()

    assert ce.detect_domain("The puppy was barking loudly") == SemanticDomain.ANIMAL_PET
    assert ce.detect_domain("The guild formed a raid party to defeat the boss") == SemanticDomain.GAMING_RPG
    assert ce.detect_domain("The captain ordered the soldiers to draw their swords") == SemanticDomain.MILITARY_MARTIAL
    assert ce.detect_domain("The wizard began to chant an ancient spell") == SemanticDomain.FANTASY_MAGIC
    assert ce.detect_domain("Submit your registration paperwork to the bureau") == SemanticDomain.OFFICE_ADMIN


def test_polysemy_animal_domain():
    """Verify polysemous words 'pen' and 'coat' resolve to animal senses."""
    ce = SemanticContextEngine()

    # 'pen' with 'puppy' -> 'kennel'
    t1, domain1, notes1 = ce.resolve_context("The puppy was sleeping inside the pen.")
    assert "kennel" in t1
    assert domain1 == SemanticDomain.ANIMAL_PET
    assert any("pen" in n for n in notes1)

    # 'coat' with 'cat' -> 'fur'
    t2, domain2, notes2 = ce.resolve_context("The white cat has a beautiful coat.")
    assert "fur" in t2
    assert domain2 == SemanticDomain.ANIMAL_PET
    assert any("coat" in n for n in notes2)


def test_polysemy_gaming_domain():
    """Verify gaming words 'tank' and 'party' resolve to RPG senses."""
    ce = SemanticContextEngine()

    # 'tank' with 'raid', 'damage' -> 'defender'
    t1, domain1, notes1 = ce.resolve_context("The raid team needs an experienced tank to absorb damage.")
    assert "defender" in t1
    assert domain1 == SemanticDomain.GAMING_RPG

    # 'party' with 'dungeon', 'boss' -> 'team'
    t2, domain2, notes2 = ce.resolve_context("We formed a party to defeat the dungeon boss.")
    assert "team" in t2
    assert domain2 == SemanticDomain.GAMING_RPG


def test_idiom_resolution():
    """Verify common English idioms are dynamically normalized to figurative meanings."""
    ce = SemanticContextEngine()

    t1, _, _ = ce.resolve_context("After a long shift, he decided to hit the sack.")
    assert "go to sleep" in t1

    t2, _, _ = ce.resolve_context("Solving this math puzzle was a piece of cake.")
    assert "very easy task" in t2

    t3, _, _ = ce.resolve_context("Don't spill the beans about our surprise party.")
    assert "reveal the secret" in t3

    t4, _, _ = ce.resolve_context("He stayed home because he was feeling under the weather.")
    assert "feeling unwell" in t4


def test_sliding_context_carryover():
    """Verify that prior context history informs disambiguation of subsequent sentences."""
    ce = SemanticContextEngine()

    # S1 mentions puppy/dog, establishing ANIMAL_PET context
    prev_context = "We were grooming the puppy in the backyard."

    # S2 only says 'He was resting inside the pen' (no explicit animal word in S2 itself)
    s2 = "He was resting inside the pen."
    t2, domain, notes = ce.resolve_context(s2, context_history=prev_context)

    # Context history should trigger 'pen' -> 'kennel'
    assert "kennel" in t2
    assert domain == SemanticDomain.ANIMAL_PET
    assert any("pen" in n for n in notes)


def test_hybrid_translator_dynamic_context_e2e():
    """End-to-end integration: HybridTranslator produces natural Vietnamese for unseen polysemy & idioms."""
    tr = HybridTranslator()

    # 1. Animal pen (not in static glossary) -> chuồng
    res1 = tr.translate("The puppy was sleeping inside the pen.", source_lang="en", target_lang="vi")
    assert "chuồng" in res1

    # 2. Animal coat (not in static glossary) -> bộ lông
    res2 = tr.translate("The white cat has a beautiful coat.", source_lang="en", target_lang="vi")
    assert "bộ lông" in res2

    # 3. Idiom: hit the sack (not in static glossary) -> đi ngủ
    res3 = tr.translate("After a long day, he decided to hit the sack.", source_lang="en", target_lang="vi")
    assert "đi ngủ" in res3
