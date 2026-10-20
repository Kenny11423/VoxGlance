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
        fps_limit: int = 6,
        diff_threshold: float = 0.05,
        scroll_threshold: float = 0.035,
        settle_delay: float = 0.55,
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
        self.scroll_threshold = scroll_threshold
        self.settle_delay = settle_delay
        self.capture = capture or create_screen_capture()
        self.differencer = differencer or FrameDifferencer(threshold=diff_threshold)
        self.ocr_engine = ocr_engine or FastOCREngine()
        self.translator = translator or HybridTranslator()
        self.stitcher = stitcher or SmartTextStitcher()
        self.on_boxes = on_boxes
        self.enable_stitching = enable_stitching
        self.roi = roi

        # State Machine for Clear-on-Scroll and Idle-Debounced Translation
        self._is_scrolling: bool = False
        self._last_scroll_time: float = 0.0
        self._has_active_overlay: bool = False
        self._last_signatures: List[str] = []

        self._is_running = False
        self._thread: Optional[threading.Thread] = None

    def clear(self) -> None:
        """Clear active overlay and reset state signatures."""
        if self.on_boxes:
            self.on_boxes([])
        self._has_active_overlay = False
        self._last_signatures = []

    def set_roi(self, roi: Optional[Tuple[int, int, int, int]]) -> None:
        """Dynamically update Region of Interest (x, y, width, height)."""
        self.roi = roi
        self.clear()
        if self.differencer:
            self.differencer.last_frame = None
        logger.info(f"VisualStreamingPipeline ROI updated: {roi}")

    def start(self) -> bool:
        """Start the background visual in-place capture loop."""
        if self._is_running:
            return True

        self._is_running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info(
            f"VisualStreamingPipeline started ({self.fps_limit} FPS, scroll_threshold: {self.scroll_threshold*100:.1f}%, settle_delay: {self.settle_delay}s)"
        )
        return True

    def _capture_loop(self) -> None:
        while self._is_running:
            start_time = time.time()
            try:
                frame = self.capture.grab(bbox=self.roi)
                diff_result = self.differencer.compare(frame)
                now = time.time()

                # CASE 1: Screen motion detected (Scrolling / Page Switch)
                if diff_result.diff_ratio >= self.scroll_threshold:
                    # Immediately erase stale overlay so user has a 100% clean screen while moving,
                    # and no ghost characters can overlap with new text!
                    if self._has_active_overlay:
                        self.clear()

                    self._is_scrolling = True
                    self._last_scroll_time = now


                # CASE 2: Currently in scrolling motion - waiting for user to stop
                elif self._is_scrolling:
                    # Check if scroll has settled (user paused scrolling for settle_delay)
                    if (now - self._last_scroll_time) >= self.settle_delay:
                        # Screen is now completely stationary!
                        # Because overlay was cleared in CASE 1, 'frame' is 100% CLEAN
                        self._is_scrolling = False
                        self._process_and_emit_frame(frame)
                        if self.differencer:
                            self.differencer.last_frame = self.differencer._to_grayscale(frame)

                # CASE 3: Completely idle (no scroll, no motion)
                else:
                    # If no active overlay yet (initial run or after clear), process clean frame
                    if not self._has_active_overlay and diff_result.should_process:
                        self._process_and_emit_frame(frame)
                        if self.differencer:
                            self.differencer.last_frame = self.differencer._to_grayscale(frame)
                    # If active overlay is already displaying and screen is static:
                    # DO NOTHING! Strictly avoid re-OCR on top of existing overlay to prevent feedback loops.

            except Exception as e:
                logger.error(f"Error in OCR capture loop: {e}")

            elapsed = time.time() - start_time
            sleep_time = max(0.01, self.interval - elapsed)
            time.sleep(sleep_time)

    def _process_and_emit_frame(self, frame) -> bool:
        """Run OCR, Sentence Stitching, Batch Translation, Aesthetic Styling, and emit to UI."""
        if frame is None:
            return False

        try:
            # 1. OCR text detection and recognition on clean frame
            raw_boxes = self.ocr_engine.detect_and_recognize(frame)
            if not raw_boxes:
                if self._has_active_overlay:
                    if self.on_boxes:
                        self.on_boxes([])
                    self._has_active_overlay = False
                return False

            current_signatures = [b.original_text.strip() for b in raw_boxes if b.original_text.strip()]
            # Debounce: if recognized text is unchanged from last cycle, skip to prevent flickering
            if self._last_signatures and self._last_signatures == current_signatures:
                self._has_active_overlay = True
                return True
            self._last_signatures = current_signatures

            # 2. Smart Sentence Stitching (group lines to prevent fragmented translation)
            if self.enable_stitching:
                processed_boxes = self.stitcher.stitch(raw_boxes)
            else:
                processed_boxes = raw_boxes

            # 3. High-Speed Batch Translation (<50ms for all boxes via GPU)
            boxes_need_trans = [
                b for b in processed_boxes if not b.translated_text or b.translated_text == b.original_text
            ]
            if boxes_need_trans:
                texts_to_trans = [b.original_text for b in boxes_need_trans]
                if hasattr(self.translator, "translate_batch"):
                    translated_list = self.translator.translate_batch(texts_to_trans, source_lang="en", target_lang="vi")
                else:
                    translated_list = [
                        self.translator.translate(t, source_lang="en", target_lang="vi") for t in texts_to_trans
                    ]

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

            # 6. Emit to Transparent Overlay
            if self.on_boxes:
                self.on_boxes(processed_boxes)

            self._has_active_overlay = True
            return True

        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return False

    def trigger_now(self) -> None:
        """Trigger an instant one-shot snapshot translation of current ROI/screen."""
        try:
            # 1. Clear any active overlay first
            if self._has_active_overlay or self.on_boxes:
                self.clear()
                # Sleep 120ms to guarantee OS compositor clears the screen buffer
                time.sleep(0.12)

            # 2. Grab 100% clean frame
            frame = self.capture.grab(bbox=self.roi)
            self._process_and_emit_frame(frame)

            # 3. Synchronize reference frame in differencer
            if self.differencer:
                self.differencer.last_frame = self.differencer._to_grayscale(frame)

        except Exception as e:
            logger.error(f"Error in instant snapshot translation: {e}")


    def stop(self) -> None:
        """Stop visual loop and release capture resources."""
        self._is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self.capture:
            self.capture.close()
        logger.info("VisualStreamingPipeline stopped.")
