"""Visual In-Place Translation Pipeline with Stitching, Multilingual MT, and Aesthetic Blending."""

import threading
import time
from typing import Callable, List, Optional, Tuple
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
        roi: Optional[Tuple[int, int, int, int]] = None,
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
        self.roi = roi

        self._is_running = False
        self._thread: Optional[threading.Thread] = None

    def set_roi(self, roi: Optional[Tuple[int, int, int, int]]) -> None:
        """Dynamically update Region of Interest (x, y, width, height)."""
        self.roi = roi
        logger.info(f"VisualStreamingPipeline ROI updated: {roi}")

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
                frame = self.capture.grab(bbox=self.roi)
                diff_result = self.differencer.compare(frame)

                if diff_result.should_process:
                    # If page scrolled significantly (diff_ratio >= 0.15), clear stale overlay immediately
                    if diff_result.diff_ratio >= 0.15 and hasattr(self, "_last_signatures"):
                        if self.on_boxes:
                            self.on_boxes([])

                    # 1. OCR text detection and recognition
                    raw_boxes = self.ocr_engine.detect_and_recognize(frame)

                    if raw_boxes:
                        current_signatures = [b.original_text.strip() for b in raw_boxes if b.original_text.strip()]
                        # Debounce: if recognized text is unchanged from last cycle, skip to prevent flickering
                        if hasattr(self, "_last_signatures") and self._last_signatures == current_signatures:
                            time.sleep(self.interval)
                            continue
                        self._last_signatures = current_signatures

                        # 2. Smart Sentence Stitching (group lines to prevent fragmented translation)
                        if self.enable_stitching:
                            processed_boxes = self.stitcher.stitch(raw_boxes)
                        else:
                            processed_boxes = raw_boxes

                        # 3. High-Speed Batch Translation (<50ms for all boxes via GPU)
                        boxes_need_trans = [b for b in processed_boxes if not b.translated_text or b.translated_text == b.original_text]
                        if boxes_need_trans:
                            texts_to_trans = [b.original_text for b in boxes_need_trans]
                            if hasattr(self.translator, "translate_batch"):
                                translated_list = self.translator.translate_batch(texts_to_trans, source_lang="en", target_lang="vi")
                            else:
                                translated_list = [self.translator.translate(t, source_lang="en", target_lang="vi") for t in texts_to_trans]

                            for box_obj, trans_t in zip(boxes_need_trans, translated_list):
                                box_obj.translated_text = trans_t

                        # 4. Aesthetic Styling on local frame
                        for box in processed_boxes:
                            apply_aesthetic_styling(box, frame=frame)

                        # 5. Offset box coordinates to absolute screen position if ROI was used
                        if self.roi:
                            offset_x, offset_y = self.roi[0], self.roi[1]
                            for b in processed_boxes:
                                b.x += offset_x
                                b.y += offset_y

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
