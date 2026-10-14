"""Machine Translation Engine supporting Local CTranslate2 and Hybrid Cloud API."""

from abc import ABC, abstractmethod
import os
from typing import Optional
from loguru import logger

from src.core.cache import LRUTermCache


class BaseTranslator(ABC):
    """Abstract interface for translation engines."""

    @abstractmethod
    def translate(self, text: str, source_lang: str = "en", target_lang: str = "vi") -> str:
        pass


def _preload_nvidia_libs() -> None:
    """Preload bundled NVIDIA CUDA/cuDNN/cuBLAS shared libraries."""
    import ctypes
    import glob
    import sys
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
                                    ctypes.CDLL(os.path.join(lib_dir, fname))
                                except Exception:
                                    pass
    except Exception:
        pass


class LocalCTranslate2Translator(BaseTranslator):
    """Local ultra-fast translation using CTranslate2 (Helsinki-NLP Opus-MT en->vi, ~15ms)."""

    def __init__(self, model_path: Optional[str] = None, device: str = "cuda"):
        self.device = device
        self.model_path = model_path
        self._model = None
        self._sp_source = None
        self._sp_target = None
        self._init_engine()

    def _init_engine(self) -> None:
        try:
            if self.device == "cuda":
                _preload_nvidia_libs()

            if not self.model_path or not os.path.exists(self.model_path):
                from huggingface_hub import snapshot_download
                self.model_path = snapshot_download("gaudi/opus-mt-en-vi-ctranslate2")

            import ctranslate2
            import sentencepiece as spm

            sp_source_path = os.path.join(self.model_path, "source.spm")
            sp_target_path = os.path.join(self.model_path, "target.spm")
            if os.path.exists(sp_source_path) and os.path.exists(sp_target_path):
                self._sp_source = spm.SentencePieceProcessor(model_file=sp_source_path)
                self._sp_target = spm.SentencePieceProcessor(model_file=sp_target_path)

            try:
                self._model = ctranslate2.Translator(self.model_path, device=self.device)
                logger.info(f"LocalCTranslate2Translator loaded on {self.device} (Sub-30ms offline translation active).")
            except Exception as cuda_err:
                if self.device == "cuda":
                    logger.warning(f"CUDA translation error ({cuda_err}). Falling back to CPU.")
                    self.device = "cpu"
                    self._model = ctranslate2.Translator(self.model_path, device="cpu")
                    logger.info("LocalCTranslate2Translator loaded on CPU.")
                else:
                    raise cuda_err
        except Exception as e:
            logger.warning(f"Could not load local CTranslate2 model: {e}")
            self._model = None

    def translate(self, text: str, source_lang: str = "en", target_lang: str = "vi") -> str:
        clean_text = text.strip()
        if not clean_text or (len(clean_text) == 1 and not clean_text.isalnum()):
            return ""

        if self._model is not None and self._sp_source is not None and self._sp_target is not None:
            try:
                tokens = [">>vie<<"] + self._sp_source.encode(clean_text, out_type=str) + ["</s>"]
                results = self._model.translate_batch(
                    [tokens],
                    beam_size=2,
                    repetition_penalty=1.2,
                    max_decoding_length=80,
                )
                out_tokens = [tok for tok in results[0].hypotheses[0] if tok not in ["</s>", ">>vie<<"]]
                vi_text = self._sp_target.decode(out_tokens).strip()
                if vi_text:
                    return vi_text
            except Exception as e:
                logger.error(f"CTranslate2 inference error: {e}")

        return clean_text



class CloudTranslator(BaseTranslator):
    """Real-time online translator with persistent HTTP connection pool for low latency."""

    def __init__(self, api_key: Optional[str] = None, provider: str = "mymemory"):
        self.api_key = api_key or os.getenv("TRANSLATOR_API_KEY", "")
        self.provider = provider
        self._mymemory = None
        self._session = None
        self._init_backend()

    def _init_backend(self) -> None:
        try:
            import requests
            self._session = requests.Session()
            # Set Keep-Alive headers
            self._session.headers.update({"User-Agent": "VoxGlance/1.0"})
        except Exception as e:
            self._session = None

        try:
            from deep_translator import MyMemoryTranslator
            self._mymemory = MyMemoryTranslator(source="en-US", target="vi-VN")
            logger.info("Online translator initialized (High-speed Keep-Alive MyMemory en -> vi).")
        except Exception as e:
            logger.warning(f"Could not initialize MyMemoryTranslator: {e}")
            self._mymemory = None

    def translate(self, text: str, source_lang: str = "en", target_lang: str = "vi") -> str:
        clean_text = text.strip()
        if not clean_text:
            return ""

        # 1. Fast path: Direct Keep-Alive HTTP session (reusing TLS connection, ~400-700ms)
        if self._session is not None:
            try:
                params = {
                    "q": clean_text,
                    "langpair": f"{source_lang}|{target_lang}",
                }
                resp = self._session.get("https://api.mymemory.translated.net/get", params=params, timeout=2.5)
                if resp.status_code == 200:
                    data = resp.json()
                    trans = data.get("responseData", {}).get("translatedText")
                    if trans and not trans.startswith("MYMEMORY WARNING"):
                        return trans.strip()
            except Exception as e:
                logger.debug(f"Fast Keep-Alive session error: {e}")

        # 2. Fallback: standard MyMemoryTranslator
        if self._mymemory is not None:
            try:
                translated = self._mymemory.translate(clean_text)
                if translated and not translated.startswith("MYMEMORY WARNING"):
                    return translated.strip()
            except Exception as e:
                logger.debug(f"MyMemory translation temporary error: {e}")

        # 3. Fallback: GoogleTranslator if available
        try:
            from deep_translator import GoogleTranslator
            res = GoogleTranslator(source=source_lang, target=target_lang).translate(clean_text)
            if res:
                return res.strip()
        except Exception:
            pass

        return f"[Cloud Offline]: {clean_text}"


class HybridTranslator(BaseTranslator):
    """Hybrid Translator: checks LRU cache first, translates via Online/Cloud, falls back to Local."""

    def __init__(
        self,
        cache: Optional[LRUTermCache] = None,
        local_translator: Optional[BaseTranslator] = None,
        cloud_translator: Optional[BaseTranslator] = None,
        prefer_cloud: bool = False,
    ):
        self.cache = cache or LRUTermCache(maxsize=2000)
        self.local = local_translator or LocalCTranslate2Translator()
        self.cloud = cloud_translator or CloudTranslator()
        self.prefer_cloud = prefer_cloud

    def translate(self, text: str, source_lang: str = "en", target_lang: str = "vi") -> str:
        clean = text.strip()
        if not clean:
            return ""

        # 1. Check LRU Cache (0ms latency)
        cached = self.cache.get(clean)
        if cached:
            return cached

        # 2. Local-first for sub-30ms zero-lag translation, fallback to cloud
        result = ""
        if not self.prefer_cloud and hasattr(self.local, "_model") and self.local._model is not None:
            result = self.local.translate(clean, source_lang, target_lang)
            if not result or result == clean:
                result = self.cloud.translate(clean, source_lang, target_lang)
        else:
            result = self.cloud.translate(clean, source_lang, target_lang)
            if not result or result.startswith("[Cloud Offline]"):
                result = self.local.translate(clean, source_lang, target_lang)

        # 3. Store in LRU Cache if valid translation
        if result:
            self.cache.put(clean, result)
        return result

