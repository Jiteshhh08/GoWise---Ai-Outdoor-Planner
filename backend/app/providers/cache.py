from dataclasses import dataclass
from time import monotonic
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class _Entry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """Small process-local cache for successful public provider responses."""

    def __init__(self, ttl_seconds: int, max_entries: int = 256) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: dict[str, _Entry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= monotonic():
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        now = monotonic()
        expired = [cache_key for cache_key, entry in self._entries.items() if entry.expires_at <= now]
        for cache_key in expired:
            self._entries.pop(cache_key, None)
        if len(self._entries) >= self.max_entries:
            oldest_key = min(self._entries, key=lambda cache_key: self._entries[cache_key].expires_at)
            self._entries.pop(oldest_key, None)
        self._entries[key] = _Entry(value=value, expires_at=now + self.ttl_seconds)


def rounded_coordinate(value: float) -> str:
    return f"{value:.3f}"
