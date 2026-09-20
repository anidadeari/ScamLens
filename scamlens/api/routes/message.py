from fastapi import APIRouter, HTTPException

from scamlens.api.dependencies import message_model
from scamlens.api.schemas import MessageRequest, MessageResponse, MessageScores
from scamlens.message_inference import ArtifactLoadError, MessageInputError, predict_message

router = APIRouter()

LIMITATIONS = [
    "Experimental English SMS spam/ham baseline trained on an older dataset.",
    "Not validated as a phishing, fraud, or safety detector.",
    "A ham prediction does not confirm that a message is safe.",
]


@router.post("/analyze/message", response_model=MessageResponse)
async def analyze_message(payload: MessageRequest) -> MessageResponse:
    try:
        result = predict_message(message_model(), payload.text)
    except MessageInputError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ArtifactLoadError as error:
        raise HTTPException(status_code=503, detail="Message analysis is unavailable.") from error
    return MessageResponse(
        prediction=result.label,
        scores=MessageScores(spam=result.spam_score, threshold=result.threshold),
        interpretation=(
            "Experimental SMS spam prediction; this is not a fraud or safety determination."
            if result.label == "spam"
            else "Experimental SMS ham (non-spam) prediction; this does not confirm safety."
        ),
        limitations=LIMITATIONS,
    )
