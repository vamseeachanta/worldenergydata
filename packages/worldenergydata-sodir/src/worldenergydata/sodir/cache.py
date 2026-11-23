"""
Caching implementation for SODIR API responses.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""

    data: Any
    timestamp: float
    ttl: float

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.timestamp > self.ttl


class SodirCache:
    """Simple in-memory cache for SODIR API responses."""

    def __init__(self, default_ttl: int = 86400):
        """
        Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds (24 hours)
        """
        self.cache = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired."""
        if key in self.cache:
            entry = self.cache[key]
            if not entry.is_expired():
                logger.debug(f"Cache hit for {key}")
                return entry.data
            else:
                logger.debug(f"Cache expired for {key}")
                del self.cache[key]
        return None

    def set(self, key: str, data: Any, ttl: Optional[int] = None):
        """Store item in cache."""
        ttl = ttl or self.default_ttl
        self.cache[key] = CacheEntry(data=data, timestamp=time.time(), ttl=ttl)
        logger.debug(f"Cached {key} with TTL {ttl}")

    def clear(self):
        """Clear all cached items."""
        self.cache.clear()
        logger.info("Cache cleared")
