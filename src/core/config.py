"""Configuration loader and schema using Pydantic."""

from pathlib import Path
from typing import Literal, Optional
import yaml
from pydantic import BaseModel, Field


class SystemConfig(BaseModel):
    device: str = "cuda:0"
    target_vram_mb: int = 950
    peak_guard_buffer_mb: int = 150
    enable_cuda: bool = True
    log_level: str = "INFO"


class VadConfig(BaseModel):
    enabled: bool = True
    threshold: float = 0.5
    min_speech_duration_ms: int = 100
    min_silence_duration_ms: int = 200


class AsrConfig(BaseModel):
    model_size: str = "small"
    compute_type: str = "int8_float16"
    beam_size: int = 1
    max_vram_mb: int = 400
    language: str = "auto"


class TranslationConfig(BaseModel):
    engine: Literal["local", "cloud"] = "local"
    target_language: str = "vi"


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
    auto_hide_seconds: float = 3.0
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
