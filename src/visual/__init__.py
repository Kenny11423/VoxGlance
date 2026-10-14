"""Visual processing modules: screen capture, frame differencing, OCR, and pipeline."""

from src.visual.diff import FrameDifferencer, FrameDiffResult
from src.visual.capture import BaseScreenCapture, create_screen_capture
from src.visual.ocr import BaseOCREngine, FastOCREngine
from src.visual.pipeline import VisualStreamingPipeline

__all__ = [
    "FrameDifferencer",
    "FrameDiffResult",
    "BaseScreenCapture",
    "create_screen_capture",
    "BaseOCREngine",
    "FastOCREngine",
    "VisualStreamingPipeline",
]
