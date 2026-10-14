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
        subtitle_timeout_sec: float = 8.0,
        enable_collision_check: bool = True,
    ):
        super().__init__()
        self.font_size = font_size
        self.subtitle_timeout_sec = subtitle_timeout_sec
        self.enable_collision_check = enable_collision_check
        self.resolver = CollisionResolver()

        # 2-Line Roll-Up Subtitle State (preserves previous sentence for reading)
        self.current_subtitle: str = ""
        self.is_partial: bool = False
        self.subtitle_updated_time: float = 0.0

        self.prev_subtitle: str = ""
        self.prev_updated_time: float = 0.0
        self.committed_subtitle: str = ""
        self.committed_updated_time: float = 0.0
        self.partial_subtitle: str = ""
        self.partial_updated_time: float = 0.0

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
        now = time.time()
        changed = False

        # Expire previous committed subtitle after timeout
        if self.prev_subtitle and (now - self.prev_updated_time > self.subtitle_timeout_sec):
            self.prev_subtitle = ""
            changed = True

        # Expire latest committed subtitle after timeout
        if self.committed_subtitle and (now - self.committed_updated_time > self.subtitle_timeout_sec):
            self.committed_subtitle = ""
            changed = True

        # Expire partial streaming subtitle if silence for 3s
        if self.partial_subtitle and (now - self.partial_updated_time > 3.0):
            self.partial_subtitle = ""
            changed = True

        if not self.prev_subtitle and not self.committed_subtitle and not self.partial_subtitle:
            if self.current_subtitle:
                self.current_subtitle = ""
                changed = True

        # Auto-expire OCR boxes older than 3 seconds
        active_boxes = [b for b in self.ocr_boxes if (now - b.timestamp) < 3.0]
        if len(active_boxes) != len(self.ocr_boxes):
            self.ocr_boxes = active_boxes
            changed = True

        if changed:
            self.update()

    def update_subtitle(self, text: str, is_partial: bool = False) -> None:
        """Set new live subtitle tokens with 2-line roll-up retention."""
        now = time.time()
        self.subtitle_updated_time = now
        self.current_subtitle = text
        self.is_partial = is_partial

        if is_partial:
            self.partial_subtitle = text
            self.partial_updated_time = now
        else:
            # Full sentence committed: roll previous sentence to line 1 so user has time to read
            if self.committed_subtitle and self.committed_subtitle != text:
                self.prev_subtitle = self.committed_subtitle
                self.prev_updated_time = self.committed_updated_time

            self.committed_subtitle = text
            self.committed_updated_time = now
            self.partial_subtitle = ""  # Sentence ended, clear partial

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

        # 2. Render Live Audio Subtitles (2-Line Roll-Up)
        if self.prev_subtitle or self.committed_subtitle or self.partial_subtitle or self.current_subtitle:
            self._draw_subtitle(painter, screen_w, screen_h)

        painter.end()

    def _draw_ocr_box(self, painter: QPainter, box: VisualBoundingBox) -> None:
        """Draw translated text directly replacing on-screen text."""
        font = QFont("Sans-Serif", 13, QFont.Weight.Bold)
        painter.setFont(font)

        bg_rect = QRect(box.x, box.y, max(box.width, 100), max(box.height, 28))
        painter.setBrush(QBrush(QColor(15, 23, 42, 220)))  # Slate 900 semi-transparent
        painter.setPen(QPen(QColor(56, 189, 248, 200), 1.5))  # Cyan border
        painter.drawRoundedRect(bg_rect, 4, 4)

        painter.setPen(QColor(255, 255, 255))
        painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, box.translated_text)

    def _draw_subtitle(self, painter: QPainter, screen_w: int, screen_h: int) -> None:
        """Draw modern streaming subtitle pill supporting 2-Line Roll-Up."""
        now = time.time()
        wrap_flags = int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap)
        max_w = int(screen_w * 0.78)

        # Assemble active lines:
        lines = []
        # Line 1: Previous committed sentence (stays visible for easy reading)
        if self.prev_subtitle and (now - self.prev_updated_time <= self.subtitle_timeout_sec):
            lines.append({
                "text": self.prev_subtitle,
                "is_history": True,
                "is_partial": False,
            })

        # Line 2: Current active sentence (committed or live partial stream)
        current_text = self.partial_subtitle if self.partial_subtitle else self.committed_subtitle
        if not current_text and self.current_subtitle:
            current_text = self.current_subtitle

        if current_text and (not lines or lines[0]["text"] != current_text):
            lines.append({
                "text": current_text,
                "is_history": False,
                "is_partial": bool(self.partial_subtitle),
            })

        if not lines:
            return

        # Calculate bounding dimensions
        font_main = QFont("Sans-Serif", self.font_size, QFont.Weight.Bold)
        font_hist = QFont("Sans-Serif", max(13, self.font_size - 2), QFont.Weight.Medium)

        total_h = 20
        max_line_w = 280

        line_layouts = []
        for line in lines:
            f = font_hist if line["is_history"] else font_main
            painter.setFont(f)
            m = painter.fontMetrics()
            bound = m.boundingRect(QRect(0, 0, max_w - 40, 2000), wrap_flags, line["text"])
            line_layouts.append((line, f, bound.height()))
            total_h += bound.height() + 8
            if bound.width() + 48 > max_line_w:
                max_line_w = min(bound.width() + 48, max_w)

        sub_w = max_line_w
        sub_h = total_h

        # Compute position with Collision Resolver
        if self.enable_collision_check:
            sub_x, sub_y, is_top = self.resolver.resolve_position(
                screen_w, screen_h, sub_w, sub_h, self.ocr_boxes
            )
        else:
            sub_x = (screen_w - sub_w) // 2
            sub_y = int(screen_h * 0.85) - (sub_h - 40)
            is_top = False

        pill_rect = QRect(sub_x, sub_y, sub_w, sub_h)

        # Pill background: dark frosted glass capsule
        has_partial = any(l["is_partial"] for l in lines)
        bg_color = QColor(10, 10, 10, 215)
        border_color = QColor(250, 204, 21, 200) if has_partial else QColor(56, 189, 248, 160)

        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.5))
        painter.drawRoundedRect(pill_rect, 14, 14)

        # Render each line with appropriate styling
        curr_y = sub_y + 10
        for line, f, h in line_layouts:
            line_rect = QRect(sub_x + 20, curr_y, sub_w - 40, h)
            painter.setFont(f)

            # Shadow
            painter.setPen(QColor(0, 0, 0, 230))
            painter.drawText(line_rect.translated(1, 1), wrap_flags, line["text"])

            # Text Color
            if line["is_history"]:
                # Muted slate/white for previous sentence
                painter.setPen(QColor(203, 213, 225, 220))
            elif line["is_partial"]:
                # Warm yellow for live streaming speech
                painter.setPen(QColor(254, 240, 138, 255))
            else:
                # Bright white for latest committed sentence
                painter.setPen(QColor(255, 255, 255, 255))

            painter.drawText(line_rect, wrap_flags, line["text"])
            curr_y += h + 8

