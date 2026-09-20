"""Train and evaluate the controlled within-corpus three-class email baseline."""

from __future__ import annotations

import json
from collections import Counter
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

from scamlens.email_inference import EMAIL_TASK
from scamlens.email_model import (
    EMAIL_LABELS,
    RANDOM_SEED,
    build_email_pipeline,
    email_classification_metrics,
    fit_email_model,
)
from scamlens.email_validation import (
    validate_email_dataset_manifest,
    validate_feature_columns,
)
from scamlens.runtime import require_output_permission, sha256, source_version_identifier


DATA_PATH = PROJECT_ROOT / "data/processed/email_mendeley_three_class.csv"
MANIFEST_PATH = PROJECT_ROOT / "data/processed/email_mendeley_split_manifest.csv"
PREPARATION_CONFIG_PATH = PROJECT_ROOT / "data/processed/email_mendeley_config.json"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts/email/baseline_v1"
MODEL_PATH = ARTIFACT_DIR / "email_pipeline.joblib"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"
CONFUSION_PATH = ARTIFACT_DIR / "confusion_matrices.json"
METADATA_PATH = ARTIFACT_DIR / "metadata.json"
CONFIG_PATH = ARTIFACT_DIR / "config.json"
LABELS_PATH = ARTIFACT_DIR / "label_mapping.json"
ERRORS_PATH = ARTIFACT_DIR / "error_analysis.json"
MODEL_CARD_PATH = PROJECT_ROOT / "docs/EMAIL_MODEL_CARD.md"


def distribution(frame: pd.DataFrame) -> dict[str, object]:
    counts = frame["label"].value_counts()
    return {
        "rows": len(frame),
        "classes": {
            label: {
                "count": int(counts.get(label, 0)),
                "percentage": round(float(counts.get(label, 0) / len(frame) * 100), 6),
            }
            for label in EMAIL_LABELS
        },
    }


def evaluate(model: object, frame: pd.DataFrame) -> dict[str, object]:
    return email_classification_metrics(frame["label"], model.predict(frame["model_text"]))


def evaluate_dummy(model: DummyClassifier, frame: pd.DataFrame) -> dict[str, object]:
    return email_classification_metrics(
        frame["label"], model.predict(frame[["model_text"]])
    )


def aggregate_error_analysis(
    frame: pd.DataFrame, predictions: np.ndarray
) -> dict[str, object]:
    audited = frame.assign(predicted_label=predictions)
    transitions: dict[str, object] = {}
    markers = ["[EMAIL]", "[URL]", "[IP_ADDRESS]", "[PHONE]", "[NUMERIC_ID]", "[NAME]"]
    for actual in EMAIL_LABELS:
        for predicted in EMAIL_LABELS:
            if actual == predicted:
                continue
            part = audited[
                (audited["label"] == actual) & (audited["predicted_label"] == predicted)
            ]
            transitions[f"{actual}_to_{predicted}"] = {
                "count": len(part),
                "median_subject_characters": (
                    float(part["subject"].str.len().median()) if len(part) else None
                ),
                "median_body_characters": (
                    float(part["body"].str.len().median()) if len(part) else None
                ),
                "source_container_counts": {
                    key: int(value)
                    for key, value in part["source_container"].value_counts().items()
                },
                "rows_containing_redaction_markers": {
                    marker: int(part["model_text"].str.contains(marker, regex=False).sum())
                    for marker in markers
                },
            }
    source_style = {}
    for (container, actual), part in audited.groupby(["source_container", "label"]):
        source_style[f"{container}:{actual}"] = {
            "rows": len(part),
            "correct": int((part["label"] == part["predicted_label"]).sum()),
            "accuracy": float((part["label"] == part["predicted_label"]).mean()),
        }
    return {
        "privacy": "Aggregate descriptions only; no email excerpts are stored.",
        "error_transitions": transitions,
        "correctness_by_source_container_and_class": source_style,
        "interpretation": (
            "Differences by mbox/eml container are evidence that corpus/style artifacts "
            "may affect both errors and correct predictions. They do not establish a "
            "causal feature attribution and source confounding remains unresolved."
        ),
    }


