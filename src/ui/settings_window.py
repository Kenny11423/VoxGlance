"""Settings and Translation Mode Configuration Window."""

from typing import Callable, Optional
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QSlider,
    QGroupBox,
    QFrame,
    QApplication,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCloseEvent

from src.core.config import MODE_PRESETS, AppConfig


class SettingsWindow(QWidget):
    """Clean, professional Settings Window that lives in the OS taskbar."""

    def __init__(
        self,
        config: AppConfig,
        on_mode_changed: Optional[Callable[[str], None]] = None,
        on_font_size_changed: Optional[Callable[[int], None]] = None,
        on_engine_changed: Optional[Callable[[str], None]] = None,
        on_translate_now: Optional[Callable[[], None]] = None,
        on_select_roi: Optional[Callable[[], None]] = None,
        on_toggle_visibility: Optional[Callable[[], None]] = None,
    ):
        super().__init__()
        self.config = config
        self.on_mode_changed = on_mode_changed
        self.on_font_size_changed = on_font_size_changed
        self.on_engine_changed = on_engine_changed
        self.on_translate_now = on_translate_now
        self.on_select_roi = on_select_roi
        self.on_toggle_visibility = on_toggle_visibility

        self.current_mode = getattr(config.audio.translation, "mode", "novel")
        self._init_ui()

    def _init_ui(self) -> None:
        # Standard desktop application window visible in the OS taskbar
        self.setWindowTitle("OmniTranslator - Cài Đặt")
        self.resize(540, 640)
        self.setMinimumSize(500, 580)

        # Ensure it is a standard top-level window in the taskbar
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        # Clean dark desktop styling without emojis or icons
        self.setStyleSheet("""
            QWidget {
                background-color: #161A22;
                color: #E6EDF3;
                font-family: 'Noto Sans', sans-serif;
            }
            QGroupBox {
                border: 1px solid #30363D;
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 16px;
                font-weight: bold;
                font-size: 13px;
                color: #58A6FF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
            }
            QRadioButton {
                font-size: 13px;
                font-weight: normal;
                color: #C9D1D9;
                padding: 4px;
            }
            QRadioButton:hover {
                color: #58A6FF;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #8B949E;
                border-radius: 8px;
                background-color: #0D1117;
            }
            QRadioButton::indicator:checked {
                background-color: #1F6FEB;
                border: 2px solid #58A6FF;
            }
            QSlider::groove:horizontal {
                border: 1px solid #30363D;
                height: 6px;
                background: #21262D;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #1F6FEB;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #58A6FF;
                border: 1px solid #C9D1D9;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363D;
                border-color: #8B949E;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #1F6FEB;
                border-color: #58A6FF;
            }
            QPushButton#btnPrimary {
                background-color: #238636;
                border-color: #2EA043;
                color: #FFFFFF;
            }
            QPushButton#btnPrimary:hover {
                background-color: #2EA043;
            }
            QLabel {
                font-size: 12px;
                color: #8B949E;
            }
            QLabel#lblStatus {
                font-size: 12px;
                color: #3FB950;
                font-weight: bold;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Header Title
        lbl_title = QLabel("Cài Đặt Hệ Thống Dịch Thuật")
        lbl_title.setFont(QFont("Noto Sans", 15, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #FFFFFF; font-size: 16px;")
        main_layout.addWidget(lbl_title)

        # SECTION 1: Mode Selection Group
        grp_modes = QGroupBox("Chế độ Dịch thuật Chuyên biệt")
        modes_layout = QVBoxLayout(grp_modes)
        modes_layout.setSpacing(8)

        self.mode_group = QButtonGroup(self)
        self.radio_buttons = {}

        mode_options = [
            ("novel", "Tiểu thuyết (Web novel, truyện chữ)", "Tối ưu câu văn mượt mà, gộp toàn bộ khổ văn, che sạch chữ gốc."),
            ("comic", "Truyện tranh (Manga, Manhwa)", "Bắt trọn cụm bong bóng thoại, căn giữa chữ, mặt nạ bo tròn."),
            ("document", "Tài liệu (Báo cáo, sách, kỹ thuật)", "Văn phong học thuật chuẩn mực, bảo toàn mục 1. 2., danh sách và bảng."),
            ("game", "Trò chơi (Game 3D, HUD)", "Độ trễ thấp nhất (<20ms), thuật ngữ game, mặt nạ mờ không che khuất màn chơi."),
        ]

        for mode_key, mode_title, mode_desc in mode_options:
            v_box = QVBoxLayout()
            v_box.setSpacing(2)

            rb = QRadioButton(mode_title)
            rb.setChecked(self.current_mode == mode_key)
            self.mode_group.addButton(rb)
            self.radio_buttons[mode_key] = rb

            lbl_desc = QLabel(f"    {mode_desc}")
            lbl_desc.setStyleSheet("color: #8B949E; font-size: 11px;")

            v_box.addWidget(rb)
            v_box.addWidget(lbl_desc)
            modes_layout.addLayout(v_box)

            # Connect selection
            rb.toggled.connect(lambda checked, m=mode_key: self._on_mode_toggled(m, checked))

        main_layout.addWidget(grp_modes)

        # SECTION 2: Translation Engine Group
        grp_engine = QGroupBox("Động cơ Dịch thuật")
        engine_layout = QVBoxLayout(grp_engine)

        self.engine_group = QButtonGroup(self)
        current_engine = getattr(self.config.audio.translation, "engine", "hybrid")

        engines = [
            ("local", "Cục bộ Offline (CTranslate2 - GPU RTX 2050)", "Chạy hoàn toàn trên máy, không kết nối mạng, tốc độ cao."),
            ("hybrid", "Hybrid Tự động (Cục bộ + Dự phòng Cloud)", "Ưu tiên dịch offline, dự phòng khi gặp ngôn ngữ hiếm."),
            ("llm", "Mô hình LLM (Ollama cục bộ / Gemini API)", "Suy luận ngữ cảnh sâu bằng mô hình ngôn ngữ lớn."),
        ]

        for eng_key, eng_title, eng_desc in engines:
            v_box = QVBoxLayout()
            v_box.setSpacing(2)

            rb_eng = QRadioButton(eng_title)
            rb_eng.setChecked(current_engine == eng_key)
            self.engine_group.addButton(rb_eng)

            lbl_eng_desc = QLabel(f"    {eng_desc}")
            lbl_eng_desc.setStyleSheet("color: #8B949E; font-size: 11px;")

            v_box.addWidget(rb_eng)
            v_box.addWidget(lbl_eng_desc)
            engine_layout.addLayout(v_box)

            rb_eng.toggled.connect(lambda checked, e=eng_key: self._on_engine_toggled(e, checked))

        main_layout.addWidget(grp_engine)

        # SECTION 3: Display Typography
        grp_display = QGroupBox("Hiển thị & Cỡ chữ")
        display_layout = QHBoxLayout(grp_display)

        lbl_font = QLabel("Cỡ chữ hiển thị:")
        self.slider_font = QSlider(Qt.Orientation.Horizontal)
        self.slider_font.setRange(10, 26)
        current_font = getattr(self.config.ui, "font_size", 14)
        self.slider_font.setValue(current_font)

        self.lbl_font_val = QLabel(f"{current_font} pt")
        self.lbl_font_val.setStyleSheet("color: #58A6FF; font-weight: bold; min-width: 40px;")

        self.slider_font.valueChanged.connect(self._on_font_slider_changed)

        display_layout.addWidget(lbl_font)
        display_layout.addWidget(self.slider_font)
        display_layout.addWidget(self.lbl_font_val)

        main_layout.addWidget(grp_display)

        # SECTION 4: Direct Translation Actions
        grp_actions = QGroupBox("Thao Tác Trực Tiếp")
        actions_layout = QHBoxLayout(grp_actions)
        actions_layout.setSpacing(10)

        btn_action_translate = QPushButton("Dịch Trang Này")
        btn_action_translate.setObjectName("btnPrimary")
        btn_action_translate.clicked.connect(self._handle_translate_now)

        btn_action_roi = QPushButton("Chọn Vùng Dịch")
        btn_action_roi.clicked.connect(self._handle_select_roi)

        btn_action_toggle = QPushButton("Ẩn / Hiện Dịch")
        btn_action_toggle.clicked.connect(self._handle_toggle_vis)

        actions_layout.addWidget(btn_action_translate)
        actions_layout.addWidget(btn_action_roi)
        actions_layout.addWidget(btn_action_toggle)

        main_layout.addWidget(grp_actions)

        # SECTION 5: Hardware & System Status
        grp_status = QGroupBox("Thông tin Hệ thống")
        status_layout = QVBoxLayout(grp_status)
        status_layout.setSpacing(4)

        lbl_gpu = QLabel("Phần cứng: NVIDIA GeForce RTX 2050 (4GB VRAM)")
        lbl_mode_status = QLabel(f"Chế độ hiện tại: {self.current_mode.capitalize()}")
        self.lbl_mode_status = lbl_mode_status

        lbl_offline = QLabel("Trạng thái mạng: 100% Offline (Không gọi API bên ngoài)")
        lbl_offline.setObjectName("lblStatus")

        status_layout.addWidget(lbl_gpu)
        status_layout.addWidget(lbl_mode_status)
        status_layout.addWidget(lbl_offline)

        main_layout.addWidget(grp_status)

        # Bottom Button Bar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        btn_minimize = QPushButton("Thu nhỏ xuống Taskbar")
        btn_minimize.clicked.connect(self.showMinimized)

        btn_close = QPushButton("Ẩn Cửa Sổ")
        btn_close.clicked.connect(self.hide)

        btn_apply = QPushButton("Bắt đầu Dịch & Thu nhỏ")
        btn_apply.setObjectName("btnPrimary")
        btn_apply.clicked.connect(self._handle_apply)

        btn_bar.addWidget(btn_minimize)
        btn_bar.addWidget(btn_close)
        btn_bar.addStretch()
        btn_bar.addWidget(btn_apply)

        main_layout.addLayout(btn_bar)

        # Center window on screen
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                max(0, (geo.width() - self.width()) // 2),
                max(0, (geo.height() - self.height()) // 2),
            )

    def _on_mode_toggled(self, mode: str, checked: bool) -> None:
        if checked:
            self.current_mode = mode
            self.lbl_mode_status.setText(f"Chế độ hiện tại: {mode.capitalize()}")
            if self.on_mode_changed:
                self.on_mode_changed(mode)

    def _on_engine_toggled(self, engine: str, checked: bool) -> None:
        if checked and self.on_engine_changed:
            self.on_engine_changed(engine)

    def _on_font_slider_changed(self, val: int) -> None:
        self.lbl_font_val.setText(f"{val} pt")
        if self.on_font_size_changed:
            self.on_font_size_changed(val)

    def _handle_apply(self) -> None:
        if self.on_mode_changed:
            self.on_mode_changed(self.current_mode)
        # Minimize window to taskbar after apply
        self.showMinimized()

    def _handle_translate_now(self) -> None:
        if self.on_translate_now:
            self.on_translate_now()

    def _handle_select_roi(self) -> None:
        if self.on_select_roi:
            self.on_select_roi()

    def _handle_toggle_vis(self) -> None:
        if self.on_toggle_visibility:
            self.on_toggle_visibility()

    def set_active_mode(self, mode: str) -> None:
        """Programmatically update active mode radio button."""
        clean_mode = mode.lower().strip()
        if clean_mode in self.radio_buttons:
            self.current_mode = clean_mode
            self.radio_buttons[clean_mode].setChecked(True)
            self.lbl_mode_status.setText(f"Chế độ hiện tại: {clean_mode.capitalize()}")

    def show_and_activate(self) -> None:
        """Show window, restore from minimized, and bring to foreground."""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Minimize to taskbar on close click rather than terminating background service."""
        event.ignore()
        self.showMinimized()
