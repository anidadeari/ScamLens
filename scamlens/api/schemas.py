"""Stable public request and response contracts for the local API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr

from scamlens.email_inference import MAX_EMAIL_CHARACTERS
from scamlens.message_inference import MAX_MESSAGE_CHARACTERS
from scamlens.url_analysis import MAX_URL_CHARACTERS


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MessageRequest(APIModel):
    text: StrictStr = Field(max_length=MAX_MESSAGE_CHARACTERS)


class EmailRequest(APIModel):
    subject: StrictStr = Field(default="", max_length=MAX_EMAIL_CHARACTERS)
    body: StrictStr = Field(default="", max_length=MAX_EMAIL_CHARACTERS)


class URLRequest(APIModel):
    url: StrictStr = Field(max_length=MAX_URL_CHARACTERS)


class MessageScores(APIModel):
    spam: float
    threshold: float


class MessageResponse(APIModel):
    analysis_type: Literal["message"] = "message"
    prediction: Literal["ham", "spam"]
    scores: MessageScores
    interpretation: str
    limitations: list[str]


class EmailResponse(APIModel):
    analysis_type: Literal["email"] = "email"
    prediction: Literal["Valid", "Spam", "Phishing"]
    classifier_outputs: dict[Literal["Valid", "Spam", "Phishing"], float]
    observed_indicators: list[str]
    disagreement: bool
    disagreement_message: str | None
    verification_guidance: list[str]
    limitations: list[str]
    evaluation_scope: Literal["within_corpus_only"] = "within_corpus_only"
    generalization_status: Literal["not_established"] = "not_established"


class URLResponse(APIModel):
    analysis_type: Literal["url"] = "url"
    prediction: Literal["benign", "phish"]
    classifier_outputs: dict[Literal["benign", "phish"], float]
    observed_indicators: list[str]
    disagreement: bool
    disagreement_message: str | None
    verification_guidance: list[str]
    limitations: list[str]


class OCRResponse(APIModel):
    analysis_type: Literal["ocr"] = "ocr"
    extracted_text: str
    usable_text: bool
    classification_performed: Literal[False] = False
    review_required: Literal[True] = True
    limitations: list[str]


class ExperimentMetrics(APIModel):
    experiment: str
    evaluation_scope: str
    accuracy: float
    macro_f1: float
    target_recall_label: str
    target_recall: float
    limitations: list[str]


class PerformanceResponse(APIModel):
    source: Literal["stored_artifacts"] = "stored_artifacts"
    experiments_are_directly_comparable: Literal[False] = False
    message: ExperimentMetrics
    email: ExperimentMetrics
    url: ExperimentMetrics


class HealthResponse(APIModel):
    status: Literal["ok"] = "ok"
    service: Literal["scamlens-local-api"] = "scamlens-local-api"


class ReadinessResponse(APIModel):
    status: Literal["ready"] = "ready"
    service: Literal["scamlens-local-api"] = "scamlens-local-api"
