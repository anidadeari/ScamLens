"""Trusted local inference for the experimental SMS spam/ham baseline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import warnings

import joblib
import numpy as np
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.pipeline import Pipeline

from scamlens.message_model import predictions_from_scores, scores_for_spam


TASK_NAME = "experimental English SMS spam/ham baseline"
EXPECTED_LABELS = ["ham", "spam"]
MAX_MESSAGE_CHARACTERS = 5_000


class ArtifactLoadError(RuntimeError):
    """Raised when the trusted local model artifact cannot be used safely."""


class MessageInputError(ValueError):
    """Raised when submitted message text is invalid."""


@dataclass(frozen=True)
class MessagePrediction:
    label: str
    spam_score: float
    threshold: float


def validate_message_input(message: object) -> str:
    if not isinstance(message, str):
        raise MessageInputError("Message must be text.")
    if not message.strip():
        raise MessageInputError("Enter a message before running the analysis.")
    if len(message) > MAX_MESSAGE_CHARACTERS:
        raise MessageInputError(
            f"Message is too long. The limit is {MAX_MESSAGE_CHARACTERS:,} characters; "
            f"your input contains {len(message):,}. Nothing was truncated."
        )
    return message


def load_trusted_artifact(path: Path) -> dict[str, object]:
    """Load only the project-controlled artifact at the caller-supplied local path."""
    if not path.is_file():
        raise ArtifactLoadError(
            "The local model artifact is missing. Reproduce Milestone 4 artifacts "
            "before starting the app."
        )
    try:
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always", InconsistentVersionWarning)
            bundle = joblib.load(path)
    except Exception as error:
        raise ArtifactLoadError(
            "The local model artifact could not be loaded. It may be damaged or "
            "incompatible with the installed dependencies."
        ) from error

    if any(
        issubclass(warning.category, InconsistentVersionWarning)
        for warning in caught_warnings
    ):
        raise ArtifactLoadError(
            "The local model artifact was created with an incompatible "
            "scikit-learn version."
        )
    if not isinstance(bundle, dict):
        raise ArtifactLoadError("The local model artifact has an invalid structure.")
    required = {"pipeline", "threshold", "labels", "task"}
    if not required.issubset(bundle):
        raise ArtifactLoadError("The local model artifact is missing required fields.")
    if not isinstance(bundle["pipeline"], Pipeline):
        raise ArtifactLoadError("The local model artifact does not contain a Pipeline.")
    if bundle["labels"] != EXPECTED_LABELS or bundle["task"] != TASK_NAME:
        raise ArtifactLoadError("The local model artifact has incompatible metadata.")
    try:
        predictions_from_scores(np.array([0.5]), bundle["threshold"])
        classifier = bundle["pipeline"].named_steps["classifier"]
        if list(classifier.classes_) != EXPECTED_LABELS:
            raise ValueError("unexpected classifier classes")
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise ArtifactLoadError(
            "The local model artifact has an incompatible pipeline or threshold."
        ) from error
    return bundle


def predict_message(bundle: dict[str, object], message: object) -> MessagePrediction:
    validated_message = validate_message_input(message)
    try:
        score = float(scores_for_spam(bundle["pipeline"], [validated_message])[0])
        label = str(
            predictions_from_scores(np.array([score]), bundle["threshold"])[0]
        )
        threshold = float(bundle["threshold"])
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as error:
        raise ArtifactLoadError(
            "The local model artifact is incompatible with this application."
        ) from error
    return MessagePrediction(label=label, spam_score=score, threshold=threshold)
