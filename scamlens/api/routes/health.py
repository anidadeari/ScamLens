from fastapi import APIRouter, HTTPException

from scamlens.api.dependencies import email_model, message_model, url_model
from scamlens.api.schemas import HealthResponse, ReadinessResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def readiness() -> ReadinessResponse:
    try:
        message_model()
        email_model()
        url_model()
    except Exception as error:
        raise HTTPException(status_code=503, detail="The analysis service is not ready.") from error
    return ReadinessResponse()
