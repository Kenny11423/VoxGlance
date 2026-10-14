"""Cross-platform Screen Capture module with fallback backends."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
import numpy as np
from loguru import logger


class BaseScreenCapture(ABC):
    """Abstract base class for screen capture backends."""

    @abstractmethod
    def grab(self, monitor_index: int = 1, bbox: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """Capture screen region as RGB/RGBA numpy array."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release screen capture resources."""
        pass


class MSSScreenCapture(BaseScreenCapture):
    """Fast cross-platform screen capture using python-mss."""

    def __init__(self):
        try:
            import mss
            self._sct = mss.MSS() if hasattr(mss, "MSS") else mss.mss()
            logger.info("MSSScreenCapture initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize mss: {e}")
            self._sct = None

    def grab(self, monitor_index: int = 1, bbox: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        if self._sct is None:
            # Return empty black frame fallback
            return np.zeros((720, 1280, 3), dtype=np.uint8)

        if bbox is not None:
            # bbox: (left, top, width, height)
            region = {
                "left": bbox[0],
                "top": bbox[1],
                "width": bbox[2],
                "height": bbox[3],
            }
        else:
            monitors = self._sct.monitors
            idx = min(monitor_index, len(monitors) - 1)
            region = monitors[idx]

        screenshot = self._sct.grab(region)
        # Convert BGRA to RGB
        img_np = np.array(screenshot, dtype=np.uint8)
        if img_np.shape[2] == 4:
            img_rgb = img_np[:, :, [2, 1, 0]]  # BGRA -> RGB
        else:
            img_rgb = img_np
        return img_rgb

    def close(self) -> None:
        if self._sct is not None:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None


def create_screen_capture(backend: str = "auto") -> BaseScreenCapture:
    """Factory function for screen capture implementations."""
    return MSSScreenCapture()
