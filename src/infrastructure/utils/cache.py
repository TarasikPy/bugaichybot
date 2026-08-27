"""In-memory Time-To-Live (TTL) cache utility."""

import time


class TTLCache[K, V]:
    """Thread-safe and async-safe in-memory cache with item time-to-live expiration."""

    def __init__(self, ttl_seconds: float = 86400.0, maxsize: int = 1000) -> None:
        self._ttl: float = ttl_seconds
        self._maxsize: int = maxsize
        self._store: dict[K, tuple[V, float]] = {}

    def _evict_expired(self) -> None:
        now = time.monotonic()
        expired_keys = [k for k, (_val, expiry) in self._store.items() if now > expiry]
        for k in expired_keys:
            del self._store[k]

    def set(self, key: K, value: V, ttl_seconds: float | None = None) -> None:
        """Store a value with an expiration timestamp."""
        self._evict_expired()
        if len(self._store) >= self._maxsize and key not in self._store:
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]

        ttl = ttl_seconds if ttl_seconds is not None else self._ttl
        self._store[key] = (value, time.monotonic() + ttl)

    def get(self, key: K, default: V | None = None) -> V | None:
        """Retrieve value if not expired, otherwise return default."""
        if key not in self._store:
            return default

        value, expiry = self._store[key]
        if time.monotonic() > expiry:
            del self._store[key]
            return default

        return value

    def pop(self, key: K, default: V | None = None) -> V | None:
        """Remove and return key value."""
        val = self.get(key, default)
        self._store.pop(key, None)
        return val

    def __setitem__(self, key: K, value: V) -> None:
        self.set(key, value)

    def __getitem__(self, key: K) -> V:
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __contains__(self, key: K) -> bool:
        return self.get(key) is not None

    def __len__(self) -> int:
        self._evict_expired()
        return len(self._store)
