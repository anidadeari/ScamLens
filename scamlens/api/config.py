"""Validated, provider-neutral runtime configuration."""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping
from urllib.parse import urlsplit

from scamlens.api.safeguards import RateLimit


class ConfigurationError(ValueError):
    """Raised when runtime security configuration is unsafe or malformed."""


def _positive_int(source: Mapping[str, str], name: str, default: int) -> int:
    raw = source.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a positive integer.") from error
    if value < 1:
        raise ConfigurationError(f"{name} must be a positive integer.")
    return value


def _origin(value: str, *, require_https: bool) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in ({"https"} if require_https else {"http", "https"}):
        raise ConfigurationError("Configured origins must use an allowed HTTP scheme.")
    if not parsed.netloc or parsed.username or parsed.password or parsed.path not in {"", "/"}:
        raise ConfigurationError("Configured origins must be scheme-and-host origins only.")
    if parsed.query or parsed.fragment or value == "*":
        raise ConfigurationError("Configured origins must not contain paths, wildcards, queries, or fragments.")
    return value.rstrip("/")


@dataclass(frozen=True)
class Settings:
    environment: str
    cors_origins: tuple[str, ...]
    rate_limits: dict[str, RateLimit]
    ocr_concurrency_limit: int
    ocr_execution_timeout_seconds: int
    trust_forwarded_headers: bool = False

    @property
    def production(self) -> bool:
        return self.environment == "production"


def load_settings(source: Mapping[str, str] | None = None) -> Settings:
    values = os.environ if source is None else source
    environment = values.get("SCAMLENS_ENV", "development").strip().lower()
    if environment not in {"development", "test", "production"}:
        raise ConfigurationError("SCAMLENS_ENV must be development, test, or production.")

    trust_proxy = values.get("SCAMLENS_TRUST_FORWARDED_HEADERS", "false").strip().lower()
    if trust_proxy not in {"false", "0", "no"}:
        raise ConfigurationError(
            "Forwarded headers cannot be enabled without deployment-specific trusted-proxy networks."
        )

    if environment == "production":
        public_origin = values.get("SCAMLENS_PUBLIC_ORIGIN", "").strip()
        if not public_origin:
            raise ConfigurationError("SCAMLENS_PUBLIC_ORIGIN is required in production.")
        default_origins = (_origin(public_origin, require_https=True),)
    else:
        default_origins = ("http://localhost:3000", "http://127.0.0.1:3000")

    configured_origins = values.get("SCAMLENS_CORS_ORIGINS")
    if configured_origins is None:
        origins = default_origins
    else:
        candidates = tuple(item.strip() for item in configured_origins.split(",") if item.strip())
        if "*" in candidates:
            raise ConfigurationError("Wildcard CORS origins are not allowed.")
        origins = tuple(_origin(item, require_https=environment == "production") for item in candidates)

    rate_limits = {
        "inference": RateLimit(_positive_int(values, "SCAMLENS_INFERENCE_REQUESTS_PER_MINUTE", 60), 60),
        "ocr": RateLimit(_positive_int(values, "SCAMLENS_OCR_REQUESTS_PER_MINUTE", 10), 60),
        "performance": RateLimit(_positive_int(values, "SCAMLENS_PERFORMANCE_REQUESTS_PER_MINUTE", 120), 60),
    }
    return Settings(
        environment=environment,
        cors_origins=origins,
        rate_limits=rate_limits,
        ocr_concurrency_limit=_positive_int(values, "SCAMLENS_OCR_CONCURRENCY_LIMIT", 2),
        ocr_execution_timeout_seconds=_positive_int(values, "SCAMLENS_OCR_TIMEOUT_SECONDS", 15),
    )
