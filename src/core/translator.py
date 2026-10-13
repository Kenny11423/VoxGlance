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

        # Lightweight fallback / simulation for offline testing
        return f"[Dịch]: {clean_text}"


class CloudTranslator(BaseTranslator):
    """Cloud API Translator (DeepL, Groq, or OpenAI compatible) with low latency."""

    def __init__(self, api_key: Optional[str] = None, provider: str = "groq"):
        self.api_key = api_key or os.getenv("TRANSLATOR_API_KEY", "")
        self.provider = provider

    def translate(self, text: str, source_lang: str = "en", target_lang: str = "vi") -> str:
        clean_text = text.strip()
        if not clean_text or not self.api_key:
            return f"[Cloud Offline]: {clean_text}"

        try:
            # Placeholder for Cloud API calls with httpx
            import httpx
            # In production, dispatch to Groq / DeepL endpoint
            return f"[Dịch API]: {clean_text}"
        except Exception as e:
            logger.warning(f"Cloud translation failed: {e}")
            return f"[Fallback]: {clean_text}"


class HybridTranslator(BaseTranslator):
    """Hybrid Translator: checks LRU cache first, tries Cloud if available, falls back to Local."""

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

        # 2. Translate via Cloud or Local
        result = ""
        if self.prefer_cloud:
            result = self.cloud.translate(clean, source_lang, target_lang)
            if not result or result.startswith("[Cloud Offline]"):
                result = self.local.translate(clean, source_lang, target_lang)
        else:
            result = self.local.translate(clean, source_lang, target_lang)

        # 3. Store in LRU Cache
        self.cache.put(clean, result)
        return result
