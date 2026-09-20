"""Evaluate the finalized SMS baseline once on the untouched test split."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scamlens.message_model import (  # noqa: E402
    classification_metrics,
    predictions_from_scores,
    scores_for_spam,
)
from scamlens.data_validation import validate_and_merge_dataset_manifest  # noqa: E402
from scamlens.runtime import (  # noqa: E402
    require_output_permission,
    verify_file_hashes,
)


DATA_PATH = PROJECT_ROOT / "data" / "processed" / "uci_sms_spam_baseline.csv"
MANIFEST_PATH = PROJECT_ROOT / "data" / "processed" / "message_split_manifest.csv"
MODEL_PATH = PROJECT_ROOT / "artifacts" / "message" / "sms_spam_ham_pipeline.joblib"
OUTPUT_PATH = PROJECT_ROOT / "artifacts" / "message" / "test_metrics.json"
ERRORS_PATH = PROJECT_ROOT / "artifacts" / "message" / "test_errors.csv"
METADATA_PATH = PROJECT_ROOT / "artifacts" / "message" / "metadata.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite", action="store_true", help="Explicitly replace existing reports."
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate_pipeline(bundle: dict, frame: pd.DataFrame) -> tuple[dict, object, object]:
    scores = scores_for_spam(bundle["pipeline"], frame["message"])
    predictions = predictions_from_scores(scores, float(bundle["threshold"]))
    return classification_metrics(frame["label"], predictions), scores, predictions


def main() -> None:
    args = parse_args()
    require_output_permission([OUTPUT_PATH, ERRORS_PATH], overwrite=args.overwrite)
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    verify_file_hashes(
        {
            DATA_PATH: metadata.get("dataset_sha256", ""),
            MANIFEST_PATH: metadata.get("split_manifest_sha256", ""),
        }
    )

    data = pd.read_csv(DATA_PATH, keep_default_na=False)
    manifest = pd.read_csv(MANIFEST_PATH, keep_default_na=False)
    merged = validate_and_merge_dataset_manifest(data, manifest)
    train = merged[merged["split"] == "train"]
    test = merged[merged["split"] == "test"].copy()
    test_unique = test.drop_duplicates("message", keep="first")
    bundle = joblib.load(MODEL_PATH)

    dummy = DummyClassifier(strategy="most_frequent", random_state=42)
    dummy.fit(train[["message"]], train["label"])
    pipeline_metrics, scores, predictions = evaluate_pipeline(bundle, test)
    unique_metrics, _, _ = evaluate_pipeline(bundle, test_unique)

    report = {
        "task": "experimental English SMS spam/ham baseline",
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_sha256": sha256(MODEL_PATH),
        "threshold": float(bundle["threshold"]),
        "test_rows": int(len(test)),
        "test_unique_texts": int(len(test_unique)),
        "dummy": {
            "all_rows": classification_metrics(
                test["label"], dummy.predict(test[["message"]])
            ),
            "unique_texts": classification_metrics(
                test_unique["label"], dummy.predict(test_unique[["message"]])
            ),
        },
        "selected_pipeline": {
            "all_rows": pipeline_metrics,
            "unique_texts": unique_metrics,
        },
        "warning": (
            "These results do not establish performance on phishing, email, "
            "job scams, fraud, or modern messages."
        ),
    }

    errors = test[["row_id", "label", "message"]].assign(
        predicted_label=predictions,
        classifier_score=scores,
    )
    errors = errors[errors["label"] != errors["predicted_label"]]
    errors.sort_values("row_id").to_csv(ERRORS_PATH, index=False, lineterminator="\n")
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
