"""FastAPI application factory for the local ScamLens API."""
import time

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from scamlens.api.routes import email, health, message, performance, screenshot, url
from scamlens.api.config import Settings, load_settings
from scamlens.api.safeguards import InMemoryRateLimiter, OCRCapacity, RateLimit, enforce_rate_limit
from scamlens.api.security import SecurityHeadersMiddleware

LOCAL_FRONTEND_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def create_app(
    *,
    settings: Settings | None = None,
    rate_limits: dict[str, RateLimit] | None = None,
    rate_limit_clock=None,
    ocr_concurrency_limit: int | None = None,
) -> FastAPI:
    runtime = settings or load_settings()
    application = FastAPI(
        title="ScamLens Local API",
        version="0.1.0",
        description="Local API over existing experimental ScamLens analysis capabilities.",
        dependencies=[Depends(enforce_rate_limit)],
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(runtime.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Accept"],
    )
    if runtime.production:
        application.add_middleware(SecurityHeadersMiddleware)
    limiter = InMemoryRateLimiter(rate_limits or runtime.rate_limits, rate_limit_clock or time.monotonic)
    application.state.rate_limiter = limiter
    application.state.ocr_capacity = OCRCapacity(ocr_concurrency_limit or runtime.ocr_concurrency_limit)
    application.state.settings = runtime

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        details = [
            {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
            for item in error.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": details})

    if runtime.production:
        @application.exception_handler(Exception)
        async def unexpected_error(_request: Request, _error: Exception) -> JSONResponse:
            return JSONResponse(
                status_code=500,
                content={"detail": "The service could not complete the request."},
            )

    application.include_router(health.router, prefix="/api", tags=["health"])
    application.include_router(message.router, prefix="/api", tags=["analysis"])
    application.include_router(email.router, prefix="/api", tags=["analysis"])
    application.include_router(url.router, prefix="/api", tags=["analysis"])
    application.include_router(screenshot.router, prefix="/api", tags=["ocr"])
    application.include_router(performance.router, prefix="/api", tags=["performance"])
    return application


app = create_app()
