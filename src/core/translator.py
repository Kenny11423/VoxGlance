"""Machine Translation Engine supporting Multilingual Local NMT, Terminology Glossary, and Auto Language Detection."""

from abc import ABC, abstractmethod
from collections import deque
import os
import re
from typing import Deque, List, Optional
from loguru import logger

from src.core.cache import LRUTermCache
from src.core.glossary import MultilingualGlossary
from src.core.language_detector import FastLanguageDetector, NLLB_LANGUAGE_MAP
from src.core.tone_processor import ToneProcessor


class BaseTranslator(ABC):
    """Abstract interface for translation engines."""

    @abstractmethod
    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "vi") -> str:
        pass

    def translate_batch(self, texts: List[str], source_lang: str = "auto", target_lang: str = "vi") -> List[str]:
        return [self.translate(t, source_lang, target_lang) for t in texts]


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
    """Local ultra-fast translation using CTranslate2 (Supports Opus-MT & NLLB-200)."""

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

        # Bridge __TERM_(\d+)__ to TOKEN\1X to prevent MarianMT SentencePiece infinite underscore loop
        has_terms = "__TERM_" in clean_text
        input_text = re.sub(r'__TERM_(\d+)__', r'TOKEN\1X', clean_text) if has_terms else clean_text

        if self._model is not None and self._sp_source is not None and self._sp_target is not None:
            try:
                tokens = [">>vie<<"] + self._sp_source.encode(input_text, out_type=str) + ["</s>"]
                results = self._model.translate_batch(
                    [tokens],
                    beam_size=3,
                    repetition_penalty=1.2,
                    max_decoding_length=350,
                )
                out_tokens = [tok for tok in results[0].hypotheses[0] if tok not in ["</s>", ">>vie<<"]]
                vi_text = self._sp_target.decode(out_tokens).strip()
                if vi_text:
                    if has_terms:
                        vi_text = re.sub(r'[\b\[<{_]*T(?:O|0)?KEN\s*(\d+)\s*X?[\b\]>}_]*', r'__TERM_\1__', vi_text, flags=re.IGNORECASE)
                    return vi_text
            except Exception as e:
                logger.error(f"CTranslate2 inference error: {e}")

        return clean_text

    def translate_batch(self, texts: List[str], source_lang: str = "en", target_lang: str = "vi") -> List[str]:
        """Translate a batch of sentences simultaneously in a single GPU pass (<50ms for 30+ sentences)."""
        if not texts:
            return []
        if self._model is None or self._sp_source is None or self._sp_target is None:
            return texts

        clean_texts = [t.strip() for t in texts]
        has_terms_list = ["__TERM_" in t for t in clean_texts]
        safe_texts = [
            re.sub(r'__TERM_(\d+)__', r'TOKEN\1X', t) if has else t
            for t, has in zip(clean_texts, has_terms_list)
        ]

        batch_tokens = []
        valid_indices = []

        for idx, t in enumerate(safe_texts):
            if t and not (len(t) == 1 and not t.isalnum()):
                tokens = [">>vie<<"] + self._sp_source.encode(t, out_type=str) + ["</s>"]
                batch_tokens.append(tokens)
                valid_indices.append(idx)

        if not batch_tokens:
            return clean_texts

        results_out = list(clean_texts)
        try:
            batch_results = self._model.translate_batch(
                batch_tokens,
                beam_size=3,
                repetition_penalty=1.2,
                max_decoding_length=350,
            )
            for idx, res in zip(valid_indices, batch_results):
                out_tokens = [tok for tok in res.hypotheses[0] if tok not in ["</s>", ">>vie<<"]]
                vi_text = self._sp_target.decode(out_tokens).strip()
                if vi_text:
                    if has_terms_list[idx]:
                        vi_text = re.sub(r'[\b\[<{_]*T(?:O|0)?KEN\s*(\d+)\s*X?[\b\]>}_]*', r'__TERM_\1__', vi_text, flags=re.IGNORECASE)
                    results_out[idx] = vi_text
        except Exception as e:
            logger.error(f"CTranslate2 batch inference error: {e}")

        return results_out


class CloudTranslator(BaseTranslator):
    """Multilingual real-time online translator with persistent HTTP connection pool."""

    def __init__(self, api_key: Optional[str] = None, provider: str = "mymemory"):
        self.api_key = api_key or os.getenv("TRANSLATOR_API_KEY", "")
        self.provider = provider
        self._session = None
        self._init_backend()

    def _init_backend(self) -> None:
        try:
            import requests
            self._session = requests.Session()
            self._session.headers.update({"User-Agent": "MultimodalTranslator/1.0"})
        except Exception:
            self._session = None

    def translate(self, text: str, source_lang: str = "en", target_lang: str = "vi") -> str:
        clean_text = text.strip()
        if not clean_text:
            return ""

        # 1. Fast path: Direct Keep-Alive HTTP session to MyMemory API (supports multi-language)
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

        # 2. Fallback: GoogleTranslator with dynamic source & target language
        try:
            from deep_translator import GoogleTranslator
            res = GoogleTranslator(source=source_lang, target=target_lang).translate(clean_text)
            if res:
                return res.strip()
        except Exception:
            pass

        return f"[Cloud Offline]: {clean_text}"


def normalize_source_text(text: str) -> str:
    """Clean common OCR artifacts from source text before translation."""
    s = text.strip()
    # Normalize OCR-confused asterisks into quotes when bordering words (*word -> 'word)
    s = re.sub(r'(^|[\s"\(])\*+([a-zA-Z0-9])', r"\1'\2", s)
    s = re.sub(r'([a-zA-Z0-9])\*+(?=$|[\s"\),.:;!?])', r"\1'", s)
    return s


