"""In-memory thread-safe LRU Cache for UI terms and repeated translations."""

from collections import OrderedDict
import threading
from typing import Optional


class LRUTermCache:
    """Thread-safe LRU cache to store OCR and speech translation pairs."""

    def __init__(self, maxsize: int = 2000):
        self.maxsize = maxsize
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _normalize_key(self, key: str) -> str:
        """Strip and normalize whitespace for consistent hashing."""
        return " ".join(key.strip().split())

    def get(self, key: str) -> Optional[str]:
        """Retrieve translated text if cached, updating LRU order."""
        norm_key = self._normalize_key(key)
        with self._lock:
            if norm_key in self._cache:
                self._hits += 1
                self._cache.move_to_end(norm_key)
                return self._cache[norm_key]
            self._misses += 1
            return None

    def put(self, key: str, value: str) -> None:
        """Insert or update translation in cache, evicting oldest if full."""
        norm_key = self._normalize_key(key)
        norm_val = value.strip()
        with self._lock:
            if norm_key in self._cache:
                self._cache.move_to_end(norm_key)
            self._cache[norm_key] = norm_val
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    def contains(self, key: str) -> bool:
        """Check presence without altering LRU order or hit counters."""
        norm_key = self._normalize_key(key)
        with self._lock:
            return norm_key in self._cache

    def clear(self) -> None:
        """Clear all entries and reset stats."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict:
        """Return cache hit/miss statistics and utilization."""
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = (self._hits / total) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": round(hit_ratio, 4),
            }
