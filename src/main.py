#!/usr/bin/env python3
"""OmniTranslate: Main Application Entry Point."""

import argparse
import sys
import threading
import time
from pathlib import Path
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import load_config
from src.core.memory import MemoryController
from src.core.ipc import IPCChannels, SubtitleToken, VisualBoundingBox
from src.audio.capture import AudioCaptureManager
from src.audio.vad import SileroVAD
from src.audio.asr import FasterWhisperEngine
from src.core.translator import HybridTranslator


def run_demo_overlay(config):
    """Run interactive demonstration of Transparent Overlay and Collision Resolver."""
    from PyQt6.QtWidgets import QApplication
    from src.ui.overlay import TransparentOverlayWindow

    app = QApplication(sys.argv)
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
            ("Xin chào, tôi là OmniTranslate", True),
            ("Xin chào, tôi là OmniTranslate - hệ thống dịch thuật thời gian thực", False),
            ("Độ trễ xử lý cực thấp dưới 800ms", False),
            ("Mức tiêu thụ VRAM luôn duy trì dưới 950MB trên GPU RTX 2050", False),
        ]

        for text, is_partial in demo_phrases:
            overlay.update_subtitle(text, is_partial=is_partial)
            time.sleep(1.5)

        # Demo Collision Avoidance: place an OCR box at the bottom
        logger.info("Simulating OCR text detected at bottom screen. Subtitle will relocate to TOP!")
        screen_w = overlay.width()
        screen_h = overlay.height()
        box_y = int(screen_h * 0.85) - 20

        overlay.update_ocr_boxes([
            VisualBoundingBox(
                x=(screen_w - 400) // 2,
                y=box_y,
                width=400,
                height=45,
                original_text="GAME OVER / RETRY",
                translated_text="KẾT THÚC / CHƠI LẠI",
            )
        ])
        overlay.update_subtitle("Phụ đề đã tự động dời lên đỉnh màn hình để không che mất chữ OCR!", False)

        time.sleep(4.0)
        logger.info("Demo complete. Overlay running. Press Ctrl+C in terminal to exit.")

    thread = threading.Thread(target=_demo_feed, daemon=True)
    thread.start()

    sys.exit(app.exec())


def main():
    parser = argparse.ArgumentParser(description="OmniTranslate Desktop Application")
    parser.add_argument("--mode", choices=["demo", "cli", "overlay"], default="demo", help="Execution mode")
    parser.add_argument("--config", default=None, help="Path to config YAML")
    args = parser.parse_args()

    config = load_config(args.config)
    logger.info(f"Loaded OmniTranslate config. Target VRAM: {config.system.target_vram_mb}MB")

    memory = MemoryController(
        target_vram_mb=config.system.target_vram_mb,
        peak_guard_buffer_mb=config.system.peak_guard_buffer_mb,
    )
    vram_status = memory.get_vram_info()
    logger.info(f"Current VRAM: {vram_status.used_mb}MB / {config.system.target_vram_mb}MB (Status: {'SAFE' if vram_status.is_safe else 'ALERT'})")

    if args.mode in ["demo", "overlay"]:
        run_demo_overlay(config)
    else:
        logger.info("CLI mode started. Listening to audio stream...")
        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Application terminated by user.")
        finally:
            memory.shutdown()


if __name__ == "__main__":
    main()
