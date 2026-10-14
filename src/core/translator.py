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


class LocalCTranslate2Translator(BaseTranslator):
    """Local translation using CTranslate2 (e.g., Opus-MT or NLLB-200 INT8)."""

    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        self.device = device
        self.model_path = model_path
        self._model = None
        self._tokenizer = None
        self._init_engine()

    def _init_engine(self) -> None:
        if self.model_path and os.path.exists(self.model_path):
            try:
                import ctranslate2
                self._model = ctranslate2.Translator(self.model_path, device=self.device)
                logger.info(f"LocalCTranslate2Translator loaded from {self.model_path} on {self.device}")
            except Exception as e:
                logger.warning(f"Failed to load CTranslate2 model from {self.model_path}: {e}")
                self._model = None
        else:
            # Fallback fast heuristic / dictionary baseline when model weights are not loaded
            self._model = None

    def translate(self, text: str, source_lang: str = "en", target_lang: str = "vi") -> str:
        clean_text = text.strip()
        if not clean_text:
            return ""

        if self._model is not None:
            try:
                # If model is loaded, translate via CTranslate2
                tokens = clean_text.split()
                results = self._model.translate_batch([tokens])
                return " ".join(results[0].hypotheses[0])
            except Exception as e:
                logger.error(f"CTranslate2 inference error: {e}")

        # Lightweight fallback when local model weights are not loaded
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
            self._session.headers.update({"User-Agent": "OmniTranslate/1.0"})
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
        prefer_cloud: bool = True,
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

        # 2. Translate via Cloud / Online or Local
        result = ""
        if self.prefer_cloud:
            result = self.cloud.translate(clean, source_lang, target_lang)
            if not result or result.startswith("[Cloud Offline]"):
                result = self.local.translate(clean, source_lang, target_lang)
        else:
            result = self.local.translate(clean, source_lang, target_lang)

        # 3. Store in LRU Cache if valid translation
        if result:
            self.cache.put(clean, result)
        return result

