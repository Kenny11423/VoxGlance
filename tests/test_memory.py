"""Tests for MemoryController and LRUTermCache."""

import pytest
from src.core.cache import LRUTermCache
from src.core.memory import MemoryController, VRAMInfo


def test_lru_cache_operations():
    cache = LRUTermCache(maxsize=3)

    cache.put("hello", "xin chào")
    cache.put("world", "thế giới")
    cache.put("game", "trò chơi")

    assert cache.get("hello") == "xin chào"
    assert cache.get("world") == "thế giới"
    assert cache.get("game") == "trò chơi"
    assert cache.get("nonexistent") is None

    # Check stats
    stats = cache.stats()
    assert stats["size"] == 3
    assert stats["hits"] == 3
    assert stats["misses"] == 1

    # Eviction test (LRU)
    # hello was accessed, then world, then game.
    # accessing world and game makes hello least recently used?
    # wait: cache.get("hello") made hello most recently used!
    # then world, then game was most recently used.
    # so least recently used is "hello"? No, order after gets was:
    # put hello -> [hello]
    # put world -> [hello, world]
    # put game -> [hello, world, game]
    # get hello -> [world, game, hello]
    # get world -> [game, hello, world]
    # get game -> [hello, world, game]
    # least recently used is "hello".
    # Now put new item "start" -> "hello" evicted!
    cache.put("start", "bắt đầu")
    assert cache.get("hello") is None
    assert cache.get("start") == "bắt đầu"
    assert cache.get("world") == "thế giới"
    assert cache.get("game") == "trò chơi"


def test_lru_cache_normalization():
    cache = LRUTermCache(maxsize=10)
    cache.put("  Settings   Menu  ", "Menu Cài Đặt")
    assert cache.get("Settings Menu") == "Menu Cài Đặt"
    assert cache.contains("  Settings Menu  ") is True


def test_memory_controller():
    controller = MemoryController(device_index=0, target_vram_mb=950, peak_guard_buffer_mb=150)
    info = controller.get_vram_info()
    assert isinstance(info, VRAMInfo)
    assert info.total_mb > 0
    assert info.used_mb >= 0
    assert info.free_mb >= 0

    # Budget calculation
    # If we ask for an impossibly huge amount of VRAM (e.g. 5000 MB), it should reject
    assert controller.can_allocate(5000.0) is False

    # Cleanup trigger
    cleaned = controller.enforce_cleanup()
    assert isinstance(cleaned, VRAMInfo)

    controller.shutdown()
