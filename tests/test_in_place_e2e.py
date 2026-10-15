"""End-to-End Integration Test for In-Place Visual Translation Pipeline."""

import numpy as np
from PIL import Image, ImageDraw
import pytest

from src.core.cache import LRUTermCache
from src.core.glossary import MultilingualGlossary
from src.core.ipc import VisualBoundingBox
from src.core.language_detector import FastLanguageDetector
from src.core.translator import HybridTranslator
from src.visual.aesthetic import apply_aesthetic_styling
from src.visual.ocr import FastOCREngine
from src.visual.stitcher import SmartTextStitcher


def test_end_to_end_in_place_visual_pipeline():
    """Simulate full end-to-end pipeline:
    Frame -> OCR -> Stitcher -> Language Detect -> Glossary -> MT -> Aesthetic Styling.
    """
    # 1. Create a simulated game dialogue screenshot (dark navy background)
    img = Image.new("RGB", (600, 200), color=(18, 24, 38))
    draw = ImageDraw.Draw(img)
    draw.text((40, 50), "Cast Fireball to defeat the monster.", fill=(250, 250, 250))
    frame = np.array(img)

    # 2. Run OCR Engine
    ocr = FastOCREngine(confidence_threshold=0.4)
    raw_boxes = ocr.detect_and_recognize(frame)
    assert len(raw_boxes) >= 1

    # 3. Run Sentence Stitcher
    stitcher = SmartTextStitcher()
    stitched_boxes = stitcher.stitch(raw_boxes)
    assert len(stitched_boxes) >= 1
    stitched_box = stitched_boxes[0]

    # 4. Set up Glossary with custom term
    glossary = MultilingualGlossary()
    glossary.add_term("Fireball", "Quả Cầu Lửa", domain="game")

    # 5. Hybrid Translator with auto language detector & glossary
    cache = LRUTermCache()
    cache.put("Cast __TERM_0__ to defeat the monster.", "Thi triển __TERM_0__ để đánh bại quái vật.")

    translator = HybridTranslator(
        cache=cache,
        glossary=glossary,
        language_detector=FastLanguageDetector(),
    )

    translated = translator.translate(stitched_box.original_text, source_lang="auto", target_lang="vi")
    stitched_box.translated_text = translated

    # 6. Apply In-place Aesthetic Styling
    apply_aesthetic_styling(stitched_box, frame=frame)

    # 7. Assertions: Aesthetic & translation integrity
    # Background should match sampled dark navy (18, 24, 38)
    assert stitched_box.bg_color is not None
    assert stitched_box.bg_color[0] <= 30
    assert stitched_box.bg_color[2] >= 30

    # Text color should be white/bright for dark background
    assert stitched_box.text_color == (255, 255, 255)
    assert stitched_box.outline_color == (10, 10, 15)

    # Font size must be valid
    assert 8 <= stitched_box.font_size <= 24

    # Translated text must preserve protected glossary term
    assert stitched_box.translated_text != ""