def render_model_card(metrics: dict[str, object], metadata: dict[str, object]) -> str:
    validation = metrics["logistic_regression"]["validation"]
    test = metrics["logistic_regression"]["test"]
    rows = []
    for label in EMAIL_LABELS:
        item = test["per_class"][label]
        rows.append(
            f"| {label} | {item['precision']:.6f} | {item['recall']:.6f} | "
            f"{item['f1']:.6f} | {item['support']} |"
        )
    return f"""# Email Model Card

## Model summary

This artifact is a controlled, exploratory three-class email baseline for
`Valid`, `Spam`, and `Phishing`. Its evaluation scope is **within corpus only**.
Real-world, source-independent, and user-independent generalization are not
established.

The sklearn Pipeline combines word TF-IDF with multinomial-compatible Logistic
Regression. It was trained on {metadata['split_distribution']['train']['rows']}
rows with random seed {RANDOM_SEED}. Only the redacted Subject and Body text are
model input. No source, UID, ID, language, filename, split, duplicate-group,
contributor, or translation metadata is used as a feature.

## Data and evaluation

The source is version 1 of the Mendeley *Multilingual Phishing Email Dataset for
Low-Resource Languages*. The English anchor was prepared with deterministic
privacy redaction, and normalized duplicate groups were kept within one fixed
train/validation/test split. Translation variants were excluded.

The corpus is imbalanced: Valid is about 71%, Spam 20%, and Phishing 9%. Model
selection used validation macro-F1 over a small declared grid. Test was evaluated
once after the selection was frozen.

- Validation accuracy: {validation['accuracy']:.6f}
- Validation macro-F1: {validation['macro_f1']:.6f}
- Test accuracy: {test['accuracy']:.6f}
- Test macro-F1: {test['macro_f1']:.6f}
- Test weighted-F1: {test['weighted_f1']:.6f}

### Test performance by class

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

Confusion-matrix values and complete validation/test metrics are stored in the
artifact directory.

## Intended use

- Reproducible technical exploration of a three-class text classifier.
- Comparing simple baselines within this exact prepared corpus.
- Testing future local application integration after explicit approval.

## Limitations and known failure modes

- The audit concluded Decision B: meaningful source-aware generalization is not
  supported by the corpus.
- Valid mail is concentrated in only three source values, and class is strongly
  associated with mbox/eml provenance.
- Removing metadata does not remove vocabulary, topic, formatting, campaign, or
  collection artifacts embedded in Subject and Body.
- Privacy redaction reduces exposure but cannot guarantee that every personal or
  contextual identifier was removed.
- Surface duplicate grouping cannot detect every semantic paraphrase.
- Class imbalance makes accuracy insufficient; macro-F1 and Phishing/Spam
  precision and recall must be considered.
- The label annotation procedure and collection period are not fully documented.

## Prohibited interpretation

This model must not be described as a production phishing detector, evidence of
real-world generalization, source-independent performance, user-independent
performance, or proof that an individual email is safe or malicious.
"""


