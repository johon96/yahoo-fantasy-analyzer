"""File-based JSON cache for yfantasy."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default TTLs in seconds
TTL_ROSTER = 300        # 5 minutes
TTL_FREE_AGENTS = 1800  # 30 minutes
TTL_PLAYERS = 3600      # 1 hour
TTL_LEAGUE = 86400      # 24 hours


class FileCache:
    """Simple file-based JSON cache with TTL expiry."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, ttl_seconds: int) -> Optional[Any]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            if time.time() - data["timestamp"] > ttl_seconds:
                logger.debug("Cache expired: %s", key)
                return None
            logger.debug("Cache hit: %s", key)
            return data["value"]
        except (json.JSONDecodeError, KeyError):
            return None

    def set(self, key: str, value: Any) -> None:
        path = self._path(key)
        path.write_text(json.dumps({"timestamp": time.time(), "value": value}))
        logger.debug("Cache set: %s", key)

    def invalidate(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def clear(self) -> None:
        for f in self.cache_dir.glob("*.json"):
            f.unlink()

    def _path(self, key: str) -> Path:
        safe = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{safe}.json"
