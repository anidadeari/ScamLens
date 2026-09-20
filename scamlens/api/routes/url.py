from fastapi import APIRouter, HTTPException

from scamlens.api.dependencies import url_model
from scamlens.api.schemas import URLRequest, URLResponse
from scamlens.url_analysis import URLInputError, observe_url
from scamlens.url_inference import URLArtifactError, predict_url

router = APIRouter()

GUIDANCE = [
    "Do not open a suspicious link solely to test it.",
    "Independently navigate to the organization's official site or app.",
    "Verify the sender or request through a trusted channel.",
    "Avoid entering credentials or payment information when uncertain.",
]
LIMITATIONS = [
    "ScamLens analyzes the submitted URL string only and never visits the website.",
    "No content, reputation, DNS, WHOIS, certificate, ownership, or domain-age check is performed.",
    "A prediction does not guarantee safety or maliciousness; HTTPS is not evidence of legitimacy.",
]


@router.post("/analyze/url", response_model=URLResponse)
async def analyze_url(payload: URLRequest) -> URLResponse:
    try:
        result = predict_url(url_model(), payload.url)
        indicators = observe_url(payload.url)
    except URLInputError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except URLArtifactError as error:
        raise HTTPException(status_code=503, detail="URL analysis is unavailable.") from error
    disagreement = result.label == "benign" and bool(indicators)
    return URLResponse(
        prediction=result.label,
        classifier_outputs=result.scores,
        observed_indicators=indicators,
        disagreement=disagreement,
        disagreement_message=(
            "The classifier predicted Benign, but the URL contains string-level indicators that warrant additional verification."
            if disagreement else None
        ),
        verification_guidance=GUIDANCE,
        limitations=LIMITATIONS,
    )
