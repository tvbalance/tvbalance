"""In-memory brake on repeated failures, per key (a client address).

The first few failures are free; every further one doubles the wait, up to a cap. Failures are
forgotten after a quiet period and on success. Restarting the engine resets everything, which is
fine for a LAN service.
"""

from __future__ import annotations

from dataclasses import dataclass

from tvbalance.ports.services import Clock


@dataclass(slots=True)
class _Entry:
    failures: int
    last_failure: float
    locked_until: float


class RateLimiter:
    def __init__(
        self,
        clock: Clock,
        *,
        free_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 900.0,
        forget_after: float = 3600.0,
        max_keys: int = 10_000,
    ) -> None:
        self._clock = clock
        self._free = free_attempts
        self._base = base_delay
        self._max = max_delay
        self._forget_after = forget_after
        self._max_keys = max_keys
        self._entries: dict[str, _Entry] = {}

    def retry_after(self, key: str) -> float:
        """Seconds to wait before the next attempt; 0 when it may go ahead."""
        entry = self._live(key)
        if entry is None:
            return 0.0
        return max(0.0, entry.locked_until - self._now())

    def failure(self, key: str) -> None:
        now = self._now()
        entry = self._live(key)
        if entry is None:
            self._make_room()
            entry = self._entries[key] = _Entry(0, now, 0.0)
        entry.failures += 1
        entry.last_failure = now
        over = entry.failures - self._free
        if over > 0:
            entry.locked_until = now + min(self._base * 2 ** (over - 1), self._max)

    def success(self, key: str) -> None:
        self._entries.pop(key, None)

    def tracked(self) -> int:
        return len(self._entries)

    def _now(self) -> float:
        return self._clock.now().timestamp()

    def _live(self, key: str) -> _Entry | None:
        entry = self._entries.get(key)
        if entry is not None and self._now() - entry.last_failure > self._forget_after:
            del self._entries[key]
            return None
        return entry

    def _make_room(self) -> None:
        if len(self._entries) < self._max_keys:
            return
        oldest = min(self._entries, key=lambda k: self._entries[k].last_failure)
        del self._entries[oldest]
