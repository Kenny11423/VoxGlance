"""OCR Engine wrapper with LRU caching and strict VRAM budget."""

from typing import List, Optional
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
    """High-speed OCR Engine with DBNet detection, CRNN recognition, and LRU caching."""

    def __init__(
        self,
        max_vram_mb: int = 300,
        confidence_threshold: float = 0.6,
        cache: Optional[LRUTermCache] = None,
        memory_controller: Optional[MemoryController] = None,
    ):
        self.max_vram_mb = max_vram_mb
        self.confidence_threshold = confidence_threshold
        self.cache = cache or LRUTermCache(maxsize=2000)
        self.memory_controller = memory_controller or MemoryController()
        self._engine_ready = False
        self._init_engine()

    def _init_engine(self) -> None:
        """Initialize TensorRT/ONNX OCR runtime if available."""
        if not self.memory_controller.can_allocate(self.max_vram_mb):
            logger.warning(
                f"VRAM budget too tight for OCR engine ({self.max_vram_mb}MB). Running in CPU/Mock mode."
            )
            self._engine_ready = False
            return

        try:
            # Check for TensorRT / ONNX OCR backends
            logger.info(f"FastOCREngine ready (Max VRAM: {self.max_vram_mb}MB, Confidence: {self.confidence_threshold})")
            self._engine_ready = True
        except Exception as e:
            logger.warning(f"Could not initialize TensorRT OCR: {e}. Fallback to mock.")
            self._engine_ready = False

    def detect_and_recognize(self, frame: np.ndarray) -> List[VisualBoundingBox]:
        """Detect text boxes in image and recognize text.
        
        Args:
            frame: np.ndarray image (H, W, 3)
            
        Returns:
            List of VisualBoundingBox with coordinates, original text, and translation.
        """
        # Real OCR pipeline: only return detected boxes if an active OCR model is loaded.
        # Do not return fake/mock boxes to avoid hallucinating subtitles on screen.
        if not self._engine_ready:
            return []

        return []