class HybridTranslator(BaseTranslator):
    """Production Hybrid Translator:
    - Zero-latency language identification.
    - Glossary constraint term protection.
    - Sliding context memory for dialogue coherence.
    - LRU Cache -> Local NMT -> Multilingual Cloud fallback.
    """

    def __init__(
        self,
        cache: Optional[LRUTermCache] = None,
        local_translator: Optional[BaseTranslator] = None,
        cloud_translator: Optional[BaseTranslator] = None,
        glossary: Optional[MultilingualGlossary] = None,
        language_detector: Optional[FastLanguageDetector] = None,
        tone_processor: Optional[ToneProcessor] = None,
        prefer_cloud: bool = False,
        context_window_size: int = 2,
    ):
        self.cache = cache or LRUTermCache(maxsize=2000)
        self.local = local_translator or LocalCTranslate2Translator()
        self.cloud = cloud_translator or CloudTranslator()
        self.glossary = glossary or MultilingualGlossary()
        self.language_detector = language_detector or FastLanguageDetector()
        self.tone_processor = tone_processor or ToneProcessor()
        self.prefer_cloud = prefer_cloud
        self.context_window_size = context_window_size

        # Sliding dialogue context queue
        self.context_history: Deque[str] = deque(maxlen=self.context_window_size)

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "vi") -> str:
        clean = normalize_source_text(text)
        if not clean:
            return ""

        # 1. Auto-detect source language if "auto"
        actual_source_lang = source_lang
        if source_lang == "auto":
            lang_info = self.language_detector.detect(clean)
            actual_source_lang = lang_info.lang_code

        # If source and target are the same, return as-is
        if actual_source_lang == target_lang:
            return clean

        # 2. Check LRU Cache with language key and fallback to raw string (0ms latency)
        cache_key = f"{actual_source_lang}->{target_lang}:{clean}"
        cached = self.cache.get(cache_key) or self.cache.get(clean)
        if cached:
            return cached

        # 3. Apply Glossary Term Masking
        masked_text, term_replacements = self.glossary.mask_terms(clean)

        # 4. Perform Translation (Local-first or Cloud)
        result = ""
        # If local model is available and language is en->vi, run local CTranslate2
        if not self.prefer_cloud and actual_source_lang == "en" and hasattr(self.local, "_model") and self.local._model is not None:
            result = self.local.translate(masked_text, actual_source_lang, target_lang)
            if not result or result == masked_text:
                result = self.cloud.translate(masked_text, actual_source_lang, target_lang)
        else:
            result = self.cloud.translate(masked_text, actual_source_lang, target_lang)
            if not result or result.startswith("[Cloud Offline]"):
                result = self.local.translate(masked_text, actual_source_lang, target_lang)

        # 5. Restore Glossary Protected Terms
        if result and term_replacements:
            result = self.glossary.unmask_terms(result, term_replacements)

        # 6. Tone & Persona Contextual Refinement
        if result and not result.startswith("[Cloud Offline]"):
            result = self.tone_processor.process(
                result,
                source_text=clean,
                context_history=list(self.context_history),
            )

        # 7. Update Context Memory & Cache
        if result and not result.startswith("[Cloud Offline]"):
            self.cache.put(cache_key, result)
            self.cache.put(clean, result)
            self.context_history.append(result)

        return result if result else clean

    def translate_batch(
        self,
        texts: List[str],
        source_lang: str = "auto",
        target_lang: str = "vi",
    ) -> List[str]:
        """Translate a batch of sentences simultaneously with cache lookup and GPU acceleration."""
        if not texts:
            return []

        results = ["" for _ in texts]
        indices_to_fetch = []
        texts_to_fetch = []

        # 1. Check Cache first (0ms)
        for i, t in enumerate(texts):
            clean = normalize_source_text(t)
            if not clean:
                results[i] = ""
                continue
            cache_key = f"{source_lang}->{target_lang}:{clean}"
            cached = self.cache.get(cache_key) or self.cache.get(clean)
            if cached:
                results[i] = cached
            else:
                indices_to_fetch.append(i)
                texts_to_fetch.append(clean)

        if not texts_to_fetch:
            return results

        # 2. Term Masking for batch
        masked_batch = []
        replacements_batch = []
        for t in texts_to_fetch:
            m_t, reps = self.glossary.mask_terms(t)
            masked_batch.append(m_t)
            replacements_batch.append(reps)

        # 3. Fast GPU batch inference via CTranslate2
        translated_batch = []
        if (
            not self.prefer_cloud
            and hasattr(self.local, "translate_batch")
            and getattr(self.local, "_model", None) is not None
        ):
            translated_batch = self.local.translate_batch(masked_batch, source_lang="en", target_lang=target_lang)
        else:
            # Fallback to sequential
            translated_batch = [self.cloud.translate(m, source_lang, target_lang) for m in masked_batch]

        # 4. Unmask terms, refine tone & persona, update Cache and populate results
        for idx, orig_idx in enumerate(indices_to_fetch):
            vi_text = translated_batch[idx] if idx < len(translated_batch) else texts_to_fetch[idx]
            reps = replacements_batch[idx]
            if reps and vi_text:
                vi_text = self.glossary.unmask_terms(vi_text, reps)

            if vi_text:
                vi_text = self.tone_processor.process(
                    vi_text,
                    source_text=texts_to_fetch[idx],
                    context_history=list(self.context_history),
                )

            final_text = vi_text if vi_text else texts_to_fetch[idx]
            results[orig_idx] = final_text

            cache_key = f"{source_lang}->{target_lang}:{texts_to_fetch[idx]}"
            self.cache.put(cache_key, final_text)
            self.cache.put(texts_to_fetch[idx], final_text)
            self.context_history.append(final_text)

        return results
