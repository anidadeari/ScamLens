"""Application-level response headers used as defense in depth."""
from __future__ import annotations


SECURITY_HEADERS = (
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"),
)


class SecurityHeadersMiddleware:
    """Add API-safe headers without buffering request or response bodies."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {name.lower() for name, _value in headers}
                headers.extend(item for item in SECURITY_HEADERS if item[0] not in existing)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