def main() -> None:
    outputs = [
        MODEL_PATH, METRICS_PATH, CONFUSION_PATH, METADATA_PATH, CONFIG_PATH,
        LABELS_PATH, ERRORS_PATH, MODEL_CARD_PATH,
    ]
    require_output_permission(outputs, overwrite=False)
    data = pd.read_csv(DATA_PATH, keep_default_na=False)
    manifest = pd.read_csv(MANIFEST_PATH, keep_default_na=False)
    preparation_config = json.loads(PREPARATION_CONFIG_PATH.read_text(encoding="utf-8"))
    validate_feature_columns(preparation_config["feature_columns"])
    merged = validate_email_dataset_manifest(data, manifest)
    splits = {
        name: merged[merged["split"] == name].copy()
        for name in ("train", "validation", "test")
    }

    dummy = DummyClassifier(strategy="prior", random_state=RANDOM_SEED)
    dummy.fit(splits["train"][["model_text"]], splits["train"]["label"])

    candidates = []
    fitted = {}
    for class_weight in (None, "balanced"):
        for c_value in (0.5, 1.0, 2.0):
            model = build_email_pipeline(c_value=c_value, class_weight=class_weight)
            fit_email_model(model, splits["train"]["model_text"], splits["train"]["label"])
            validation_metrics = evaluate(model, splits["validation"])
            key = (c_value, class_weight)
            fitted[key] = model
            candidates.append(
                {
                    "parameters": {"C": c_value, "class_weight": class_weight},
                    "validation_metrics": validation_metrics,
                }
            )
    selected = max(
        candidates,
        key=lambda item: (
            item["validation_metrics"]["macro_f1"],
            item["validation_metrics"]["per_class"]["Phishing"]["recall"],
            item["validation_metrics"]["weighted_f1"],
            -item["parameters"]["C"],
            item["parameters"]["class_weight"] is None,
        ),
    )
    selected_parameters = selected["parameters"]
    selected_model = fitted[(selected_parameters["C"], selected_parameters["class_weight"])]

    # The choice is frozen above using validation only. Test is evaluated once here.
    test_predictions = selected_model.predict(splits["test"]["model_text"])
    test_metrics = email_classification_metrics(splits["test"]["label"], test_predictions)
    validation_predictions = selected_model.predict(splits["validation"]["model_text"])
    dummy_metrics = {
        "purpose": (
            "The prior-strategy DummyClassifier ignores text and predicts the most "
            "frequent training class, providing a class-imbalance reference."
        ),
        "validation": evaluate_dummy(dummy, splits["validation"]),
        "test": evaluate_dummy(dummy, splits["test"]),
    }
    metrics = {
        "evaluation_scope": "within_corpus_only",
        "generalization_status": "not_established",
        "selection_metric": "validation macro-F1",
        "selection_rule": (
            "Highest validation macro-F1, then Phishing recall, weighted-F1, lower C, "
            "and no class weighting. Test was not used for selection."
        ),
        "dummy_classifier": dummy_metrics,
        "logistic_regression": {
            "selected_parameters": selected_parameters,
            "validation": selected["validation_metrics"],
            "test": test_metrics,
        },
        "validation_candidates": candidates,
    }
    error_analysis = {
        "validation": aggregate_error_analysis(splits["validation"], validation_predictions),
        "test": aggregate_error_analysis(splits["test"], test_predictions),
    }
    label_mapping = {
        "ordered_labels": EMAIL_LABELS,
        "label_to_index": {label: index for index, label in enumerate(EMAIL_LABELS)},
        "index_to_label": {str(index): label for index, label in enumerate(EMAIL_LABELS)},
    }
    config = {
        "random_seed": RANDOM_SEED,
        "evaluation_scope": "within_corpus_only",
        "generalization_status": "not_established",
        "feature_columns": ["subject", "body"],
        "model_input": "Subject and Body joined into the prepared model_text field",
        "forbidden_metadata_used": False,
        "tfidf": {
            "analyzer": "word", "ngram_range": [1, 2], "lowercase": True,
            "min_df": 2, "sublinear_tf": True,
        },
        "candidate_C": [0.5, 1.0, 2.0],
        "candidate_class_weight": [None, "balanced"],
        "selected_parameters": selected_parameters,
    }
    metadata = {
        "task": EMAIL_TASK,
        "model_type": "TF-IDF plus LogisticRegression sklearn Pipeline",
        "evaluation_scope": "within_corpus_only",
        "generalization_status": "not_established",
        "training_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_file": str(DATA_PATH.relative_to(PROJECT_ROOT)),
        "dataset_sha256": sha256(DATA_PATH),
        "manifest_file": str(MANIFEST_PATH.relative_to(PROJECT_ROOT)),
        "manifest_sha256": sha256(MANIFEST_PATH),
        "random_seed": RANDOM_SEED,
        "feature_configuration": config["tfidf"] | {"input_fields": ["subject", "body"]},
        "class_distribution": distribution(merged),
        "split_distribution": {name: distribution(frame) for name, frame in splits.items()},
        "label_mapping": label_mapping,
        "versions": {
            "python": platform.python_version(), "pandas": pd.__version__,
            "scikit-learn": sklearn.__version__, "joblib": joblib.__version__,
            "numpy": np.__version__, "scipy": scipy.__version__,
        },
        "code_version": source_version_identifier(PROJECT_ROOT),
    }
    bundle = {
        "pipeline": selected_model,
        "labels": EMAIL_LABELS,
        "label_mapping": label_mapping["label_to_index"],
        "task": EMAIL_TASK,
        "evaluation_scope": "within_corpus_only",
        "generalization_status": "not_established",
        "feature_columns": ["subject", "body"],
    }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=False)
    joblib.dump(bundle, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    CONFUSION_PATH.write_text(
        json.dumps(
            {
                "labels": EMAIL_LABELS,
                "dummy_validation": dummy_metrics["validation"]["confusion_matrix"],
                "dummy_test": dummy_metrics["test"]["confusion_matrix"],
                "logistic_validation": selected["validation_metrics"]["confusion_matrix"],
                "logistic_test": test_metrics["confusion_matrix"],
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    LABELS_PATH.write_text(json.dumps(label_mapping, indent=2) + "\n", encoding="utf-8")
    ERRORS_PATH.write_text(json.dumps(error_analysis, indent=2) + "\n", encoding="utf-8")
    MODEL_CARD_PATH.write_text(render_model_card(metrics, metadata), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
