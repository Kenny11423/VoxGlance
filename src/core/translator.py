"""Machine Translation Engine supporting Multilingual Local NMT, Terminology Glossary, and Auto Language Detection."""

from abc import ABC, abstractmethod
from collections import deque
import os
import re
from typing import Deque, List, Optional, Tuple
from loguru import logger

from src.core.cache import LRUTermCache
from src.core.context_engine import SemanticContextEngine, SemanticDomain
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


def split_sentences(text: str) -> List[str]:
    """Split multi-sentence text into individual sentences for NMT models.

    Prevents single-sentence NMT models (e.g. MarianMT) from prematurely terminating
    and omitting subsequent sentences in multi-sentence paragraphs.
    """
    clean = text.strip()
    if not clean:
        return []

    # Sentence boundary delimiter: [.!?…]+ followed by optional quote/bracket and whitespace,
    # ONLY when followed by an uppercase letter, digit, or opening quote/bracket.
    # Keeps dialogue tags attached: '"Hello!" she said.' remains 1 sentence.
    pattern = r'([.!?…]+["\'”’»\)\]]*\s+(?=[A-Z0-9"\'“‘«\[\(]))'
    parts = re.split(pattern, clean)
    sentences = []
    curr = ""
    for part in parts:
        curr += part
        if re.search(r'[.!?…]+["\'”’»\)\]]*\s+$', curr):
            # Exclude numbered list prefix like '1.', '2.', '10.'
            if re.match(r'^\s*(?:\(?\d+[\.\)]|[A-Za-z][\.\)])\s*$', curr):
                continue
            # Exclude standard honorifics / abbreviations ending in dot
            if not re.search(r'\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|e\.g|i\.e)\.\s+$', curr, re.IGNORECASE):
                if curr.strip():
                    sentences.append(curr.strip())
                curr = ""
    if curr.strip():
        sentences.append(curr.strip())
    return sentences if sentences else [clean]


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

        # Check if text contains multiple sentences - translate each to avoid MarianMT truncation
        sents = split_sentences(clean_text)
        if len(sents) > 1:
            trans_sents = self.translate_batch(sents, source_lang=source_lang, target_lang=target_lang)
            return " ".join(ts for ts in trans_sents if ts)

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
                        vi_text = re.sub(
                            r'[\b\[<{_]*T[O0]?K[E3]?N?\s*(\d+)\s*X?[\b\]>}_]*',
                            r'__TERM_\1__',
                            vi_text,
                            flags=re.IGNORECASE,
                        )
                    return vi_text
            except Exception as e:
                logger.error(f"CTranslate2 inference error: {e}")

        return clean_text

    def translate_batch(self, texts: List[str], source_lang: str = "en", target_lang: str = "vi") -> List[str]:
        """Translate a batch of sentences simultaneously in a single GPU pass with multi-sentence preservation."""
        if not texts:
            return []
        if self._model is None or self._sp_source is None or self._sp_target is None:
            return texts

        # Flatten multi-sentence texts into individual sentences
        mapping: List[Tuple[int, int]] = []  # (item_idx, sentence_count)
        flat_sentences: List[str] = []
        for idx, t in enumerate(texts):
            clean_t = t.strip()
            if not clean_t:
                mapping.append((idx, 0))
            else:
                sents = split_sentences(clean_t)
                mapping.append((idx, len(sents)))
                flat_sentences.extend(sents)

        if not flat_sentences:
            return [t.strip() for t in texts]

        has_terms_list = ["__TERM_" in s for s in flat_sentences]
        safe_sentences = [
            re.sub(r'__TERM_(\d+)__', r'TOKEN\1X', s) if has else s
            for s, has in zip(flat_sentences, has_terms_list)
        ]

        batch_tokens = []
        valid_indices = []

        for idx, s in enumerate(safe_sentences):
            if s and not (len(s) == 1 and not s.isalnum()):
                tokens = [">>vie<<"] + self._sp_source.encode(s, out_type=str) + ["</s>"]
                batch_tokens.append(tokens)
                valid_indices.append(idx)

        flat_results = list(safe_sentences)
        if batch_tokens:
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
                            vi_text = re.sub(
                                r'[\b\[<{_]*T[O0]?K[E3]?N?\s*(\d+)\s*X?[\b\]>}_]*',
                                r'__TERM_\1__',
                                vi_text,
                                flags=re.IGNORECASE,
                            )
                        flat_results[idx] = vi_text
            except Exception as e:
                logger.error(f"CTranslate2 batch inference error: {e}")

        # Recombine flattened sentences back into original text structures
        final_results = []
        curr_offset = 0
        for item_idx, count in mapping:
            if count == 0:
                final_results.append(texts[item_idx].strip())
            else:
                joined = " ".join(flat_results[curr_offset : curr_offset + count]).strip()
                final_results.append(joined if joined else texts[item_idx].strip())
                curr_offset += count

        return final_results


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


