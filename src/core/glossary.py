"""Multilingual Terminology and Custom Glossary Protection Engine.

Features:
1. Fast substring matching for game terms, character names, skills, and technical vocabulary.
2. Placeholder replacement: Replaces terms with protected tokens before translation.
3. Post-translation restoration: Injects official translations or preserves exact original terms.
"""

from dataclasses import dataclass
import json
import os
import re
from typing import Dict, List, Optional, Tuple
from loguru import logger


@dataclass
class GlossaryEntry:
    """Entry defining term mapping."""
    source_term: str
    target_term: str
    domain: str = "general"
    case_sensitive: bool = False


class MultilingualGlossary:
    """Manages custom domain dictionaries and protects terms from literal mistranslation."""

    def __init__(self, glossary_file: Optional[str] = None):
        self.entries: Dict[str, GlossaryEntry] = {}
        self._pattern: Optional[re.Pattern] = None
        if glossary_file and os.path.exists(glossary_file):
            self.load_from_file(glossary_file)
        else:
            default_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "configs",
                "default_glossary.json"
            )
            if os.path.exists(default_path):
                self.load_from_file(default_path)

    def add_term(
        self,
        source_term: str,
        target_term: str,
        domain: str = "general",
        case_sensitive: bool = False,
    ) -> None:
        """Add or update a term in the glossary."""
        src_clean = source_term.strip()
        tgt_clean = target_term.strip()
        if not src_clean:
            return

        key = src_clean if case_sensitive else src_clean.lower()
        self.entries[key] = GlossaryEntry(
            source_term=src_clean,
            target_term=tgt_clean,
            domain=domain,
            case_sensitive=case_sensitive,
        )
        self._rebuild_pattern()

    def load_from_file(self, filepath: str) -> bool:
        """Load terms from a JSON file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, str):
                        self.add_term(k, v)
                    elif isinstance(v, dict):
                        self.add_term(
                            k,
                            v.get("target", k),
                            domain=v.get("domain", "general"),
                            case_sensitive=v.get("case_sensitive", False),
                        )
            logger.info(f"Loaded {len(self.entries)} glossary terms from {filepath}")
            return True
        except Exception as e:
            logger.warning(f"Could not load glossary from {filepath}: {e}")
            return False

    def _rebuild_pattern(self) -> None:
        """Compile regex pattern for all registered terms sorted by length descending."""
        if not self.entries:
            self._pattern = None
            return

        # Sort terms longest first to prevent prefix shadowing
        escaped_terms = [re.escape(e.source_term) for e in sorted(
            self.entries.values(), key=lambda x: len(x.source_term), reverse=True
        )]
        pattern_str = r"\b(" + "|".join(escaped_terms) + r")\b"
        self._pattern = re.compile(pattern_str, re.IGNORECASE)

    def mask_terms(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """Find terms in text and replace with unique protected tokens.

        Returns:
            Tuple of (masked_text, list of (token_id, target_translation)).
        """
        if not self._pattern or not text:
            return text, []

        matches = []
        token_counter = 0

        def replace_match(match: re.Match) -> str:
            nonlocal token_counter
            matched_str = match.group(0)
            key = matched_str if matched_str in self.entries else matched_str.lower()
            entry = self.entries.get(key)
            target_replacement = entry.target_term if entry else matched_str

            token = f"__TERM_{token_counter}__"
            matches.append((token, target_replacement))
            token_counter += 1
            return token

        masked_text = self._pattern.sub(replace_match, text)
        return masked_text, matches

    def unmask_terms(self, text: str, replacements: List[Tuple[str, str]]) -> str:
        """Replace protected tokens with target translated terms, resilient to NMT mangling."""
        if not text or not replacements:
            return text

        result = text
        for token, target_term in replacements:
            idx_m = re.search(r'\d+', token)
            idx = idx_m.group(0) if idx_m else '0'
            # Patterns covering exact token and variations produced by Marian/NLLB tokenizer:
            patterns = [
                re.compile(re.escape(token), re.IGNORECASE),
                re.compile(r'[_\[<{]*TERM[_\s]*' + idx + r'[_\]>}]*', re.IGNORECASE),
                re.compile(r'[_\[<{]*T(?:O|0)?KEN[_\s]*' + idx + r'[X\s_\]>}]*', re.IGNORECASE),
                re.compile(r'[_\[<{]*BAR[_\s]*' + idx + r'[_\]>}]*', re.IGNORECASE),
            ]
            for p in patterns:
                result = p.sub(target_term, result)

        # Clean any trailing run of underscores left behind by token distortion
        result = re.sub(r'_{2,}', ' ', result)
        # Normalize whitespace
        result = re.sub(r'[ \t]{2,}', ' ', result).strip()
        return result
