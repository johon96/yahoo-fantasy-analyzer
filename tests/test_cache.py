"""Tests for yfantasy file-based cache."""

import json
import time
from yfantasy.cache import FileCache


def test_cache_miss(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    assert cache.get("nonexistent", ttl_seconds=60) is None


def test_cache_set_and_get(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    cache.set("my_key", {"hello": "world"})
    result = cache.get("my_key", ttl_seconds=60)
    assert result == {"hello": "world"}


def test_cache_expired(tmp_path):
    import hashlib
    cache = FileCache(cache_dir=tmp_path)
    cache.set("old_key", {"stale": True})
    # Manually backdate the file (key is SHA-256 hashed for filesystem safety)
    safe = hashlib.sha256("old_key".encode()).hexdigest()[:16]
    cache_file = tmp_path / f"{safe}.json"
    data = json.loads(cache_file.read_text())
    data["timestamp"] = time.time() - 120
    cache_file.write_text(json.dumps(data))

    assert cache.get("old_key", ttl_seconds=60) is None


def test_cache_invalidate(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    cache.set("deleteme", {"bye": True})
    assert cache.get("deleteme", ttl_seconds=60) is not None
    cache.invalidate("deleteme")
    assert cache.get("deleteme", ttl_seconds=60) is None


def test_cache_clear(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.get("a", ttl_seconds=60) is None
    assert cache.get("b", ttl_seconds=60) is None


def test_cache_key_sanitization(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    cache.set("league/465.l.34948/roster;week=5", {"data": True})
    result = cache.get("league/465.l.34948/roster;week=5", ttl_seconds=60)
    assert result == {"data": True}
