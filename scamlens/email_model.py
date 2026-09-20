"""Model helpers for the exploratory within-corpus email baseline."""

from __future__ import annotations

from typing import Any
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline


EMAIL_LABELS = ["Valid", "Spam", "Phishing"]
RANDOM_SEED = 42


def build_email_pipeline(*, c_value: float, class_weight: str | None) -> Pipeline:
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
                    max_iter=2_000,
                    random_state=RANDOM_SEED,
                    solver="lbfgs",
                ),
            ),
        ]
    )


def fit_email_model(model: Any, features: Any, labels: Any) -> Any:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        fitted = model.fit(features, labels)
    if any(issubclass(item.category, ConvergenceWarning) for item in caught):
        raise RuntimeError("Email model fitting emitted ConvergenceWarning")
    return fitted


def email_classification_metrics(expected: Any, predicted: Any) -> dict[str, Any]:
    expected_array = np.asarray(expected)
    predicted_array = np.asarray(predicted)
    if expected_array.ndim != 1 or predicted_array.ndim != 1:
        raise ValueError("Metric inputs must be one-dimensional")
    if not len(expected_array) or len(expected_array) != len(predicted_array):
        raise ValueError("Metric inputs must be non-empty and have equal lengths")
    for name, values in (("expected", expected_array), ("predicted", predicted_array)):
        unexpected = set(values.tolist()) - set(EMAIL_LABELS)
        if unexpected:
            raise ValueError(f"{name} contains invalid labels: {sorted(unexpected)}")
    report = classification_report(
        expected_array,
        predicted_array,
        labels=EMAIL_LABELS,
        output_dict=True,
        zero_division=0,
    )
    return {
        "accuracy": float(accuracy_score(expected_array, predicted_array)),
        "macro_precision": float(report["macro avg"]["precision"]),
        "macro_recall": float(report["macro avg"]["recall"]),
        "macro_f1": float(report["macro avg"]["f1-score"]),
        "weighted_precision": float(report["weighted avg"]["precision"]),
        "weighted_recall": float(report["weighted avg"]["recall"]),
        "weighted_f1": float(report["weighted avg"]["f1-score"]),
        "per_class": {
            label: {
                "precision": float(report[label]["precision"]),
                "recall": float(report[label]["recall"]),
                "f1": float(report[label]["f1-score"]),
                "support": int(report[label]["support"]),
            }
            for label in EMAIL_LABELS
        },
        "confusion_matrix": confusion_matrix(
            expected_array, predicted_array, labels=EMAIL_LABELS
        ).tolist(),
        "confusion_matrix_labels": EMAIL_LABELS,
    }

