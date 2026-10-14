"""Visual OCR Streaming Pipeline with Frame Differencing and LRU Translation Caching."""

import threading
import time
from typing import Callable, List, Optional
from loguru import logger

from src.core.ipc import VisualBoundingBox
from src.core.translator import HybridTranslator
from src.visual.capture import BaseScreenCapture, create_screen_capture
from src.visual.diff import FrameDifferencer
from src.visual.ocr import BaseOCREngine, FastOCREngine


class VisualStreamingPipeline:
    """Periodically captures screen, detects text changes, runs OCR, and emits translated boxes."""

    def __init__(
        self,
        fps_limit: int = 5,
        diff_threshold: float = 0.05,
        capture: Optional[BaseScreenCapture] = None,
        differencer: Optional[FrameDifferencer] = None,
        ocr_engine: Optional[BaseOCREngine] = None,
        translator: Optional[HybridTranslator] = None,
        on_boxes: Optional[Callable[[List[VisualBoundingBox]], None]] = None,
    ):
        self.fps_limit = max(1, fps_limit)
        self.interval = 1.0 / self.fps_limit
        self.capture = capture or create_screen_capture()
        self.differencer = differencer or FrameDifferencer(threshold=diff_threshold)
        self.ocr_engine = ocr_engine or FastOCREngine()
        self.translator = translator or HybridTranslator()
        self.on_boxes = on_boxes

        self._is_running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Start the background OCR screen capture loop."""
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
                    # Screen changed significantly: run OCR
                    boxes = self.ocr_engine.detect_and_recognize(frame)
                    if boxes and self.on_boxes:
                        # Translate any untranslated text using cached translator
                        for box in boxes:
                            if not box.translated_text or box.translated_text == box.original_text:
                                box.translated_text = self.translator.translate(box.original_text)
                        self.on_boxes(boxes)
            except Exception as e:
                logger.error(f"Error in OCR capture loop: {e}")

            elapsed = time.time() - start_time
            sleep_time = max(0.01, self.interval - elapsed)
            time.sleep(sleep_time)

    def stop(self) -> None:
        """Stop OCR loop and release capture resources."""
        self._is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self.capture:
            self.capture.close()
        logger.info("VisualStreamingPipeline stopped.")
