"""Model and evaluation helpers for the experimental SMS spam/ham baseline."""

from __future__ import annotations

from typing import Any
import math
from numbers import Real
import warnings

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline


LABELS = ["ham", "spam"]


def fit_with_convergence_check(model: Any, features: Any, labels: Any) -> Any:
    """Fit a model and fail before artifact writes if convergence is uncertain."""
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always", ConvergenceWarning)
        fitted = model.fit(features, labels)
    if any(
        issubclass(warning.category, ConvergenceWarning)
        for warning in caught_warnings
    ):
        raise RuntimeError("Model fitting emitted ConvergenceWarning")
    return fitted


def build_pipeline(*, c_value: float, class_weight: str | None) -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=2,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=c_value,
                    class_weight=class_weight,
                    max_iter=1_000,
                    random_state=42,
                    solver="liblinear",
                ),
            ),
        ]
    )


def scores_for_spam(model: Pipeline, messages: pd.Series) -> np.ndarray:
    classifier = model.named_steps["classifier"]
    spam_index = list(classifier.classes_).index("spam")
    return model.predict_proba(messages)[:, spam_index]


def predictions_from_scores(scores: np.ndarray, threshold: float) -> np.ndarray:
    if (
        not isinstance(threshold, Real)
        or isinstance(threshold, (bool, np.bool_))
        or not math.isfinite(float(threshold))
        or not 0.0 <= float(threshold) <= 1.0
    ):
        raise ValueError("threshold must be a finite number within [0, 1]")
    score_array = np.asarray(scores)
    if score_array.ndim != 1:
        raise ValueError("scores must be one-dimensional")
    if not np.issubdtype(score_array.dtype, np.number):
        raise ValueError("scores must be numeric")
    if not np.isfinite(score_array).all():
        raise ValueError("scores must contain only finite values")
    if ((score_array < 0.0) | (score_array > 1.0)).any():
        raise ValueError("scores must be within [0, 1]")
    return np.where(score_array >= float(threshold), "spam", "ham")


def classification_metrics(
    expected: pd.Series | np.ndarray, predicted: pd.Series | np.ndarray
) -> dict[str, Any]:
    expected_array = np.asarray(expected)
    predicted_array = np.asarray(predicted)
    if expected_array.ndim != 1 or predicted_array.ndim != 1:
        raise ValueError("metric inputs must be one-dimensional")
    if len(expected_array) == 0 or len(predicted_array) == 0:
        raise ValueError("metric inputs must be non-empty")
    if len(expected_array) != len(predicted_array):
        raise ValueError("metric inputs must have equal lengths")
    for name, values in (("expected", expected_array), ("predicted", predicted_array)):
        unexpected = set(values.tolist()) - set(LABELS)
        if unexpected:
            raise ValueError(f"{name} contains invalid labels: {sorted(unexpected)}")
    report = classification_report(
        expected_array,
        predicted_array,
        labels=LABELS,
        output_dict=True,
        zero_division=0,
    )
    return {
        "per_class": {
            label: {
                metric: float(report[label][metric])
                for metric in ("precision", "recall", "f1-score")
            }
            | {"support": int(report[label]["support"])}
            for label in LABELS
        },
        "macro_f1": float(report["macro avg"]["f1-score"]),
        "accuracy": float(accuracy_score(expected_array, predicted_array)),
        "confusion_matrix": confusion_matrix(
            expected_array, predicted_array, labels=LABELS
        ).tolist(),
        "confusion_matrix_labels": LABELS,
    }
