"""Small, process-local request safeguards for the development API."""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
import time
from typing import Callable

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class RateLimit:
    requests: int
    window_seconds: float


DEFAULT_RATE_LIMITS = {
    "inference": RateLimit(requests=60, window_seconds=60.0),
    "ocr": RateLimit(requests=10, window_seconds=60.0),
    "performance": RateLimit(requests=120, window_seconds=60.0),
}

RATE_LIMIT_PATHS = {
    "/api/analyze/message": "inference",
    "/api/analyze/email": "inference",
    "/api/analyze/url": "inference",
    "/api/ocr": "ocr",
    "/api/performance": "performance",
}


async def enforce_rate_limit(request: Request) -> None:
    bucket = RATE_LIMIT_PATHS.get(request.url.path)
    if not bucket:
        return
    identity = request.client.host if request.client else "unknown-direct-peer"
    if not await request.app.state.rate_limiter.allow(identity, bucket):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Wait briefly before trying again.",
            headers={"Retry-After": "60"},
        )


class InMemoryRateLimiter:
    """Fixed-window-history limiter scoped to one API process.

    Identity is the direct connection peer supplied by ASGI. Forwarding headers are
    intentionally ignored until production proxy trust is designed.
    """

    def __init__(
        self,
        limits: dict[str, RateLimit] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limits = limits or DEFAULT_RATE_LIMITS
        self._clock = clock
        self._requests: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, identity: str, bucket: str) -> bool:
        limit = self.limits[bucket]
        now = self._clock()
        cutoff = now - limit.window_seconds
        async with self._lock:
            history = self._requests[(identity, bucket)]
            while history and history[0] <= cutoff:
                history.popleft()
            if len(history) >= limit.requests:
                return False
            history.append(now)
            return True

    async def reset(self) -> None:
        async with self._lock:
            self._requests.clear()


class OCRCapacity:
    """Fail-fast per-process capacity gate; it never creates a waiting queue."""

    def __init__(self, limit: int = 2) -> None:
        if limit < 1:
            raise ValueError("OCR concurrency limit must be positive.")
        self.limit = limit
        self._active = 0
        self._lock = asyncio.Lock()

    async def try_acquire(self) -> bool:
        async with self._lock:
            if self._active >= self.limit:
                return False
            self._active += 1
            return True

    async def release(self) -> None:
        async with self._lock:
            self._active -= 1
