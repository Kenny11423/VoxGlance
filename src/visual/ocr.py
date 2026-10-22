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


import os
import re
import sys

VIETNAMESE_ACCENTED_CHARS = set(
    "àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ"
    "ÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ"
)

LOG_KEYWORD_RE = re.compile(
    r"\b(INFO|DEBUG|WARN|WARNING|ERROR|CRITICAL|Traceback|VRAM|NVML)\b",
    re.IGNORECASE,
)

SYSTEM_CODE_PATTERNS = [
    "src.core", "src.visual", "fastocrengine", "localctranslate2",
    "voxglance", "waylandgrim", "det_limit_side_len",
    "subtitles_queue", "visual_boxes_queue", ".venv", "venv/bin"
]

UI_BUTTON_PATTERNS = [
    "dich trang nay", "dang dich", "chon vung", "an/hien", "ẩn/hiện", "chọn vùng", "dịch trang",
    "masterpost", "follow", "+ follow"
]
UI_BUTTON_ALNUM = {re.sub(r"[^a-zA-Z0-9]", "", p.lower()) for p in UI_BUTTON_PATTERNS if p}

TIMESTAMP_RE = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2})")
TELEMETRY_RE = re.compile(r"(\d+%\s*\+*\s*\d+%|\d+\s*°?C|\d+\.?\d*\s*(GB|MB|FPS))")


def _preload_nvidia_libs() -> None:
    """Preload bundled NVIDIA CUDA/cuDNN/cuBLAS shared libraries with RTLD_GLOBAL."""
    import ctypes
    import glob
    try:
        for p in sys.path:
            if "site-packages" in p:
                for lib_dir in glob.glob(os.path.join(p, "nvidia", "*", "lib")):
                    if os.path.isdir(lib_dir):
                        if lib_dir not in os.environ.get("LD_LIBRARY_PATH", ""):
                            os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"
                        for fname in sorted(os.listdir(lib_dir)):
                            if fname.endswith(".so") or ".so." in fname:
                                try:
                                    ctypes.CDLL(os.path.join(lib_dir, fname), mode=ctypes.RTLD_GLOBAL)
                                except Exception:
                                    pass
    except Exception:
        pass


def restore_word_boundaries(text: str) -> str:
    """Insert missing spaces between words often concatenated by OCR engine."""
    s = text.strip()
    # Normalize rogue backticks into single quote, tildes/special brackets into standard punctuation
    s = s.replace("`", "'").replace("’", "'").replace("‘", "'")
    s = re.sub(r"[<>{}\|~^]", " ", s)
    # Collapse excessively repeated character runs (e.g. Noooooo -> Noo) without dropping line
    s = re.sub(r"([a-zA-Z])\1{3,}", r"\1\1", s)
    s = re.sub(r"([,.:;!?])([a-zA-Z])", r"\1 \2", s)
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"(\d+)-([a-zA-Z])", r"\1 - \2", s)
    s = re.sub(r"([a-zA-Z])\(", r"\1 (", s)
    s = re.sub(r"\)([a-zA-Z])", r") \1", s)
    return s.strip()


def is_noise_or_self_rendered(text: str, score: float = 1.0) -> bool:
    """Filter out self-rendered Vietnamese overlay text, terminal logs, and system metrics."""
    s = text.strip()
    if not s:
        return True

    # 1. Skip if text already contains Vietnamese diacritics (prevents OCR reading back the overlay)
    if any(c in VIETNAMESE_ACCENTED_CHARS for c in s):
        return True

    # 2. Skip if text contains ISO timestamps or system telemetry
    if TIMESTAMP_RE.search(s) or TELEMETRY_RE.search(s):
        return True

    # Check terminal log headers: only uppercase log levels with brackets/pipes e.g. "| ERROR |", "DEBUG:"
    if re.search(r"(?:\||\b)(?:INFO|DEBUG|CRITICAL|Traceback|NVML)(?:\||\b)", s):
        return True

    s_lower = s.lower()
    s_alnum = re.sub(r"[^a-zA-Z0-9]", "", s_lower)

    # 3. Skip URLs or browser address bar items
    if ".tumblr.com" in s_lower or s_lower.startswith("http://") or s_lower.startswith("https://"):
        return True

    # 4. Skip terminal logs and system code paths
    if any(p in s_lower for p in SYSTEM_CODE_PATTERNS):
        return True

    # Skip standalone toolbar / web buttons, never multi-word prose
    if len(s_alnum) <= 20 and s_alnum in UI_BUTTON_ALNUM:
        return True

    # 5. Skip words containing digits sandwiched between letters (e.g. toic6the)
    if re.search(r"[a-zA-Z]\d[a-zA-Z]", s):
        return True

    # 6. Skip corrupted scanline markup noise (brackets, pipes, carets), allowing quotes and normal punctuation
    if re.search(r"[<>{}\|^]", s):
        return True

    # 7. Skip unnaturally merged nonsense words with repeating character/syllable glitches
    words = s.split()
    for w in words:
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if len(w_clean) > 15 and re.search(r'([a-zA-Z])\1{2,}', w_clean):
            return True
        if len(w_clean) > 15 and re.search(r'([a-zA-Z]{2,3})\1{2,}', w_clean):
            return True
        if len(w_clean) >= 30 and not w.lower().startswith('http'):
            return True

    # 8. Skip purely numeric, isolated digits, or punctuation noise (e.g. "23 88 27", "108", "0568")
    letters = sum(1 for c in s if c.isalpha() or '\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u30ff' or '\uac00' <= c <= '\ud7af')
    if letters < 1:
        return True

    # 9. Skip isolated 1-character fragments unless common valid English words
    if len(s) == 1 and s.lower() not in {"i", "a"}:
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
        confidence_threshold: float = 0.40,
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
        """Initialize ONNX Runtime RapidOCR backend with CUDA acceleration and CPU fallback."""
        _preload_nvidia_libs()
        try:
            from rapidocr_onnxruntime import RapidOCR
            # 1. Attempt CUDA GPU acceleration for sub-second recognition
            try:
                self._engine = RapidOCR(
                    det_use_cuda=True,
                    rec_use_cuda=True,
                    det_limit_side_len=960,
                    rec_batch_num=6,
                    use_cls=False,
                )
                self._engine_ready = True
                logger.info(
                    f"FastOCREngine initialized on CUDA (det_limit_side_len=960, Threshold: {self.confidence_threshold})"
                )
            except Exception as cuda_err:
                logger.warning(f"RapidOCR CUDA initialization failed ({cuda_err}), falling back to CPU.")
                self._engine = RapidOCR(det_limit_side_len=960, use_cls=False)
                self._engine_ready = True
                logger.info(
                    f"FastOCREngine initialized on CPU (det_limit_side_len=960, Threshold: {self.confidence_threshold})"
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
                if not text or is_noise_or_self_rendered(text, score=score):
                    continue

                cleaned_text = restore_word_boundaries(text)

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
                    original_text=cleaned_text,
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
