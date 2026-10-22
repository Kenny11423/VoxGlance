"""Core Orchestrator: synchronizes Audio Pipeline, Visual OCR, and Transparent Overlay."""

from typing import Optional, Tuple
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
        enable_audio: bool = True,
        asr_engine=None,
    ):
        self.config = config
        self.overlay = overlay
        self.audio_source = audio_source
        self.enable_ocr = enable_ocr
        self.enable_audio = enable_audio

        # Core modules
        self.memory_controller = MemoryController(
            target_vram_mb=config.system.target_vram_mb,
            peak_guard_buffer_mb=config.system.peak_guard_buffer_mb,
        )
        self.translator = HybridTranslator()

        # Audio pipeline (optional if visual-only mode)
        self.audio_pipeline = None
        if self.enable_audio:
            from src.audio.asr import FasterWhisperEngine
            self.asr_engine = asr_engine or FasterWhisperEngine(
                model_size=config.audio.asr.model_size,
                device="cuda" if config.system.enable_cuda else "cpu",
                compute_type=config.audio.asr.compute_type,
                max_vram_mb=config.audio.asr.max_vram_mb,
                memory_controller=self.memory_controller,
            )
            self.audio_pipeline = AudioStreamingPipeline(
                source=self.audio_source,
                sample_rate=config.audio.sample_rate,
                chunk_ms=config.audio.chunk_duration_ms,
                asr=self.asr_engine,
                translator=self.translator,
                on_subtitle=self._handle_subtitle,
            )

        # Visual pipeline
        self.visual_pipeline = VisualStreamingPipeline(
            fps_limit=config.visual.fps_limit,
            diff_threshold=config.visual.frame_diff_threshold,
            translator=self.translator,
            on_boxes=self._handle_ocr_boxes,
        ) if self.enable_ocr else None

        self._is_active = False

    def set_roi(self, roi: Optional[Tuple[int, int, int, int]]) -> None:
        """Forward ROI to visual streaming pipeline."""
        if self.visual_pipeline:
            self.visual_pipeline.set_roi(roi)

    def set_mode(self, mode: str) -> None:
        """Apply specialized translation mode across stitcher, context engine, tone processor, and overlay."""
        clean_mode = mode.lower().strip()
        from src.core.config import MODE_PRESETS
        preset = MODE_PRESETS.get(clean_mode)
        if not preset:
            logger.warning(f"Unknown mode '{mode}', defaulting to 'novel'.")
            clean_mode = "novel"
            preset = MODE_PRESETS["novel"]

        self.config.audio.translation.mode = clean_mode

        # 1. Update stitcher in visual pipeline
        if self.visual_pipeline and hasattr(self.visual_pipeline, "stitcher"):
            self.visual_pipeline.stitcher.apply_preset(clean_mode)

        # 2. Update context engine & tone processor in translator
        if self.translator:
            if hasattr(self.translator, "context_engine"):
                self.translator.context_engine.set_mode(clean_mode)
            if hasattr(self.translator, "tone_processor"):
                self.translator.tone_processor.set_persona(preset.tone_persona)

        # 3. Update overlay visual style & show toast
        if self.overlay:
            if hasattr(self.overlay, "set_overlay_style"):
                self.overlay.set_overlay_style(preset.overlay_style)
            if hasattr(self.overlay, "show_toast"):
                self.overlay.show_toast(f"Chế độ: {preset.label}")

        logger.info(f"Switched translation mode to: {preset.label} ({clean_mode})")

        # 4. Trigger instant re-translation of current screen/ROI if visual pipeline is active
        if self.visual_pipeline:
            self.visual_pipeline.trigger_now()

    def _handle_subtitle(self, token) -> None:
        """Route subtitle token to the transparent overlay."""
        if self.overlay:
            self.overlay.update_subtitle(token.text, is_partial=token.is_partial)

    def _handle_ocr_boxes(self, boxes) -> None:
        """Route OCR bounding boxes to the transparent overlay."""
        if boxes:
            preview = [f"'{b.original_text}' -> '{b.translated_text}'" for b in boxes[:3]]
            logger.debug(f"✨ [Visual Live] Đã phát hiện & dịch {len(boxes)} cụm chữ: {', '.join(preview)}")
        if self.overlay:
            self.overlay.update_ocr_boxes(boxes)

    def start(self) -> None:
        """Start all active pipelines."""
        if self._is_active:
            return

        self._is_active = True
        logger.info(
            f"Starting Orchestrator (Audio: {self.enable_audio} ({self.audio_source}), Visual OCR: {self.enable_ocr})..."
        )

        # 1. Start Audio Pipeline if enabled
        if self.audio_pipeline:
            if not self.audio_pipeline.start():
                logger.warning("Audio pipeline failed to start.")

        # 2. Start Visual OCR Pipeline if enabled
        if self.visual_pipeline and self.enable_ocr:
            self.visual_pipeline.start()

        logger.info("Orchestrator fully running.")

    def stop(self) -> None:
        """Clean shutdown of all pipelines and controllers."""
        self._is_active = False
        logger.info("Stopping Orchestrator...")

        if self.audio_pipeline:
            self.audio_pipeline.stop()

        if self.visual_pipeline:
            self.visual_pipeline.stop()

        if self.memory_controller:
            self.memory_controller.shutdown()

        logger.info("Orchestrator stopped cleanly.")


# Backward compatibility alias
OmniTranslateOrchestrator = VoxGlanceOrchestrator
