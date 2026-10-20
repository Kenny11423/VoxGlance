"""Tests for Advanced Smart Text Stitcher and Punctuation-Aware Grouping."""

import pytest
from src.core.ipc import VisualBoundingBox
from src.visual.stitcher import SmartTextStitcher


def test_stitcher_dehyphenation():
    """Test that words split across lines with hyphens are cleanly merged without spaces."""
    stitcher = SmartTextStitcher()

    b1 = VisualBoundingBox(
        x=200, y=100, width=500, height=18,
        original_text="show your own marriage regis-",
        translated_text=""
    )
    b2 = VisualBoundingBox(
        x=200, y=126, width=120, height=18,
        original_text="tration!”",
        translated_text=""
    )

    stitched = stitcher.stitch([b1, b2], detected_lang="en")
    assert len(stitched) == 1
    assert stitched[0].original_text == "show your own marriage registration!”"
    assert stitched[0].height >= 44


def test_stitcher_unfinished_sentence_loose_gap():
    """Unfinished sentences (no period/exclamation) should bridge loose line gaps (web/novel CSS)."""
    stitcher = SmartTextStitcher()

    # Gap of 14px on 16px line height (gap/h = 0.875)
    b1 = VisualBoundingBox(
        x=150, y=100, width=600, height=16,
        original_text="The Personnel Administration Bureau handles all procedures within and",
        translated_text=""
    )
    b2 = VisualBoundingBox(
        x=150, y=130, width=620, height=16,
        original_text="outside Seireitei is especially busy, it is famous for its long wait times,",
        translated_text=""
    )

    stitched = stitcher.stitch([b1, b2], detected_lang="en")
    assert len(stitched) == 1
    assert "within and outside" in stitched[0].original_text


def test_stitcher_respects_list_items():
    """Numbered list items (e.g., 3-For, 4-For) must NOT be merged together."""
    stitcher = SmartTextStitcher()

    b1 = VisualBoundingBox(
        x=100, y=100, width=500, height=18,
        original_text="3-For the marriages of official seats and above-submission of registration",
        translated_text=""
    )
    b2 = VisualBoundingBox(
        x=100, y=128, width=500, height=18,
        original_text="4-For the marriages of nobles-submission of noble marriage registration",
        translated_text=""
    )

    stitched = stitcher.stitch([b1, b2], detected_lang="en")
    assert len(stitched) == 2
    assert stitched[0].original_text.startswith("3-")
    assert stitched[1].original_text.startswith("4-")


def test_stitcher_respects_separate_dialogue_turns():
    """When a dialogue ends with closing quote and next line starts with opening quote, keep separate."""
    stitcher = SmartTextStitcher()

    b1 = VisualBoundingBox(
        x=100, y=100, width=200, height=18,
        original_text='“Of course not!”',
        translated_text=""
    )
    b2 = VisualBoundingBox(
        x=100, y=126, width=450, height=18,
        original_text='“Renji sama... the offices have a waiting time, that part is unavoidable.”',
        translated_text=""
    )

    stitched = stitcher.stitch([b1, b2], detected_lang="en")
    assert len(stitched) == 2
    assert stitched[0].original_text == '“Of course not!”'
    assert stitched[1].original_text.startswith('“Renji sama')


def test_stitcher_multi_line_dialogue_continuation():
    """A long dialogue broken across lines without quotes in between must be merged."""
    stitcher = SmartTextStitcher()

    b1 = VisualBoundingBox(
        x=100, y=100, width=600, height=18,
        original_text='“By the way, the reception counter of the Kinin Noble Assembly is open, so',
        translated_text=""
    )
    b2 = VisualBoundingBox(
        x=100, y=126, width=620, height=18,
        original_text='please be aware of that! It is for that reason that Byakuya was concerned.”',
        translated_text=""
    )

    stitched = stitcher.stitch([b1, b2], detected_lang="en")
    assert len(stitched) == 1
    assert stitched[0].original_text.startswith('“By the way')
    assert stitched[0].original_text.endswith('concerned.”')
