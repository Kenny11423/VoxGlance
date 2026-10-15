"""Interactive Region of Interest (ROI) Selector for Game Dialogue & Document Translation."""

from typing import Optional, Tuple
from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget


class RegionSelectorWidget(QWidget):
    """Semi-transparent full-screen overlay allowing click-and-drag ROI selection."""

    # Signal emitted when a valid region is selected: (x, y, width, height)
    region_selected = pyqtSignal(int, int, int, int)
    cancelled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.start_point: Optional[QPoint] = None
        self.current_point: Optional[QPoint] = None
        self.is_selecting = False

        self._init_window()

    def _init_window(self) -> None:
        """Set up frameless, transparent, on-top window covering all screens."""
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

    def mousePressEvent(self, event) -> None:
        """Handle mouse press to start selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.pos()
            self.current_point = event.pos()
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event) -> None:
        """Update current drag box coordinates."""
        if self.is_selecting:
            self.current_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        """Finish selection and emit region coordinates."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            if self.start_point and self.current_point:
                rect = self._get_selection_rect()
                if rect.width() > 30 and rect.height() > 15:
                    self.region_selected.emit(rect.x(), rect.y(), rect.width(), rect.height())
                else:
                    self.cancelled.emit()
            self.close()

    def keyPressEvent(self, event) -> None:
        """Press Escape to cancel selection."""
        if event.key() == Qt.Key.Key_Escape:
            self.is_selecting = False
            self.cancelled.emit()
            self.close()

    def _get_selection_rect(self) -> QRect:
        """Normalize start and current points into a positive QRect."""
        if not self.start_point or not self.current_point:
            return QRect()
        x = min(self.start_point.x(), self.current_point.x())
        y = min(self.start_point.y(), self.current_point.y())
        w = abs(self.current_point.x() - self.start_point.x())
        h = abs(self.current_point.y() - self.start_point.y())
        return QRect(x, y, w, h)

    def paintEvent(self, event) -> None:
        """Draw dimmed background with clear cutout for selection box."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Dim entire screen
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        # 2. Draw instructions banner at top
        banner_rect = QRect(0, 20, self.width(), 45)
        painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255, 240))
        painter.drawText(
            banner_rect,
            Qt.AlignmentFlag.AlignCenter,
            "Kéo chuột chọn khung thoại game hoặc vùng đọc tài liệu (Nhấn Esc để hủy)",
        )

        # 3. Draw active selection box cutout and neon border
        if self.is_selecting:
            rect = self._get_selection_rect()
            if not rect.isEmpty():
                # Cutout clear hole
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                painter.fillRect(rect, Qt.GlobalColor.transparent)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

                # Neon Cyan Border
                pen = QPen(QColor(56, 189, 248), 2, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.drawRect(rect)

                # Size tooltip badge
                size_text = f"{rect.width()} x {rect.height()}"
                badge_rect = QRect(rect.x(), max(0, rect.y() - 25), 90, 22)
                painter.setBrush(QBrush(QColor(15, 23, 42, 220)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(badge_rect, 3, 3)
                painter.setPen(QColor(56, 189, 248))
                painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, size_text)

        painter.end()
