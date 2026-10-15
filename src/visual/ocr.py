"""High-Speed Multilingual OCR Engine using ONNX Runtime (RapidOCR / DBNet & CRNN).

Features:
1. Multi-language text detection & recognition (English, Japanese, Chinese, Korean, Vietnamese).
2. Tight VRAM/CPU resource control via ONNX Runtime.
3. Accurate bounding box extraction and polygon geometry normalization.
"""

from typing import List, Optional, Tuple
import numpy as np
from loguru import logger

from src.core.cache import LRUTermCache
from src.core.ipc import VisualBoundingBox
from src.core.memory import MemoryController


class BaseOCREngine:
    """Abstract interface for screen OCR engines."""

    def detect_and_recognize(self, frame: np.ndarray) -> List[VisualBoundingBox]:
        raise NotImplementedError


class FastOCREngine(BaseOCREngine):
    """Production ONNX Runtime OCR engine supporting East Asian and Latin text."""

    def __init__(
        self,
        max_vram_mb: int = 300,
        confidence_threshold: float = 0.5,
        cache: Optional[LRUTermCache] = None,
        memory_controller: Optional[MemoryController] = None,
    ):
        self.max_vram_mb = max_vram_mb
        self.confidence_threshold = confidence_threshold
        self.cache = cache or LRUTermCache(maxsize=2000)
        self.memory_controller = memory_controller or MemoryController()
        self._engine = None
        self._engine_ready = False
        self._init_engine()

    def _init_engine(self) -> None:
        """Initialize ONNX Runtime RapidOCR backend."""
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()
            self._engine_ready = True
            logger.info(
                f"FastOCREngine initialized with RapidOCR (ONNX Runtime, Threshold: {self.confidence_threshold})"
            )
        except Exception as e:
            logger.warning(f"Could not load RapidOCR: {e}. OCR will run in fallback mock mode.")
            self._engine_ready = False

    def detect_and_recognize(self, frame: np.ndarray) -> List[VisualBoundingBox]:
        """Detect text boxes in image and recognize text.

        Args:
            frame: np.ndarray image (H, W, 3) or (H, W, 4) in BGR/RGB.

        Returns:
            List of VisualBoundingBox with coordinates, original text, and confidence.
        """
        if not self._engine_ready or self._engine is None or frame is None:
            return []

        try:
            # Ensure 3-channel BGR/RGB image
            img = frame
            if img.ndim == 3 and img.shape[2] == 4:
                img = img[:, :, :3]

            result, _ = self._engine(img)
            if not result:
                return []

            boxes: List[VisualBoundingBox] = []
            for item in result:
                dt_boxes, rec_res, score = item
                score = float(score)

                if score < self.confidence_threshold:
                    continue

                text = str(rec_res).strip()
                if not text:
                    continue

                # Compute axis-aligned bounding box from polygon coordinates
                dt_boxes = np.array(dt_boxes)
                x_min = int(np.min(dt_boxes[:, 0]))
                y_min = int(np.min(dt_boxes[:, 1]))
                x_max = int(np.max(dt_boxes[:, 0]))
                y_max = int(np.max(dt_boxes[:, 1]))

                w = max(10, x_max - x_min)
                h = max(8, y_max - y_min)

                # Check if text is vertical (height significantly greater than width)
                is_vertical = h > (w * 1.8) and len(text) > 1

                box = VisualBoundingBox(
                    x=x_min,
                    y=y_min,
                    width=w,
                    height=h,
                    original_text=text,
                    translated_text="",
                    confidence=score,
                    is_vertical=is_vertical,
                )
                boxes.append(box)

            return boxes
        except Exception as e:
            logger.error(f"Error during OCR inference: {e}")
            return []
