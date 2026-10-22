"""Unit tests for Settings Window and Specialized Mode Switching."""

import pytest
from PyQt6.QtWidgets import QApplication
import sys

from src.core.config import AppConfig, MODE_PRESETS
from src.ui.settings_window import SettingsWindow
from src.visual.stitcher import SmartTextStitcher
from src.core.context_engine import SemanticContextEngine, SemanticDomain
from src.core.tone_processor import ToneProcessor
from src.ui.overlay import TransparentOverlayWindow


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication instance exists for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_mode_presets_definitions():
    """Verify all 4 specialized modes are fully specified with no emojis."""
    assert "novel" in MODE_PRESETS
    assert "comic" in MODE_PRESETS
    assert "document" in MODE_PRESETS
    assert "game" in MODE_PRESETS

    # Check that labels are clean text (no emojis)
    for key, preset in MODE_PRESETS.items():
        assert preset.label in ["Tiểu thuyết", "Truyện tranh", "Tài liệu", "Trò chơi"]
        assert preset.stitcher_multiplier > 0
        assert preset.ocr_det_limit >= 720
        assert preset.overlay_style in ["solid", "comic_bubble", "document_flat", "game_hud_translucent"]


def test_stitcher_apply_preset():
    """Verify stitcher line tolerance adapts to different modes."""
    stitcher = SmartTextStitcher()

    stitcher.apply_preset("novel")
    assert stitcher.line_height_multiplier == 0.85
    assert stitcher.max_column_drift == 50

    stitcher.apply_preset("comic")
    assert stitcher.line_height_multiplier == 0.45
    assert stitcher.max_column_drift == 35

    stitcher.apply_preset("game")
    assert stitcher.line_height_multiplier == 0.40
    assert stitcher.max_column_drift == 30

    stitcher.apply_preset("document")
    assert stitcher.line_height_multiplier == 0.65


def test_context_engine_mode_priority():
    """Verify context engine locks/prioritizes target domain when mode is active."""
    ce = SemanticContextEngine()

    ce.set_mode("game")
    # General sentence without strong cues should prioritize GAMING_RPG in game mode
    assert ce.detect_domain("They were preparing the equipment.") == SemanticDomain.GAMING_RPG

    ce.set_mode("document")
    assert ce.detect_domain("They were preparing the equipment.") == SemanticDomain.OFFICE_ADMIN


def test_overlay_style_and_toast(qapp):
    """Verify overlay accepts styles and displays clean text toast."""
    overlay = TransparentOverlayWindow()

    overlay.set_overlay_style("comic_bubble")
    assert overlay.overlay_style == "comic_bubble"

    overlay.set_overlay_style("game_hud_translucent")
    assert overlay.overlay_style == "game_hud_translucent"

    overlay.show_toast("Chế độ: Tiểu thuyết")
    assert overlay._toast_message == "Chế độ: Tiểu thuyết"


def test_settings_window_interactions(qapp):
    """Verify SettingsWindow correctly invokes callbacks and manages modes."""
    config = AppConfig()
    captured_modes = []
    captured_fonts = []
    captured_engines = []

    win = SettingsWindow(
        config=config,
        on_mode_changed=lambda m: captured_modes.append(m),
        on_font_size_changed=lambda f: captured_fonts.append(f),
        on_engine_changed=lambda e: captured_engines.append(e),
    )

    # Check window title has no emojis
    assert "OmniTranslator - Cài Đặt" in win.windowTitle()

    # Change mode
    win.set_active_mode("game")
    assert win.current_mode == "game"

    # Font slider
    win._on_font_slider_changed(18)
    assert 18 in captured_fonts

    # Engine toggled
    win._on_engine_toggled("local", True)
    assert "local" in captured_engines
