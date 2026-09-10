"""
Shared in-memory TTL (Time-To-Live) cache for CTAS external API services.

Usage:
    from .cache import ttl_cache

    data = ttl_cache.get("my_key")
    if data is None:
        data = expensive_fetch()
        ttl_cache.set("my_key", data, ttl_seconds=300)
"""

import time
import threading
from typing import Any


class TTLCache:
    """
    Thread-safe, in-process TTL cache.

    Entries expire after `ttl_seconds` from the time they were set.
    Expired entries are lazily evicted on access; a background sweep
    runs every minute to prevent unbounded memory growth.
    """

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)
        self._lock = threading.Lock()
        self._start_sweep_thread()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        """Return the cached value for *key*, or None if missing/expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Store *value* under *key* for *ttl_seconds* seconds."""
        expires_at = time.monotonic() + ttl_seconds
        with self._lock:
            self._store[key] = (value, expires_at)

    def invalidate(self, key: str) -> None:
        """Manually evict a single entry."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Flush all entries (useful in tests)."""
        with self._lock:
            self._store.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sweep(self) -> None:
        """Remove all expired entries."""
        now = time.monotonic()
        with self._lock:
            expired_keys = [k for k, (_, exp) in self._store.items() if now > exp]
            for k in expired_keys:
                del self._store[k]

    def _start_sweep_thread(self) -> None:
        """Daemonised background thread that sweeps stale entries every 60 s."""
        def _loop():
            while True:
                time.sleep(60)
                self._sweep()

        t = threading.Thread(target=_loop, daemon=True, name="TTLCache-sweep")
        t.start()


# Module-level singleton — import and use this everywhere.
ttl_cache = TTLCache()
