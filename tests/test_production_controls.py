"""Production configuration, boundary, and operational contract tests."""
from __future__ import annotations

import asyncio

import httpx
import pytest

from scamlens.api.app import create_app
from scamlens.api.config import ConfigurationError, load_settings
from scamlens.api.safeguards import DEFAULT_RATE_LIMITS, RateLimit


def request(app, method: str, path: str, **kwargs) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://direct-peer") as client:
            return await client.request(method, path, **kwargs)
    return asyncio.run(send())


def test_development_cors_allows_localhost_and_rejects_arbitrary_origin() -> None:
    app = create_app(settings=load_settings({"SCAMLENS_ENV": "development"}))
    allowed = request(app, "OPTIONS", "/api/health", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    })
    denied = request(app, "OPTIONS", "/api/health", headers={
        "Origin": "https://attacker.invalid",
        "Access-Control-Request-Method": "GET",
    })
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


def test_production_requires_https_origin_and_never_allows_wildcard() -> None:
    with pytest.raises(ConfigurationError, match="required"):
        load_settings({"SCAMLENS_ENV": "production"})
    with pytest.raises(ConfigurationError, match="allowed HTTP scheme"):
        load_settings({"SCAMLENS_ENV": "production", "SCAMLENS_PUBLIC_ORIGIN": "http://example.invalid"})
    with pytest.raises(ConfigurationError, match="Wildcard"):
        load_settings({
            "SCAMLENS_ENV": "production",
            "SCAMLENS_PUBLIC_ORIGIN": "https://example.invalid",
            "SCAMLENS_CORS_ORIGINS": "*",
        })
    settings = load_settings({
        "SCAMLENS_ENV": "production",
        "SCAMLENS_PUBLIC_ORIGIN": "https://example.invalid",
    })
    assert settings.cors_origins == ("https://example.invalid",)
    assert "*" not in settings.cors_origins


def test_forwarded_headers_are_rejected_as_configuration_and_ignored_by_default() -> None:
    with pytest.raises(ConfigurationError, match="trusted-proxy networks"):
        load_settings({"SCAMLENS_TRUST_FORWARDED_HEADERS": "true"})

    limits = dict(DEFAULT_RATE_LIMITS)
    limits["inference"] = RateLimit(1, 60)
    app = create_app(rate_limits=limits)
    first = request(app, "POST", "/api/analyze/message", json={"text": "First"}, headers={"X-Forwarded-For": "1.1.1.1"})
    second = request(app, "POST", "/api/analyze/message", json={"text": "Second"}, headers={"X-Forwarded-For": "2.2.2.2"})
    assert first.status_code == 200
    assert second.status_code == 429


def test_security_headers_are_present_without_incorrect_hsts() -> None:
    settings = load_settings({
        "SCAMLENS_ENV": "production",
        "SCAMLENS_PUBLIC_ORIGIN": "https://example.invalid",
    })
    response = request(create_app(settings=settings), "GET", "/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "strict-transport-security" not in response.headers


def test_liveness_and_readiness_are_small_and_not_rate_limited() -> None:
    app = create_app()
    for _ in range(3):
        assert request(app, "GET", "/api/live").json() == {
            "status": "ok", "service": "scamlens-local-api"
        }
        assert request(app, "GET", "/api/ready").json() == {
            "status": "ready", "service": "scamlens-local-api"
        }


def test_readiness_failure_and_production_internal_error_are_sanitized(monkeypatch) -> None:
    from scamlens.api.routes import health

    def unavailable():
        raise RuntimeError("/private/model/path internal detail")

    monkeypatch.setattr(health, "message_model", unavailable)
    response = request(create_app(), "GET", "/api/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "The analysis service is not ready."}
    assert "private" not in response.text

    settings = load_settings({
        "SCAMLENS_ENV": "production",
        "SCAMLENS_PUBLIC_ORIGIN": "https://example.invalid",
    })
    app = create_app(settings=settings)

    @app.get("/test-unexpected")
    async def unexpected():
        raise RuntimeError("/private/path secret internal detail")

    error = request(app, "GET", "/test-unexpected")
    assert error.status_code == 500
    assert error.json() == {"detail": "The service could not complete the request."}
    assert "private" not in error.text
