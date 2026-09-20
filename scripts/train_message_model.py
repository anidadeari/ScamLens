"""Select and train the experimental English SMS spam/ham baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import platform
import sys

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.dummy import DummyClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scamlens.message_model import (  # noqa: E402
    build_pipeline,
    classification_metrics,
    fit_with_convergence_check,
    predictions_from_scores,
    scores_for_spam,
)
from scamlens.data_validation import validate_and_merge_dataset_manifest  # noqa: E402
from scamlens.message_split import assert_no_group_overlap  # noqa: E402
from scamlens.runtime import (  # noqa: E402
    require_output_permission,
    source_version_identifier,
)


DATA_PATH = PROJECT_ROOT / "data" / "processed" / "uci_sms_spam_baseline.csv"
MANIFEST_PATH = PROJECT_ROOT / "data" / "processed" / "message_split_manifest.csv"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "message"
MODEL_PATH = ARTIFACT_DIR / "sms_spam_ham_pipeline.joblib"
METADATA_PATH = ARTIFACT_DIR / "metadata.json"
CONFIG_PATH = ARTIFACT_DIR / "config.json"
VALIDATION_PATH = ARTIFACT_DIR / "validation_metrics.json"
ERRORS_PATH = ARTIFACT_DIR / "validation_errors.csv"
SEED = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite", action="store_true", help="Explicitly replace existing artifacts."
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate_model(model: object, frame: pd.DataFrame, threshold: float) -> dict:
    scores = scores_for_spam(model, frame["message"])
    predictions = predictions_from_scores(scores, threshold)
    return classification_metrics(frame["label"], predictions)


def evaluate_dummy(model: DummyClassifier, frame: pd.DataFrame) -> dict:
    return classification_metrics(frame["label"], model.predict(frame[["message"]]))


def main() -> None:
    args = parse_args()
    require_output_permission(
        [MODEL_PATH, METADATA_PATH, CONFIG_PATH, VALIDATION_PATH, ERRORS_PATH],
        overwrite=args.overwrite,
    )
    data = pd.read_csv(DATA_PATH, keep_default_na=False)
    manifest = pd.read_csv(MANIFEST_PATH, keep_default_na=False)
    merged = validate_and_merge_dataset_manifest(data, manifest)
    assert_no_group_overlap(merged)

    train = merged[merged["split"] == "train"].copy()
    validation = merged[merged["split"] == "validation"].copy()
    if merged[merged["split"] == "test"].empty:
        raise ValueError("The test split is missing")

    dummy = DummyClassifier(strategy="most_frequent", random_state=SEED)
    dummy.fit(train[["message"]], train["label"])

    candidate_parameters = [
        {"c_value": c_value, "class_weight": class_weight}
        for class_weight in (None, "balanced")
        for c_value in (0.5, 1.0, 2.0)
    ]
    thresholds = [0.40, 0.50, 0.60]
    candidates: list[dict] = []
    fitted_models: dict[tuple[float, str | None], object] = {}

    for parameters in candidate_parameters:
        model = build_pipeline(**parameters)
        fit_with_convergence_check(model, train["message"], train["label"])
        fitted_models[(parameters["c_value"], parameters["class_weight"])] = model
        scores = scores_for_spam(model, validation["message"])
        for threshold in thresholds:
            predictions = predictions_from_scores(scores, threshold)
            metrics = classification_metrics(validation["label"], predictions)
            candidates.append(
                {"parameters": parameters, "threshold": threshold, "metrics": metrics}
            )

    # Select only from validation. Tie-breakers are declared and deterministic.
    best = max(
        candidates,
        key=lambda item: (
            item["metrics"]["macro_f1"],
            item["metrics"]["per_class"]["spam"]["f1-score"],
            item["metrics"]["accuracy"],
            -abs(item["threshold"] - 0.5),
            -item["parameters"]["c_value"],
            item["parameters"]["class_weight"] is None,
        ),
    )
    selected_parameters = best["parameters"]
    selected_threshold = float(best["threshold"])
    selected_model = fitted_models[
        (selected_parameters["c_value"], selected_parameters["class_weight"])
    ]

    validation_scores = scores_for_spam(selected_model, validation["message"])
    validation_predictions = predictions_from_scores(
        validation_scores, selected_threshold
    )
    error_frame = validation[["row_id", "label", "message"]].assign(
        predicted_label=validation_predictions,
        classifier_score=validation_scores,
    )
    error_frame = error_frame[error_frame["label"] != error_frame["predicted_label"]]
    error_frame = error_frame.assign(
        error_type=np.where(error_frame["label"] == "ham", "false_positive", "false_negative")
    )

    validation_unique = validation.drop_duplicates("message", keep="first")
    validation_results = {
        "selection_rule": (
            "Highest validation macro-F1; then spam F1, accuracy, threshold closest "
            "to 0.5, lower C, and no class weighting. Test features and labels were "
            "not used for model or threshold selection."
        ),
        "selected": best,
        "all_candidates": candidates,
        "dummy": {
            "all_rows": evaluate_dummy(dummy, validation),
            "unique_texts": evaluate_dummy(dummy, validation_unique),
        },
        "selected_pipeline": {
            "all_rows": best["metrics"],
            "unique_texts": evaluate_model(
                selected_model, validation_unique, selected_threshold
            ),
        },
        "error_counts": {
            key: int(value)
            for key, value in error_frame["error_type"].value_counts().items()
        },
    }

    config = {
        "task": "experimental English SMS spam/ham baseline",
        "random_seed": SEED,
        "label_mapping": {"ham": "ham", "spam": "spam"},
        "selection_metric": "validation macro-F1",
        "candidate_c_values": [0.5, 1.0, 2.0],
        "candidate_class_weights": [None, "balanced"],
        "candidate_thresholds": thresholds,
        "selected_parameters": selected_parameters,
        "selected_threshold": selected_threshold,
        "tfidf": {
            "analyzer": "word",
            "ngram_range": [1, 2],
            "lowercase": True,
            "min_df": 2,
            "sublinear_tf": True,
        },
    }
    metadata = {
        "model_type": "TF-IDF plus LogisticRegression sklearn Pipeline",
        "training_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "trained_rows": int(len(train)),
        "validation_rows": int(len(validation)),
        "dataset_file": str(DATA_PATH.relative_to(PROJECT_ROOT)),
        "dataset_sha256": sha256(DATA_PATH),
        "split_manifest_file": str(MANIFEST_PATH.relative_to(PROJECT_ROOT)),
        "split_manifest_sha256": sha256(MANIFEST_PATH),
        "versions": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "scikit-learn": sklearn.__version__,
            "joblib": joblib.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "code_version": source_version_identifier(PROJECT_ROOT),
        "limitations": [
            "This is an experimental English SMS spam/ham baseline.",
            "It does not establish performance on phishing, email, job scams, fraud, or modern messages.",
            "The numeric output is a classifier score, not a verified probability of harm.",
        ],
    }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": selected_model,
            "threshold": selected_threshold,
            "labels": ["ham", "spam"],
            "task": config["task"],
        },
        MODEL_PATH,
    )
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    VALIDATION_PATH.write_text(
        json.dumps(validation_results, indent=2) + "\n", encoding="utf-8"
    )
    error_frame.sort_values(["error_type", "row_id"]).to_csv(
        ERRORS_PATH, index=False, lineterminator="\n"
    )
    print(json.dumps(validation_results, indent=2))


if __name__ == "__main__":
    main()
