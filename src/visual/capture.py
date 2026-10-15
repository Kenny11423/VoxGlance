"""Cross-platform Screen Capture module with native Wayland (grim) and Windows/X11 (mss) backends."""

from abc import ABC, abstractmethod
import io
import os
import shutil
import subprocess
from typing import Optional, Tuple
import numpy as np
from loguru import logger


class BaseScreenCapture(ABC):
    """Abstract base class for screen capture backends."""

    @abstractmethod
    def grab(self, monitor_index: int = 1, bbox: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """Capture screen region as RGB numpy array."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release screen capture resources."""
        pass


class WaylandGrimScreenCapture(BaseScreenCapture):
    """High-speed native screen capture for Wayland compositors (Hyprland, Sway) using grim."""

    def __init__(self):
        self._grim_path = shutil.which("grim")
        if not self._grim_path:
            raise RuntimeError("grim is not installed on system")
        logger.info(f"WaylandGrimScreenCapture initialized using {self._grim_path} (Native Wayland backend active).")

    def grab(self, monitor_index: int = 1, bbox: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        try:
            cmd = [self._grim_path, "-l", "0"]  # Level 0 compression for sub-50ms speed
            if bbox is not None:
                x, y, w, h = bbox
                cmd.extend(["-g", f"{x},{y} {w}x{h}"])
            cmd.append("-")

            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=2.0)
            if res.returncode == 0 and res.stdout:
                # Fast path: decode via OpenCV if available
                try:
                    import cv2
                    arr_bgr = cv2.imdecode(np.frombuffer(res.stdout, np.uint8), cv2.IMREAD_COLOR)
                    if arr_bgr is not None:
                        return arr_bgr[:, :, [2, 1, 0]]  # BGR -> RGB
                except Exception:
                    pass

                # Fallback to PIL
                from PIL import Image
                img = Image.open(io.BytesIO(res.stdout))
                return np.array(img.convert("RGB"))
        except Exception as e:
            logger.debug(f"Wayland grim capture error: {e}")

        return np.zeros((720, 1280, 3), dtype=np.uint8)

    def close(self) -> None:
        pass


class MSSScreenCapture(BaseScreenCapture):
    """Cross-platform screen capture using python-mss (Windows and Linux X11)."""

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
            return np.zeros((720, 1280, 3), dtype=np.uint8)

        if bbox is not None:
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
    """Factory function: automatically detects Wayland (grim) or X11/Windows (mss)."""
    # 1. Wayland auto-detection
    is_wayland = bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"))
    has_grim = bool(shutil.which("grim"))

    if (backend == "wayland" or (backend == "auto" and is_wayland)) and has_grim:
        try:
            return WaylandGrimScreenCapture()
        except Exception as e:
            logger.warning(f"Could not initialize WaylandGrimScreenCapture: {e}. Falling back to MSS.")

    # 2. Default X11 / Windows capture
    return MSSScreenCapture()
