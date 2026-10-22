"""Configuration loader and schema using Pydantic."""

from pathlib import Path
from typing import Literal, Optional
import yaml
from pydantic import BaseModel, Field


class SystemConfig(BaseModel):
    device: str = "cuda:0"
    target_vram_mb: int = 1800
    peak_guard_buffer_mb: int = 150
    enable_cuda: bool = True
    log_level: str = "INFO"


class VadConfig(BaseModel):
    enabled: bool = True
    threshold: float = 0.5
    min_speech_duration_ms: int = 100
    min_silence_duration_ms: int = 200


class AsrConfig(BaseModel):
    model_size: str = "base"
    compute_type: str = "float16"
    beam_size: int = 1
    max_vram_mb: int = 400
    language: str = "auto"


class ModePreset(BaseModel):
    name: str
    label: str
    description: str
    stitcher_multiplier: float
    ocr_det_limit: int
    overlay_style: str  # "solid", "comic_bubble", "document_flat", "game_hud_translucent"
    tone_persona: str   # "literary", "casual", "formal", "gamer"
    target_domain: str


MODE_PRESETS: dict[str, ModePreset] = {
    "novel": ModePreset(
        name="novel",
        label="Tiểu thuyết",
        description="Văn phong trau chuốt, gộp trọn khổ văn lớn, che sạch chữ gốc 100%.",
        stitcher_multiplier=0.85,
        ocr_det_limit=960,
        overlay_style="solid",
        tone_persona="literary",
        target_domain="animal_pet",
    ),
    "comic": ModePreset(
        name="comic",
        label="Truyện tranh",
        description="Nhận diện bóng thoại, căn giữa chữ, mặt nạ bo tròn mềm mại.",
        stitcher_multiplier=0.45,
        ocr_det_limit=960,
        overlay_style="comic_bubble",
        tone_persona="casual",
        target_domain="general",
    ),
    "document": ModePreset(
        name="document",
        label="Tài liệu",
        description="Văn phong học thuật, bảo vệ số thứ tự, bullet và bảng biểu.",
        stitcher_multiplier=0.65,
        ocr_det_limit=1280,
        overlay_style="document_flat",
        tone_persona="formal",
        target_domain="office_admin",
    ),
    "game": ModePreset(
        name="game",
        label="Trò chơi",
        description="Độ trễ thấp (<20ms), thuật ngữ game, mặt nạ HUD mờ không che combat.",
        stitcher_multiplier=0.40,
        ocr_det_limit=720,
        overlay_style="game_hud_translucent",
        tone_persona="gamer",
        target_domain="gaming_rpg",
    ),
}


class TranslationConfig(BaseModel):
    engine: Literal["local", "cloud", "hybrid", "llm"] = "hybrid"
    mode: Literal["novel", "comic", "document", "game"] = "novel"
    source_language: str = "auto"
    target_language: str = "vi"
    enable_glossary: bool = True
    glossary_file: Optional[str] = None
    enable_stitching: bool = True
    enable_context_engine: bool = True
    context_window_size: int = 3
    llm_provider: str = "auto"
    llm_model: Optional[str] = None
    llm_endpoint: Optional[str] = None


class AudioConfig(BaseModel):
    backend: str = "auto"
    sample_rate: int = 16000
    chunk_duration_ms: int = 250
    channels: int = 1
    vad: VadConfig = Field(default_factory=VadConfig)
    asr: AsrConfig = Field(default_factory=AsrConfig)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)


class OcrConfig(BaseModel):
    enabled: bool = True
    det_model: str = "dbnet"
    rec_model: str = "svtr"
    max_vram_mb: int = 300
    confidence_threshold: float = 0.6


class VisualCacheConfig(BaseModel):
    max_entries: int = 2000


class VisualConfig(BaseModel):
    backend: str = "auto"
    fps_limit: int = 10
    frame_diff_threshold: float = 0.05
    ocr: OcrConfig = Field(default_factory=OcrConfig)
    cache: VisualCacheConfig = Field(default_factory=VisualCacheConfig)


class UiConfig(BaseModel):
    fps: int = 60
    click_through: bool = True
    font_size: int = 18
    auto_hide_seconds: float = 7.0
    collision_detection: bool = True


class AppConfig(BaseModel):
    system: SystemConfig = Field(default_factory=SystemConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    visual: VisualConfig = Field(default_factory=VisualConfig)
    ui: UiConfig = Field(default_factory=UiConfig)


def load_config(config_path: Optional[str | Path] = None) -> AppConfig:
    """Load configuration from YAML file or return defaults."""
    if config_path is None:
        # Default search path
        default_file = Path(__file__).resolve().parent.parent.parent / "configs" / "default_config.yaml"
        if default_file.exists():
            config_path = default_file

    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return AppConfig(**data)

    return AppConfig()
