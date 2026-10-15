"""Visual In-Place Translation Pipeline with Stitching, Multilingual MT, and Aesthetic Blending."""

import threading
import time
from typing import Callable, List, Optional
from loguru import logger

from src.core.ipc import VisualBoundingBox
from src.core.translator import HybridTranslator
from src.visual.aesthetic import apply_aesthetic_styling
from src.visual.capture import BaseScreenCapture, create_screen_capture
from src.visual.diff import FrameDifferencer
from src.visual.ocr import BaseOCREngine, FastOCREngine
from src.visual.stitcher import SmartTextStitcher


class VisualStreamingPipeline:
    """Captures screen, detects text, stitches sentences, translates, applies aesthetic styling, and emits to UI."""

    def __init__(
        self,
        fps_limit: int = 5,
        diff_threshold: float = 0.05,
        capture: Optional[BaseScreenCapture] = None,
        differencer: Optional[FrameDifferencer] = None,
        ocr_engine: Optional[BaseOCREngine] = None,
        translator: Optional[HybridTranslator] = None,
        stitcher: Optional[SmartTextStitcher] = None,
        on_boxes: Optional[Callable[[List[VisualBoundingBox]], None]] = None,
        enable_stitching: bool = True,
    ):
        self.fps_limit = max(1, fps_limit)
        self.interval = 1.0 / self.fps_limit
        self.capture = capture or create_screen_capture()
        self.differencer = differencer or FrameDifferencer(threshold=diff_threshold)
        self.ocr_engine = ocr_engine or FastOCREngine()
        self.translator = translator or HybridTranslator()
        self.stitcher = stitcher or SmartTextStitcher()
        self.on_boxes = on_boxes
        self.enable_stitching = enable_stitching

        self._is_running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Start the background visual in-place capture loop."""
        if self._is_running:
            return True

        self._is_running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info(f"VisualStreamingPipeline started ({self.fps_limit} FPS, threshold: {self.differencer.threshold*100}%)")
        return True

    def _capture_loop(self) -> None:
        while self._is_running:
            start_time = time.time()
            try:
                frame = self.capture.grab()
                diff_result = self.differencer.compare(frame)

                if diff_result.should_process:
                    # 1. OCR text detection and recognition
                    raw_boxes = self.ocr_engine.detect_and_recognize(frame)

                    if raw_boxes:
                        # 2. Smart Sentence Stitching (group lines to prevent fragmented translation)
                        if self.enable_stitching:
                            processed_boxes = self.stitcher.stitch(raw_boxes)
                        else:
                            processed_boxes = raw_boxes

                        # 3. Multilingual Translation & Aesthetic Styling
                        for box in processed_boxes:
                            if not box.translated_text or box.translated_text == box.original_text:
                                box.translated_text = self.translator.translate(
                                    box.original_text,
                                    source_lang=getattr(box, "detected_lang", "auto"),
                                    target_lang="vi",
                                )
                            # 4. Apply In-place Aesthetic Styling (Background sampling & Font Auto-scaling)
                            apply_aesthetic_styling(box, frame=frame)

                        if self.on_boxes:
                            self.on_boxes(processed_boxes)
            except Exception as e:
                logger.error(f"Error in OCR capture loop: {e}")

            elapsed = time.time() - start_time
            sleep_time = max(0.01, self.interval - elapsed)
            time.sleep(sleep_time)

    def stop(self) -> None:
        """Stop visual loop and release capture resources."""
        self._is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self.capture:
            self.capture.close()
        logger.info("VisualStreamingPipeline stopped.")
