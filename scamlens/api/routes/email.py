from fastapi import APIRouter, HTTPException

from scamlens.api.dependencies import email_model
from scamlens.api.schemas import EmailRequest, EmailResponse
from scamlens.email_inference import EmailArtifactError, EmailInputError, MAX_EMAIL_CHARACTERS, predict_email
from scamlens.email_observations import observe_email_text

router = APIRouter()

GUIDANCE_WITH_INDICATORS = [
    "Do not use links, buttons, contact details, or instructions in the email.",
    "Verify the request through an independently trusted website, app, phone number, or known contact.",
    "For account messages, open the service directly and check for alerts there.",
]
GUIDANCE_WITHOUT_INDICATORS = [
    "Treat the classifier result as one limited signal, not a safety check.",
    "Independently verify unexpected or consequential requests before acting.",
    "Avoid email-provided links or contact details when in doubt.",
]
LIMITATIONS = [
    "Exploratory three-class baseline evaluated within one source corpus.",
    "Real-world generalization is not established.",
    "Does not inspect links, attachments, images, sender identity, or headers.",
]


@router.post("/analyze/email", response_model=EmailResponse)
async def analyze_email(payload: EmailRequest) -> EmailResponse:
    if len(payload.subject) + len(payload.body) > MAX_EMAIL_CHARACTERS:
        raise HTTPException(status_code=422, detail="Email input exceeds the supported character limit.")
    try:
        result = predict_email(email_model(), subject=payload.subject, body=payload.body)
    except EmailInputError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except EmailArtifactError as error:
        raise HTTPException(status_code=503, detail="Email analysis is unavailable.") from error
    indicators = observe_email_text(payload.subject, payload.body)
    disagreement = result.label == "Valid" and bool(indicators)
    return EmailResponse(
        prediction=result.label,
        classifier_outputs=result.scores,
        observed_indicators=indicators,
        disagreement=disagreement,
        disagreement_message=(
            "The classifier predicted Valid, but the text contains indicators that warrant additional verification."
            if disagreement else None
        ),
        verification_guidance=(GUIDANCE_WITH_INDICATORS if indicators else GUIDANCE_WITHOUT_INDICATORS),
        limitations=LIMITATIONS,
    )
