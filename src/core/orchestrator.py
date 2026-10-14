"""Core Orchestrator: synchronizes Audio Pipeline, Visual OCR, and Transparent Overlay."""

from typing import Optional
from loguru import logger

from src.audio.pipeline import AudioStreamingPipeline
from src.core.config import AppConfig
from src.core.memory import MemoryController
from src.core.translator import HybridTranslator
from src.ui.overlay import TransparentOverlayWindow
from src.visual.pipeline import VisualStreamingPipeline


class VoxGlanceOrchestrator:
    """Central engine orchestrating multimodal streaming translation."""

    def __init__(
        self,
        config: AppConfig,
        overlay: Optional[TransparentOverlayWindow] = None,
        audio_source: str = "auto",
        enable_ocr: bool = True,
        asr_engine=None,
    ):
        self.config = config
        self.overlay = overlay
        self.audio_source = audio_source
        self.enable_ocr = enable_ocr

        # Core modules
        self.memory_controller = MemoryController(
            target_vram_mb=config.system.target_vram_mb,
            peak_guard_buffer_mb=config.system.peak_guard_buffer_mb,
        )
        self.translator = HybridTranslator()

        from src.audio.asr import FasterWhisperEngine
        self.asr_engine = asr_engine or FasterWhisperEngine(
            model_size=config.audio.asr.model_size,
            device="cuda" if config.system.enable_cuda else "cpu",
            compute_type=config.audio.asr.compute_type,
            max_vram_mb=config.audio.asr.max_vram_mb,
            memory_controller=self.memory_controller,
        )

        # Pipelines
        self.audio_pipeline = AudioStreamingPipeline(
            source=self.audio_source,
            sample_rate=config.audio.sample_rate,
            chunk_ms=config.audio.chunk_duration_ms,
            asr=self.asr_engine,
            translator=self.translator,
            on_subtitle=self._handle_subtitle,
        )

        self.visual_pipeline = VisualStreamingPipeline(
            fps_limit=config.visual.fps_limit,
            diff_threshold=config.visual.frame_diff_threshold,
            translator=self.translator,
            on_boxes=self._handle_ocr_boxes,
        ) if self.enable_ocr else None

        self._is_active = False

    def _handle_subtitle(self, token) -> None:
        """Route subtitle token to the transparent overlay."""
        if self.overlay:
            self.overlay.update_subtitle(token.text, is_partial=token.is_partial)

    def _handle_ocr_boxes(self, boxes) -> None:
        """Route OCR bounding boxes to the transparent overlay."""
        if self.overlay:
            self.overlay.update_ocr_boxes(boxes)

    def start(self) -> None:
        """Start all active pipelines."""
        if self._is_active:
            return

        self._is_active = True
        logger.info(f"Starting VoxGlance Orchestrator (Audio Source: {self.audio_source}, OCR: {self.enable_ocr})...")

        # 1. Start Audio Pipeline
        if not self.audio_pipeline.start():
            logger.warning("Audio pipeline failed to start.")

        # 2. Start Visual OCR Pipeline
        if self.visual_pipeline and self.enable_ocr:
            self.visual_pipeline.start()

        logger.info("VoxGlance Orchestrator fully running.")

    def stop(self) -> None:
        """Clean shutdown of all pipelines and controllers."""
        self._is_active = False
        logger.info("Stopping VoxGlance Orchestrator...")

        if self.audio_pipeline:
            self.audio_pipeline.stop()

        if self.visual_pipeline:
            self.visual_pipeline.stop()

        if self.memory_controller:
            self.memory_controller.shutdown()

        logger.info("VoxGlance Orchestrator stopped cleanly.")


# Backward compatibility alias
OmniTranslateOrchestrator = VoxGlanceOrchestrator
