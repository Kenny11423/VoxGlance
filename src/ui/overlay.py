"""High-performance 60 FPS Transparent & Click-Through Overlay window using PyQt6."""

import time
from typing import List, Optional
from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QMainWindow

from src.core.ipc import VisualBoundingBox
from src.ui.collision import CollisionResolver


class TransparentOverlayWindow(QMainWindow):
    """Transparent, frameless, click-through overlay window for live subtitles and OCR."""

    def __init__(
        self,
        font_size: int = 18,
        subtitle_timeout_sec: float = 4.0,
        enable_collision_check: bool = True,
    ):
        super().__init__()
        self.font_size = font_size
        self.subtitle_timeout_sec = subtitle_timeout_sec
        self.enable_collision_check = enable_collision_check
        self.resolver = CollisionResolver()

        # State
        self.current_subtitle: str = ""
        self.is_partial: bool = False
        self.subtitle_updated_time: float = 0.0
        self.ocr_boxes: List[VisualBoundingBox] = []

        self.setWindowTitle("OmniTranslate Overlay")
        self.setStyleSheet("background: transparent;")
        self._apply_hyprland_rules()
        self._init_window_flags()
        self._init_timers()

    def _apply_hyprland_rules(self) -> None:
        """Register dynamic Hyprland window rules to eliminate blur, shadow, and borders."""
        import os
        import shutil
        import subprocess

        if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") or "Hyprland" in os.environ.get("XDG_CURRENT_DESKTOP", ""):
            if shutil.which("hyprctl"):
                for rule in [
                    "match:title ^(OmniTranslate Overlay)$, float on",
                    "match:title ^(OmniTranslate Overlay)$, pin on",
                    "match:title ^(OmniTranslate Overlay)$, no_blur on",
                    "match:title ^(OmniTranslate Overlay)$, no_shadow on",
                    "match:title ^(OmniTranslate Overlay)$, no_anim on",
                    "match:title ^(OmniTranslate Overlay)$, no_initial_focus on",
                    "match:title ^(OmniTranslate Overlay)$, no_focus on",
                    "match:title ^(OmniTranslate Overlay)$, move 0 0",
                    "match:title ^(OmniTranslate Overlay)$, size 100% 100%",
                ]:
                    try:
                        subprocess.run(["hyprctl", "keyword", "windowrule", rule], capture_output=True, timeout=1.0)
                    except Exception:
                        pass

    def _init_window_flags(self) -> None:
        """Configure Qt window attributes for transparent click-through display."""
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # Full screen geometry
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

    def _enable_click_through(self) -> None:
        """Hardware-level click-through enabling for Windows (Win32) and Linux (XShape)."""
        import sys

        handle = self.windowHandle()
        if not handle:
            return

        # 1. Windows: WS_EX_TRANSPARENT | WS_EX_LAYERED
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(handle.winId())
                GWL_EXSTYLE = -20
                WS_EX_TRANSPARENT = 0x00000020
                WS_EX_LAYERED = 0x00080000
                user32 = ctypes.windll.user32
                style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED)
            except Exception:
                pass

        # 2. Linux (X11 / XWayland): XShapeCombineRectangles with ShapeInput
        elif sys.platform.startswith("linux"):
            try:
                from PyQt6.QtWidgets import QApplication
                app = QApplication.instance()
                if app and app.platformName() == "xcb":
                    import ctypes
                    x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
                    xext = ctypes.cdll.LoadLibrary("libXext.so.6")
                    display = x11.XOpenDisplay(None)
                    if display:
                        win_id = int(handle.winId())
                        # ShapeInput = 2, ShapeSet = 0
                        xext.XShapeCombineRectangles(display, win_id, 2, 0, 0, None, 0, 0, 0)
                        x11.XFlush(display)
                        x11.XCloseDisplay(display)
            except Exception:
                pass

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(100, self._enable_click_through)

    def _init_timers(self) -> None:
        """Periodic refresh timer to ensure smooth 60 FPS repaint loop."""
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self._check_timeouts_and_repaint)
        self.render_timer.start(16)  # ~60 FPS (16.6ms)

    def _check_timeouts_and_repaint(self) -> None:
        # Auto-clear subtitle if silent for more than subtitle_timeout_sec
        if self.current_subtitle and (time.time() - self.subtitle_updated_time > self.subtitle_timeout_sec):
            self.current_subtitle = ""
            self.update()

        # Auto-expire OCR boxes older than 3 seconds
        now = time.time()
        active_boxes = [b for b in self.ocr_boxes if (now - b.timestamp) < 3.0]
        if len(active_boxes) != len(self.ocr_boxes):
            self.ocr_boxes = active_boxes
            self.update()

    def update_subtitle(self, text: str, is_partial: bool = False) -> None:
        """Set new live subtitle tokens and trigger redraw."""
        self.current_subtitle = text
        self.is_partial = is_partial
        self.subtitle_updated_time = time.time()
        self.update()

    def update_ocr_boxes(self, boxes: List[VisualBoundingBox]) -> None:
        """Update active OCR text overlays."""
        self.ocr_boxes = boxes
        self.update()

    def paintEvent(self, event) -> None:
        """Render subtitles and OCR overlays using QPainter."""
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        screen_w = self.width()
        screen_h = self.height()

        # 1. Render OCR Bounding Boxes
        for box in self.ocr_boxes:
            self._draw_ocr_box(painter, box)

        # 2. Render Live Audio Subtitle
        if self.current_subtitle:
            self._draw_subtitle(painter, screen_w, screen_h)

        painter.end()

    def _draw_ocr_box(self, painter: QPainter, box: VisualBoundingBox) -> None:
        """Draw translated text directly replacing on-screen text."""
        font = QFont("Sans-Serif", 13, QFont.Weight.Bold)
        painter.setFont(font)

        # Background badge
        bg_rect = QRect(box.x, box.y, max(box.width, 100), max(box.height, 28))
        painter.setBrush(QBrush(QColor(15, 23, 42, 220)))  # Slate 900 semi-transparent
        painter.setPen(QPen(QColor(56, 189, 248, 200), 1.5))  # Cyan border
        painter.drawRoundedRect(bg_rect, 4, 4)

        # Text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, box.translated_text)

    def _draw_subtitle(self, painter: QPainter, screen_w: int, screen_h: int) -> None:
        """Draw modern streaming subtitle pill at bottom or top (if collision)."""
        font = QFont("Sans-Serif", self.font_size, QFont.Weight.Bold)
        painter.setFont(font)

        metrics = painter.fontMetrics()
        wrap_flags = int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap)
        max_w = int(screen_w * 0.75)
        text_bound = metrics.boundingRect(QRect(0, 0, max_w, 2000), wrap_flags, self.current_subtitle)
        sub_w = min(max(text_bound.width() + 40, 300), max_w)
        sub_h = text_bound.height() + 24

        # Compute position with Collision Resolver
        if self.enable_collision_check:
            sub_x, sub_y, is_top = self.resolver.resolve_position(
                screen_w, screen_h, sub_w, sub_h, self.ocr_boxes
            )
        else:
            sub_x = (screen_w - sub_w) // 2
            sub_y = int(screen_h * 0.85)
            is_top = False

        pill_rect = QRect(sub_x, sub_y, sub_w, sub_h)

        # Pill background: dark translucent capsule
        bg_color = QColor(10, 10, 10, 200)
        border_color = QColor(250, 204, 21, 180) if self.is_partial else QColor(255, 255, 255, 120)

        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.5))
        painter.drawRoundedRect(pill_rect, 12, 12)

        # Subtitle Text with subtle glowing shadow
        # Shadow
        painter.setPen(QColor(0, 0, 0, 220))
        shadow_rect = pill_rect.translated(1, 1)
        painter.drawText(shadow_rect, wrap_flags, self.current_subtitle)

        # Fore text (Yellow for partial stream, White for committed text)
        fore_color = QColor(254, 240, 138) if self.is_partial else QColor(255, 255, 255)
        painter.setPen(fore_color)
        painter.drawText(pill_rect, wrap_flags, self.current_subtitle)

