#!/usr/bin/env python3
"""Main Application Entry Point: Real-time Multimodal Live Translator (Visual & Audio)."""

import argparse
import os
import signal
import sys
import threading
import time
from pathlib import Path
from loguru import logger

if sys.platform.startswith("linux"):
    # Ensure XCB/XWayland platform on Linux to enable hardware XShape click-through
    os.environ["QT_QPA_PLATFORM"] = "xcb"

# Cleanly handle Ctrl+C in terminal
signal.signal(signal.SIGINT, signal.SIG_DFL)

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import load_config
from src.core.memory import MemoryController
from src.core.ipc import IPCChannels, SubtitleToken, VisualBoundingBox
from src.core.translator import HybridTranslator
from src.core.orchestrator import VoxGlanceOrchestrator


def run_demo_overlay(config):
    """Run interactive demonstration of Transparent Overlay and Collision Resolver."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    from src.ui.overlay import TransparentOverlayWindow

    app = QApplication(sys.argv)

    sig_timer = QTimer()
    sig_timer.start(250)
    sig_timer.timeout.connect(lambda: None)

    overlay = TransparentOverlayWindow(
        font_size=config.ui.font_size,
        subtitle_timeout_sec=config.ui.auto_hide_seconds,
        enable_collision_check=config.ui.collision_detection,
    )
    overlay.show()

    logger.info("Transparent Overlay running. Showing live demo simulation in 1 second...")

    def _demo_feed():
        time.sleep(1.0)
        demo_phrases = [
            ("Dịch thuật trực quan thời gian thực", True),
            ("Dịch thuật trực quan thời gian thực – Thay thế chữ tại chỗ thẩm mỹ cao", False),
            ("Không tạo hộp đen, tự động co giãn font vừa khít bounding box", False),
            ("An toàn 100% với Anti-cheat, VRAM duy trì dưới 850MB", False),
        ]

        for text, is_partial in demo_phrases:
            overlay.update_subtitle(text, is_partial=is_partial)
            time.sleep(1.5)

        # Demo In-place Aesthetic OCR Box
        screen_w = overlay.width()
        screen_h = overlay.height()
        box_y = int(screen_h * 0.75)

        overlay.update_ocr_boxes([
            VisualBoundingBox(
                x=(screen_w - 450) // 2,
                y=box_y,
                width=450,
                height=40,
                original_text="Cast Fireball on the ancient dragon.",
                translated_text="Thi triển Quả Cầu Lửa vào rồng cổ đại.",
                bg_color=(25, 32, 48),
                text_color=(255, 255, 255),
                outline_color=(10, 10, 15),
                font_size=13,
            )
        ])
        overlay.update_subtitle("Lớp che tiệp màu nền và chữ tiếng Việt tự co giãn vừa vặn!", False)

        time.sleep(4.0)
        logger.info("Demo complete. Overlay running. Press Ctrl+C in terminal to exit.")

    thread = threading.Thread(target=_demo_feed, daemon=True)
    thread.start()

    sys.exit(app.exec())


def run_visual_mode(config, roi=None):
    """Run dedicated On-Screen In-Place Visual Live Translator for Game and Documents."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    from src.ui.overlay import TransparentOverlayWindow
    from src.ui.region_selector import RegionSelectorWidget

    app = QApplication(sys.argv)

    sig_timer = QTimer()
    sig_timer.start(250)
    sig_timer.timeout.connect(lambda: None)

    overlay = TransparentOverlayWindow(
        font_size=config.ui.font_size,
        subtitle_timeout_sec=config.ui.auto_hide_seconds,
        enable_collision_check=config.ui.collision_detection,
    )
    overlay.show()

    orchestrator = VoxGlanceOrchestrator(
        config=config,
        overlay=overlay,
        enable_audio=False,  # Audio off in visual-only mode
        enable_ocr=True,
    )
    if roi:
        orchestrator.set_roi(roi)

    orchestrator.start()

    logger.info("=" * 65)
    logger.info("  VISUAL IN-PLACE LIVE TRANSLATOR ACTIVE")
    logger.info("  Chế độ dịch trực quan thay thế tại chỗ cho Game & Tài liệu.")
    logger.info(f"  Vùng quét (ROI): {roi if roi else 'Toàn màn hình (Full Screen)'}")
    logger.info("  Nhấn Ctrl+C trong terminal để thoát.")
    logger.info("=" * 65)

    try:
        app.exec()
    finally:
        orchestrator.stop()


