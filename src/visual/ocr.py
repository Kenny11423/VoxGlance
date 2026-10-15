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


import re

VIETNAMESE_ACCENTED_CHARS = set(
    "àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ"
    "ÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ"
)

LOG_KEYWORD_RE = re.compile(
    r"\b(INFO|DEBUG|WARN|WARNING|ERROR|CRITICAL|Traceback|VRAM|NVML)\b",
    re.IGNORECASE,
)

SYSTEM_LOG_PATTERNS = [
    "sc.core", "src.core", "src.visual", "sc.vial", "sc.line", "FastOCREngine",
    "LocalCTranslate2", "Orchestrator", "MemoryController", "Threshold:",
    "WaylandGrim", "subtitles_queue", "visual_boxes_queue",
    "det_limit_side_len", ".py:", ".py ", "~/.venv", "venv/bin",
    "RUN_VISUAL", "MAIN.PY", "%18%", "°C()",
    "tumblr.com", "http://", "https://", "www."
]

TIMESTAMP_RE = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2})")
TELEMETRY_RE = re.compile(r"(\d+%\s*\+*\s*\d+%|\d+\s*°?C|\d+\.?\d*\s*(GB|MB|FPS))")


def is_noise_or_self_rendered(text: str) -> bool:
    """Filter out self-rendered Vietnamese overlay text, terminal logs, and system metrics."""
    s = text.strip()
    if not s:
        return True

    # 1. Skip if text already contains Vietnamese diacritics (prevents OCR reading back the overlay)
    if any(c in VIETNAMESE_ACCENTED_CHARS for c in s):
        return True

    # 2. Skip if text contains ISO timestamps or system telemetry
    if TIMESTAMP_RE.search(s) or TELEMETRY_RE.search(s) or LOG_KEYWORD_RE.search(s):
        return True

    # 3. Skip if text contains terminal log / program telemetry artifacts
    s_upper = s.upper()
    for pattern in SYSTEM_LOG_PATTERNS:
        if pattern.upper() in s_upper:
            return True


    # 4. Skip repeated character runs (e.g. 'uuu', 'lll', 'aaa') or syllable loops (e.g. 'ulululu')
    if re.search(r"([a-zA-Z])\1{2,}", s) or re.search(r"([a-zA-Z]{2,3})\1{2,}", s):
        return True

    # 5. Skip words that are unnaturally long with no spaces (hallucinated merged text from overlapped lines)
    words = s.split()
    for w in words:
        if len(w) >= 20 and not (w.startswith("http") or "/" in w or "_" in w):
            return True


    # 6. Skip text with anomalous bracketed / markup garbage
    if re.search(r"[<>{}[\]|~^`]", s):
        return True


    # 7. Skip purely numeric, isolated digits, or punctuation noise (e.g. "23 88 27", "108", "0568")
    letters = sum(1 for c in s if c.isalpha() or '\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u30ff' or '\uac00' <= c <= '\ud7af')
    if letters < 2 and len(s) > 1:
        return True

    # 8. Skip isolated 1-2 character fragments unless common valid English words
    VALID_SHORT_WORDS = {"i", "a", "an", "as", "at", "be", "by", "do", "go", "he", "if", "in", "is", "it", "me", "my", "no", "of", "on", "or", "so", "to", "up", "us", "we", "ok"}
    if len(s) <= 2 and s.lower() not in VALID_SHORT_WORDS:
        return True

    return False



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
            # det_limit_side_len=1920 ensures 1080p full HD screens maintain pixel fidelity
            # use_cls=False prevents the classifier from mistakenly flipping normal horizontal lines upside-down
            self._engine = RapidOCR(det_limit_side_len=1920, use_cls=False)
            self._engine_ready = True
            logger.info(
                f"FastOCREngine initialized with RapidOCR (ONNX Runtime, det_limit_side_len=1920, use_cls=False, Threshold: {self.confidence_threshold})"
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
                if not text or is_noise_or_self_rendered(text):
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
                    original_line_height=float(h),
                    line_count=1,
                )
                boxes.append(box)

            return boxes
        except Exception as e:
            logger.error(f"Error during OCR inference: {e}")
            return []
