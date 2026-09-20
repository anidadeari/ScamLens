"""Focused tests for the exploratory three-class email model."""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from scamlens.email_inference import (
    EMAIL_TASK,
    EmailArtifactError,
    EmailInputError,
    load_email_artifact,
    predict_email,
)
from scamlens.email_model import (
    EMAIL_LABELS,
    build_email_pipeline,
    email_classification_metrics,
)
from scamlens.email_validation import (
    validate_email_dataset_manifest,
    validate_feature_columns,
)


def fitted_bundle() -> dict[str, object]:
    texts = pd.Series(
        [
            "Subject: Team meeting\n\nBody: Please review the agenda",
            "Subject: Project update\n\nBody: The report is attached",
            "Subject: Sale\n\nBody: Buy discounted products today",
            "Subject: Promotion\n\nBody: Special marketing offer",
            "Subject: Account alert\n\nBody: Verify credentials immediately",
            "Subject: Security warning\n\nBody: Confirm your password now",
        ]
    )
    labels = pd.Series(["Valid", "Valid", "Spam", "Spam", "Phishing", "Phishing"])
    pipeline = build_email_pipeline(c_value=1.0, class_weight="balanced")
    pipeline.fit(texts, labels)
    return {
        "pipeline": pipeline,
        "labels": EMAIL_LABELS,
        "label_mapping": {label: index for index, label in enumerate(EMAIL_LABELS)},
        "task": EMAIL_TASK,
        "evaluation_scope": "within_corpus_only",
        "generalization_status": "not_established",
        "feature_columns": ["subject", "body"],
    }


def test_artifact_loading_label_mapping_and_three_class_schema(tmp_path: Path) -> None:
    path = tmp_path / "email.joblib"
    joblib.dump(fitted_bundle(), path)
    bundle = load_email_artifact(path)
    result = predict_email(bundle, subject="Account notice", body="Review this message")
    assert result.label in EMAIL_LABELS
    assert list(result.scores) == EMAIL_LABELS
    assert sum(result.scores.values()) == pytest.approx(1.0)


def test_prediction_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "email.joblib"
    joblib.dump(fitted_bundle(), path)
    bundle = load_email_artifact(path)
    first = predict_email(bundle, subject="Status", body="The meeting is tomorrow")
    second = predict_email(bundle, subject="Status", body="The meeting is tomorrow")
    assert first == second


def test_empty_input_is_rejected() -> None:
    with pytest.raises(EmailInputError, match="Subject or Body"):
        predict_email(fitted_bundle(), subject="  ", body="\n")


def test_malformed_artifact_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.joblib"
    joblib.dump({"pipeline": "not a pipeline"}, path)
    with pytest.raises(EmailArtifactError):
        load_email_artifact(path)


def synthetic_data_and_manifest() -> tuple[pd.DataFrame, pd.DataFrame]:
    labels = ["Valid", "Spam", "Phishing"] * 3
    splits = ["train"] * 3 + ["validation"] * 3 + ["test"] * 3
    dataset = pd.DataFrame(
        {
            "row_id": range(1, 10), "label": labels,
            "subject": [f"subject {i}" for i in range(9)],
            "body": [f"body {i}" for i in range(9)],
            "duplicate_group": [f"group-{i}" for i in range(9)],
        }
    )
    dataset["model_text"] = "Subject: " + dataset["subject"] + "\n\nBody: " + dataset["body"]
    dataset = dataset[["row_id", "label", "subject", "body", "model_text", "duplicate_group"]]
    manifest = pd.DataFrame(
        {
            "row_id": range(1, 10), "uid": [f"uid-{i}" for i in range(9)],
            "label": labels, "duplicate_group": [f"group-{i}" for i in range(9)],
            "source_hash": [f"hash-{i}" for i in range(9)],
            "source_container": ["mbox"] * 9, "published_split": ["train"] * 9,
            "fold": range(9), "split": splits,
        }
    )
    return dataset, manifest


def test_split_manifest_integrity_and_no_duplicate_overlap() -> None:
    dataset, manifest = synthetic_data_and_manifest()
    merged = validate_email_dataset_manifest(dataset, manifest)
    assert len(merged) == 9
    manifest.loc[3, "duplicate_group"] = manifest.loc[0, "duplicate_group"]
    with pytest.raises(ValueError, match="cross split"):
        validate_email_dataset_manifest(dataset, manifest)


def test_only_subject_and_body_are_allowed_features() -> None:
    validate_feature_columns(["subject", "body"])
    with pytest.raises(ValueError, match="exactly Subject and Body"):
        validate_feature_columns(["subject", "source"])


def test_multiclass_metrics_schema() -> None:
    metrics = email_classification_metrics(EMAIL_LABELS, EMAIL_LABELS)
    assert metrics["macro_f1"] == 1.0
    assert list(metrics["per_class"]) == EMAIL_LABELS
    assert len(metrics["confusion_matrix"]) == 3


def test_pipeline_contains_only_text_vectorizer_and_classifier() -> None:
    pipeline = build_email_pipeline(c_value=1.0, class_weight=None)
    assert isinstance(pipeline, Pipeline)
    assert list(pipeline.named_steps) == ["tfidf", "classifier"]

