"""Trusted local inference for the exploratory three-class email baseline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import warnings

import joblib
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.pipeline import Pipeline

from scamlens.email_data import redact_text
from scamlens.email_model import EMAIL_LABELS


EMAIL_TASK = "exploratory three-class email classification"
MAX_EMAIL_CHARACTERS = 100_000


class EmailArtifactError(RuntimeError):
    pass


class EmailInputError(ValueError):
    pass


@dataclass(frozen=True)
class EmailPrediction:
    label: str
    scores: dict[str, float]


def load_email_artifact(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise EmailArtifactError("The trusted local email artifact is missing.")
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", InconsistentVersionWarning)
            bundle = joblib.load(path)
    except Exception as error:
        raise EmailArtifactError("The email artifact could not be loaded.") from error
    if any(issubclass(item.category, InconsistentVersionWarning) for item in caught):
        raise EmailArtifactError("The email artifact uses an incompatible sklearn version.")
    required = {
        "pipeline", "labels", "label_mapping", "task", "evaluation_scope",
        "generalization_status", "feature_columns",
    }
    if not isinstance(bundle, dict) or not required.issubset(bundle):
        raise EmailArtifactError("The email artifact has an invalid structure.")
    if not isinstance(bundle["pipeline"], Pipeline):
        raise EmailArtifactError("The email artifact does not contain an sklearn Pipeline.")
    if (
        bundle["labels"] != EMAIL_LABELS
        or bundle["task"] != EMAIL_TASK
        or bundle["evaluation_scope"] != "within_corpus_only"
        or bundle["generalization_status"] != "not_established"
        or bundle["feature_columns"] != ["subject", "body"]
    ):
        raise EmailArtifactError("The email artifact metadata is incompatible.")
    classifier = bundle["pipeline"].named_steps.get("classifier")
    if classifier is None or set(classifier.classes_) != set(EMAIL_LABELS):
        raise EmailArtifactError("The email artifact has incompatible classes.")
    expected_mapping = {label: index for index, label in enumerate(EMAIL_LABELS)}
    if bundle["label_mapping"] != expected_mapping:
        raise EmailArtifactError("The email artifact label mapping is incompatible.")
    return bundle


def predict_email(
    bundle: dict[str, object], *, subject: object, body: object
) -> EmailPrediction:
    if not isinstance(subject, str) or not isinstance(body, str):
        raise EmailInputError("Subject and Body must be text.")
    if not subject.strip() and not body.strip():
        raise EmailInputError("Enter a Subject or Body before prediction.")
    if len(subject) + len(body) > MAX_EMAIL_CHARACTERS:
        raise EmailInputError("Email input exceeds the supported character limit.")
    clean_subject, _ = redact_text(subject)
    clean_body, _ = redact_text(body)
    model_text = f"Subject: {clean_subject}\n\nBody: {clean_body}"
    try:
        pipeline = bundle["pipeline"]
        probabilities = pipeline.predict_proba([model_text])[0]
        classifier = pipeline.named_steps["classifier"]
        scores = {
            str(label): float(score)
            for label, score in zip(classifier.classes_, probabilities)
        }
        label = str(pipeline.predict([model_text])[0])
    except Exception as error:
        raise EmailArtifactError("The email artifact is incompatible with inference.") from error
    if label not in EMAIL_LABELS or set(scores) != set(EMAIL_LABELS):
        raise EmailArtifactError("The email prediction has an invalid class schema.")
    return EmailPrediction(label=label, scores={key: scores[key] for key in EMAIL_LABELS})

