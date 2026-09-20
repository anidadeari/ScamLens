"""Tests for local artifact loading and message inference."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pytest

from scamlens.message_inference import (
    ArtifactLoadError,
    MAX_MESSAGE_CHARACTERS,
    MessageInputError,
    load_trusted_artifact,
    predict_message,
    validate_message_input,
)
from scamlens.message_model import predictions_from_scores, scores_for_spam


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "artifacts" / "message" / "sms_spam_ham_pipeline.joblib"


@pytest.mark.parametrize("message", ["", " ", "\n\t"])
def test_blank_message_is_rejected(message: str) -> None:
    with pytest.raises(MessageInputError, match="Enter a message"):
        validate_message_input(message)


def test_oversized_message_is_rejected_without_truncation() -> None:
    message = "x" * (MAX_MESSAGE_CHARACTERS + 1)
    with pytest.raises(MessageInputError, match="Nothing was truncated"):
        validate_message_input(message)


def test_missing_and_malformed_artifacts_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ArtifactLoadError, match="missing"):
        load_trusted_artifact(tmp_path / "missing.joblib")

    malformed = tmp_path / "malformed.joblib"
    joblib.dump({"not": "a model"}, malformed)
    with pytest.raises(ArtifactLoadError, match="required fields"):
        load_trusted_artifact(malformed)


def test_inference_matches_shared_score_and_threshold_functions() -> None:
    bundle = load_trusted_artifact(MODEL_PATH)
    message = "You have won a prize. Reply now to claim."
    result = predict_message(bundle, message)

    direct_score = float(scores_for_spam(bundle["pipeline"], [message])[0])
    direct_label = str(
        predictions_from_scores(np.array([direct_score]), bundle["threshold"])[0]
    )
    assert result.spam_score == direct_score
    assert result.label == direct_label