def run_live_mode(config, audio_source: str = "auto", enable_ocr: bool = True):
    """Run full live multimodal translation with audio capture, OCR, and transparent overlay."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    from src.ui.overlay import TransparentOverlayWindow

    app = QApplication(sys.argv)

    sig_timer = QTimer()
    sig_timer.start(250)
    sig_timer.timeout.connect(lambda: None)

    overlay = TransparentOverlayWindow(
        font_size=config.ui.font_size,
        subtitle_timeout_sec=config.ui.auto_hide_seconds,
        enable_collision_check=config.ui.collision_detection,
    )
    overlay.show()
    overlay.update_subtitle("🎙️ Hệ thống đang lắng nghe... (Hãy mở video/game hoặc nói vào mic)", is_partial=True)

    orchestrator = VoxGlanceOrchestrator(
        config=config,
        overlay=overlay,
        audio_source=audio_source,
        enable_ocr=enable_ocr,
        enable_audio=True,
    )
    orchestrator.start()

    logger.info(f"Multimodal LIVE mode active (Audio: {audio_source}, OCR: {enable_ocr}). Press Ctrl+C to exit.")

    try:
        app.exec()
    finally:
        orchestrator.stop()


def main():
    parser = argparse.ArgumentParser(description="Real-time Multimodal Live Translator (Visual & Audio)")
    parser.add_argument(
        "--mode",
        choices=["visual", "live", "demo", "cli", "overlay"],
        default="visual",
        help="Execution mode (default: visual - In-place Screen Translation)",
    )
    parser.add_argument("--source", choices=["auto", "system", "mic"], default="auto", help="Audio source")
    parser.add_argument("--ocr", action="store_true", help="Enable on-screen Visual OCR capture")
    parser.add_argument("--no-ocr", action="store_true", help="Force disable on-screen Visual OCR capture")
    parser.add_argument("--roi", nargs=4, type=int, metavar=("X", "Y", "W", "H"), help="Set custom Region of Interest (x y width height)")
    parser.add_argument("--config", default=None, help="Path to config YAML")
    args = parser.parse_args()

    enable_ocr = args.ocr or (args.mode == "visual") and not args.no_ocr
    roi_tuple = tuple(args.roi) if args.roi else None

    config = load_config(args.config)
    logger.info(f"Loaded config. Target VRAM Cap: {config.system.target_vram_mb}MB")

    memory = MemoryController(
        target_vram_mb=config.system.target_vram_mb,
        peak_guard_buffer_mb=config.system.peak_guard_buffer_mb,
    )
    vram_status = memory.get_vram_info()
    logger.info(f"Current VRAM: {vram_status.used_mb:.1f}MB / {config.system.target_vram_mb}MB (Status: {'SAFE' if vram_status.is_safe else 'ALERT'})")

    if args.mode == "visual":
        run_visual_mode(config, roi=roi_tuple)
    elif args.mode == "live":
        run_live_mode(config, audio_source=args.source, enable_ocr=enable_ocr)
    elif args.mode in ["demo", "overlay"]:
        run_demo_overlay(config)
    else:
        logger.info(f"CLI mode started (Audio Source: {args.source}, OCR: {enable_ocr}). Listening to audio stream...")

        def _cli_subtitle(token):
            prefix = "🎙️ [Tạm thời]" if token.is_partial else "✅ [Chốt câu]"
            print(f"\n{prefix}: {token.text}", flush=True)

        orchestrator = VoxGlanceOrchestrator(
            config=config,
            overlay=None,
            audio_source=args.source,
            enable_ocr=enable_ocr,
        )
        if orchestrator.audio_pipeline:
            orchestrator.audio_pipeline.on_subtitle = _cli_subtitle
        orchestrator.start()

        print("\n" + "=" * 65)
        print("  CLI Active | Đang nghe âm thanh trực tiếp")
        print("  Nhấn Ctrl+C để dừng")
        print("=" * 65 + "\n")

        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Application terminated by user.")
        finally:
            orchestrator.stop()
            memory.shutdown()


if __name__ == "__main__":
    main()
