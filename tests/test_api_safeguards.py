"""Deterministic tests for process-local API request safeguards."""
from __future__ import annotations

import asyncio
from io import BytesIO

import httpx
from PIL import Image

from scamlens.api.app import create_app
from scamlens.api.safeguards import DEFAULT_RATE_LIMITS, InMemoryRateLimiter, OCRCapacity, RateLimit


def _png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (40, 20), "white").save(output, format="PNG")
    return output.getvalue()


def test_rate_limit_success_then_sanitized_429_and_health_exemption() -> None:
    async def scenario() -> None:
        limits = dict(DEFAULT_RATE_LIMITS)
        limits["inference"] = RateLimit(1, 60)
        app = create_app(rate_limits=limits)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post("/api/analyze/message", json={"text": "Hello"})
            blocked = await client.post("/api/analyze/message", json={"text": "Hello again"})
            health = await client.get("/api/health")
        assert first.status_code == 200
        assert blocked.status_code == 429
        assert blocked.json() == {"detail": "Too many requests. Wait briefly before trying again."}
        assert blocked.headers["retry-after"] == "60"
        assert health.status_code == 200
        assert "traceback" not in blocked.text.lower()
    asyncio.run(scenario())


def test_ocr_has_a_stricter_default_limit_than_inference() -> None:
    assert DEFAULT_RATE_LIMITS["ocr"].requests < DEFAULT_RATE_LIMITS["inference"].requests


def test_rate_limit_expiry_identity_isolation_and_reset_without_sleeping() -> None:
    async def scenario() -> None:
        now = [10.0]
        limiter = InMemoryRateLimiter({"test": RateLimit(1, 5)}, lambda: now[0])
        assert await limiter.allow("peer-a", "test")
        assert not await limiter.allow("peer-a", "test")
        assert await limiter.allow("peer-b", "test")
        now[0] = 16.0
        assert await limiter.allow("peer-a", "test")
        assert not await limiter.allow("peer-a", "test")
        await limiter.reset()
        assert await limiter.allow("peer-a", "test")
    asyncio.run(scenario())


def test_ocr_capacity_is_fail_fast_and_reusable() -> None:
    async def scenario() -> None:
        capacity = OCRCapacity(1)
        assert await capacity.try_acquire()
        assert not await capacity.try_acquire()
        await capacity.release()
        assert await capacity.try_acquire()
        await capacity.release()
    asyncio.run(scenario())


def test_ocr_route_returns_sanitized_overload_without_starting_ocr(monkeypatch) -> None:
    from scamlens.api.routes import screenshot as route

    called = False
    async def forbidden(_image, _timeout):
        nonlocal called
        called = True
        raise AssertionError("OCR must not start without capacity")

    async def scenario() -> None:
        app = create_app(ocr_concurrency_limit=1)
        assert await app.state.ocr_capacity.try_acquire()
        monkeypatch.setattr(route, "_extract_without_blocking", forbidden)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/ocr", files={"file": ("shot.png", _png_bytes(), "image/png")}
            )
        await app.state.ocr_capacity.release()
        assert response.status_code == 503
        assert response.json() == {"detail": "Local OCR is busy. Wait briefly and try again."}
        assert "traceback" not in response.text.lower()
        assert not called
    asyncio.run(scenario())
