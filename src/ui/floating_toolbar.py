"""Mini Floating Toolbar for On-Demand Screen Translation and Region Control."""

from typing import Callable, Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QApplication
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QCursor


class MiniFloatingToolbar(QWidget):
    """Sleek, draggable semi-transparent floating control pill for reading and gaming."""

    def __init__(
        self,
        on_translate_snapshot: Callable[[], None],
        on_select_region: Callable[[], None],
        on_toggle_visibility: Callable[[], None],
        on_open_settings: Optional[Callable[[], None]] = None,
    ):
        super().__init__()
        self.on_translate_snapshot = on_translate_snapshot
        self.on_select_region = on_select_region
        self.on_toggle_visibility = on_toggle_visibility
        self.on_open_settings = on_open_settings

        self._drag_start_pos: Optional[QPoint] = None
        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Style sheet for warm soft light golden wood pill
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(250, 246, 238, 245);
                border: 1px solid rgba(220, 206, 182, 220);
                border-radius: 16px;
            }
            QPushButton {
                background-color: #FFFDF9;
                color: #362B20;
                border: 1px solid #E2D7C3;
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F4ECE0;
                border-color: #C28B38;
                color: #20170F;
            }
            QPushButton:pressed {
                background-color: #C28B38;
                color: #FFFFFF;
                border-color: #9E671D;
            }
        """)

        # Button 1: Instant Snapshot Translate
        self.btn_snap = QPushButton("Dịch Trang Này")
        self.btn_snap.setToolTip("Chụp & dịch tức thì trang hiện tại")
        self.btn_snap.clicked.connect(self._handle_snapshot)
        layout.addWidget(self.btn_snap)

        # Button 2: Re-select Region (ROI)
        self.btn_roi = QPushButton("Chọn Vùng")
        self.btn_roi.setToolTip("Dùng chuột kéo chọn vùng mới")
        self.btn_roi.clicked.connect(self._handle_reselect)
        layout.addWidget(self.btn_roi)

        # Button 3: Toggle Hide/Show Overlay
        self.btn_toggle = QPushButton("Ẩn / Hiện")
        self.btn_toggle.setToolTip("Tạm ẩn lớp dịch để xem chữ gốc tiếng Anh")
        self.btn_toggle.clicked.connect(self._handle_toggle)
        layout.addWidget(self.btn_toggle)

        # Button 4: Settings Window
        self.btn_settings = QPushButton("Cài Đặt")
        self.btn_settings.setToolTip("Mở cửa sổ Cài Đặt và Chế độ dịch")
        if self.on_open_settings:
            self.btn_settings.clicked.connect(self.on_open_settings)
        layout.addWidget(self.btn_settings)

        # Position at top-right corner of screen
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.move(geo.width() - 420, 45)

        # Keyboard shortcuts
        from PyQt6.QtGui import QKeySequence, QShortcut
        self.sc_f9 = QShortcut(QKeySequence("F9"), self)
        self.sc_f9.activated.connect(self._handle_snapshot)
        self.sc_esc = QShortcut(QKeySequence("Escape"), self)
        self.sc_esc.activated.connect(self._handle_toggle)
        self.sc_r = QShortcut(QKeySequence("r"), self)
        self.sc_r.activated.connect(self._handle_reselect)

    def _handle_snapshot(self) -> None:
        if self.on_translate_snapshot:
            self.btn_snap.setText("Đang dịch...")
            QApplication.processEvents()
            import threading
            from PyQt6.QtCore import QTimer
            def _worker():
                try:
                    self.on_translate_snapshot()
                finally:
                    QTimer.singleShot(0, lambda: self.btn_snap.setText("Dịch Trang Này"))
            threading.Thread(target=_worker, daemon=True).start()

    def _handle_reselect(self) -> None:
        if self.on_select_region:
            self.on_select_region()

    def _handle_toggle(self) -> None:
        if self.on_toggle_visibility:
            self.on_toggle_visibility()


    def mousePressEvent(self, event):
        """Allow dragging the toolbar anywhere on screen."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_start_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
