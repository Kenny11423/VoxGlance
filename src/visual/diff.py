"""Frame Differencing and motion detection to skip static screens."""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class FrameDiffResult:
    diff_ratio: float
    should_process: bool
    pixel_delta_mean: float


class FrameDifferencer:
    """Detects significant visual changes between consecutive screen frames.
    
    If the screen motion / text change is below the threshold (default 5%),
    the frame is skipped to save GPU OCR compute.
    """

    def __init__(self, threshold: float = 0.05, pixel_tolerance: int = 15):
        self.threshold = threshold
        self.pixel_tolerance = pixel_tolerance
        self.last_frame: Optional[np.ndarray] = None

    def _to_grayscale(self, frame: np.ndarray) -> np.ndarray:
        """Convert RGB/BGR or RGBA frame to 2D grayscale."""
        if frame.ndim == 2:
            return frame
        if frame.shape[2] == 4:
            # RGBA -> RGB
            frame = frame[:, :, :3]
        # Fast luminance calculation: 0.299*R + 0.587*G + 0.114*B
        gray = (
            0.299 * frame[:, :, 0]
            + 0.587 * frame[:, :, 1]
            + 0.114 * frame[:, :, 2]
        ).astype(np.uint8)
        return gray

    def compare(self, current_frame: np.ndarray) -> FrameDiffResult:
        """Compare current frame with the last processed frame.
        
        Args:
            current_frame: np.ndarray image (H, W, C) or (H, W)
            
        Returns:
            FrameDiffResult with change ratio and processing recommendation.
        """
        curr_gray = self._to_grayscale(current_frame)

        if self.last_frame is None:
            # First frame must always be processed
            self.last_frame = curr_gray
            return FrameDiffResult(diff_ratio=1.0, should_process=True, pixel_delta_mean=255.0)

        # Check if shapes match
        if curr_gray.shape != self.last_frame.shape:
            self.last_frame = curr_gray
            return FrameDiffResult(diff_ratio=1.0, should_process=True, pixel_delta_mean=255.0)

        # Compute absolute difference
        abs_diff = np.abs(curr_gray.astype(np.int16) - self.last_frame.astype(np.int16))
        
        # Pixels that changed beyond noise tolerance
        changed_mask = abs_diff > self.pixel_tolerance
        diff_ratio = float(np.mean(changed_mask))
        pixel_delta_mean = float(np.mean(abs_diff))

        should_process = diff_ratio >= self.threshold

        if should_process:
            # Update reference frame
            self.last_frame = curr_gray

        return FrameDiffResult(
            diff_ratio=round(diff_ratio, 4),
            should_process=should_process,
            pixel_delta_mean=round(pixel_delta_mean, 2),
        )

    def reset(self) -> None:
        """Reset the reference frame."""
        self.last_frame = None