class LLMTranslator(BaseTranslator):
    """Context-aware LLM Translation engine supporting Ollama, Gemini API, and OpenAI-compatible APIs."""

    def __init__(
        self,
        provider: str = "auto",  # 'auto', 'ollama', 'gemini', 'openai'
        model_name: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        self.endpoint = endpoint
        self.model_name = model_name
        self.provider = provider
        self._init_provider()

    def _init_provider(self) -> None:
        if self.provider == "auto":
            if os.getenv("GEMINI_API_KEY"):
                self.provider = "gemini"
            elif os.getenv("OPENAI_API_KEY"):
                self.provider = "openai"
            else:
                self.provider = "ollama"

        if not self.model_name:
            if self.provider == "gemini":
                self.model_name = "gemini-1.5-flash"
            elif self.provider == "openai":
                self.model_name = "gpt-4o-mini"
            else:
                self.model_name = "qwen2.5:3b"

        if not self.endpoint and self.provider == "ollama":
            self.endpoint = "http://localhost:11434/api/generate"

    def translate(self, text: str, source_lang: str = "en", target_lang: str = "vi", context: str = "") -> str:
        clean_text = text.strip()
        if not clean_text:
            return ""

        prompt = (
            f"You are a professional literary, gaming, and technical translator.\n"
            f"Context: {context if context else 'General narrative'}\n"
            f"Translate the following text into natural, fluent Vietnamese. "
            f"Preserve tone, pronouns, and intent. Output ONLY the Vietnamese translation.\n\n"
            f"Text: {clean_text}"
        )

        try:
            import json
            import urllib.request

            if self.provider == "ollama" and self.endpoint:
                req_data = json.dumps({
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                }).encode("utf-8")
                req = urllib.request.Request(
                    self.endpoint,
                    data=req_data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        ans = data.get("response", "").strip()
                        if ans:
                            return ans

            elif self.provider == "gemini" and self.api_key:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
                payload = json.dumps({
                    "contents": [{"parts": [{"text": prompt}]}]
                }).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        ans = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        if ans:
                            return ans

        except Exception as e:
            logger.debug(f"LLM translation fallback due to: {e}")

        return clean_text


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
    - Dynamic Semantic Context Engine (WSD & Idioms).
    - Glossary constraint term protection.
    - Sliding context memory for dialogue coherence.
    - LRU Cache -> Local NMT / LLM -> Multilingual Cloud fallback.
    """

    def __init__(
        self,
        cache: Optional[LRUTermCache] = None,
        local_translator: Optional[BaseTranslator] = None,
        cloud_translator: Optional[BaseTranslator] = None,
        llm_translator: Optional[BaseTranslator] = None,
        glossary: Optional[MultilingualGlossary] = None,
        language_detector: Optional[FastLanguageDetector] = None,
        tone_processor: Optional[ToneProcessor] = None,
        context_engine: Optional[SemanticContextEngine] = None,
        prefer_cloud: bool = False,
        prefer_llm: bool = False,
        context_window_size: int = 3,
    ):
        self.cache = cache or LRUTermCache(maxsize=2000)
        self.local = local_translator or LocalCTranslate2Translator()
        self.cloud = cloud_translator or CloudTranslator()
        self.llm = llm_translator or LLMTranslator()
        self.glossary = glossary or MultilingualGlossary()
        self.language_detector = language_detector or FastLanguageDetector()
        self.tone_processor = tone_processor or ToneProcessor()
        self.context_engine = context_engine or SemanticContextEngine()
        self.prefer_cloud = prefer_cloud
        self.prefer_llm = prefer_llm
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

        # 3. Dynamic Semantic Context Check (Disambiguate polysemy & idioms without pre-existing glossary)
        context_history_str = " ".join(list(self.context_history))
        adapted_text = clean
        if actual_source_lang == "en":
            adapted_text, active_domain, disambig_notes = self.context_engine.resolve_context(
                clean, context_history=context_history_str
            )
            if disambig_notes:
                logger.debug(f"ContextEngine: {disambig_notes} (Active Domain: {active_domain})")

        # 4. Apply Glossary Term Masking
        masked_text, term_replacements = self.glossary.mask_terms(adapted_text)

        # 5. Perform Translation (LLM / Local CTranslate2 / Cloud)
        result = ""
        if self.prefer_llm and hasattr(self.llm, "translate"):
            result = self.llm.translate(masked_text, actual_source_lang, target_lang, context=context_history_str)
            if not result or result == masked_text:
                result = ""

        if not result:
            if not self.prefer_cloud and actual_source_lang == "en" and hasattr(self.local, "_model") and self.local._model is not None:
                result = self.local.translate(masked_text, actual_source_lang, target_lang)
                if not result or result == masked_text:
                    result = self.cloud.translate(masked_text, actual_source_lang, target_lang)
            else:
                result = self.cloud.translate(masked_text, actual_source_lang, target_lang)
                if not result or result.startswith("[Cloud Offline]"):
                    result = self.local.translate(masked_text, actual_source_lang, target_lang)

        # 6. Restore Glossary Protected Terms
        if result and term_replacements:
            result = self.glossary.unmask_terms(result, term_replacements)

        # 7. Tone & Persona Contextual Refinement
        if result and not result.startswith("[Cloud Offline]"):
            result = self.tone_processor.process(
                result,
                source_text=clean,
                context_history=list(self.context_history),
            )

        # 8. Update Context Memory & Cache
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

        # Dynamic Semantic Context Check for batch items
        context_history_str = " ".join(list(self.context_history))
        adapted_texts_to_fetch = []
        for t in texts_to_fetch:
            adapted_t, _, _ = self.context_engine.resolve_context(t, context_history=context_history_str)
            adapted_texts_to_fetch.append(adapted_t)

        # 2. Term Masking for batch
        masked_batch = []
        replacements_batch = []
        for t in adapted_texts_to_fetch:
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
