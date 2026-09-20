"""Focused test for the sklearn SMS classification pipeline."""

from __future__ import annotations

import pandas as pd
import numpy as np
import pytest
from sklearn.exceptions import ConvergenceWarning

from scamlens.message_model import (
    build_pipeline,
    classification_metrics,
    fit_with_convergence_check,
    predictions_from_scores,
    scores_for_spam,
)


def test_pipeline_fits_and_produces_valid_classifier_scores() -> None:
    messages = pd.Series(
        [
            "Are we meeting for lunch today",
            "Please call me when you arrive",
            "Your appointment is tomorrow morning",
            "Claim your cash prize now",
            "Winner text PRIZE to claim a reward",
            "Free entry call this premium number",
        ]
    )
    labels = pd.Series(["ham", "ham", "ham", "spam", "spam", "spam"])
    model = build_pipeline(c_value=1.0, class_weight=None)

    model.fit(messages, labels)
    scores = scores_for_spam(model, messages)
    predictions = predictions_from_scores(scores, threshold=0.5)

    assert len(scores) == len(messages)
    assert ((scores >= 0.0) & (scores <= 1.0)).all()
    assert set(predictions).issubset({"ham", "spam"})


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan"), float("inf"), True])
def test_invalid_threshold_is_rejected(threshold: object) -> None:
    with pytest.raises(ValueError, match="threshold"):
        predictions_from_scores(np.array([0.2, 0.8]), threshold)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "scores",
    [
        np.array([[0.2, 0.8]]),
        np.array([float("nan")]),
        np.array([float("inf")]),
        np.array([-0.1, 0.5]),
        np.array([0.5, 1.1]),
        np.array(["not-numeric"]),
    ],
)
def test_invalid_scores_are_rejected(scores: np.ndarray) -> None:
    with pytest.raises(ValueError, match="scores"):
        predictions_from_scores(scores, 0.5)


@pytest.mark.parametrize(
    ("expected", "predicted"),
    [
        ([], []),
        (["ham"], ["ham", "spam"]),
        (["other"], ["ham"]),
        (["ham"], ["other"]),
        ([['ham']], [['ham']]),
    ],
)
def test_invalid_metric_inputs_are_rejected(expected: list, predicted: list) -> None:
    with pytest.raises(ValueError):
        classification_metrics(np.asarray(expected), np.asarray(predicted))


def test_valid_metric_inputs_are_accepted() -> None:
    metrics = classification_metrics(
        np.array(["ham", "spam"]), np.array(["ham", "spam"])
    )
    assert metrics["accuracy"] == 1.0


class WarningEstimator:
    def fit(self, features: object, labels: object) -> "WarningEstimator":
        import warnings

        warnings.warn("did not converge", ConvergenceWarning)
        return self


def test_convergence_warning_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="ConvergenceWarning"):
        fit_with_convergence_check(WarningEstimator(), ["x"], ["ham"])
