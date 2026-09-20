"""Prepare the UCI SMS Spam Collection as a temporary spam/ham baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scamlens.runtime import require_output_permission


DEFAULT_INPUT = (
    PROJECT_ROOT / "data" / "raw" / "uci_sms_spam_collection" / "SMSSpamCollection"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "uci_sms_spam_baseline.csv"
DEFAULT_REPORT = (
    PROJECT_ROOT / "data" / "processed" / "uci_sms_spam_baseline_stats.json"
)
EXPECTED_LABELS = {"ham", "spam"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare the UCI SMS spam/ham dataset without dropping duplicates."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--overwrite", action="store_true", help="Explicitly replace existing outputs."
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_raw_dataset(path: Path) -> pd.DataFrame:
    """Parse the first tab as the delimiter and preserve message text verbatim."""
    if not path.is_file():
        raise FileNotFoundError(f"Raw dataset not found: {path}")

    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8", newline="") as source:
        for row_id, raw_line in enumerate(source, start=1):
            line = raw_line.removesuffix("\n").removesuffix("\r")
            label, separator, message = line.partition("\t")
            if not separator:
                raise ValueError(f"Row {row_id} does not contain a tab delimiter")
            rows.append({"row_id": row_id, "label": label, "message": message})

    return pd.DataFrame(rows, columns=["row_id", "label", "message"])


def validate_dataset(frame: pd.DataFrame) -> None:
    actual_labels = set(frame["label"].unique())
    if actual_labels != EXPECTED_LABELS:
        raise ValueError(
            f"Expected labels {sorted(EXPECTED_LABELS)}, found {sorted(actual_labels)}"
        )
    if frame[["label", "message"]].isna().any().any():
        raise ValueError("Missing labels or messages are not allowed")
    if frame["message"].eq("").any():
        raise ValueError("Empty messages are not allowed")


def length_summary(series: pd.Series) -> dict[str, float | int]:
    description = series.describe(percentiles=[0.25, 0.5, 0.75])
    return {
        "min": int(description["min"]),
        "p25": float(description["25%"]),
        "median": float(description["50%"]),
        "mean": float(description["mean"]),
        "p75": float(description["75%"]),
        "max": int(description["max"]),
    }


def build_report(frame: pd.DataFrame, input_path: Path) -> dict[str, object]:
    message_counts = frame.groupby("message", sort=False).size()
    pair_counts = frame.groupby(["label", "message"], sort=False).size()
    labels_per_message = frame.groupby("message", sort=False)["label"].nunique()
    class_counts = frame["label"].value_counts().sort_index()

    working = frame.assign(
        length_chars=frame["message"].str.len(),
        length_words=frame["message"].str.split().str.len(),
    )

    report: dict[str, object] = {
        "dataset": "UCI SMS Spam Collection",
        "task": "experimental spam/ham SMS classification baseline",
        "raw_file": str(input_path.relative_to(PROJECT_ROOT)),
        "raw_sha256": sha256(input_path),
        "rows": int(len(frame)),
        "columns": {
            "row_id": "integer (one-based source line number)",
            "label": "string: ham or spam",
            "message": "string: original SMS text",
        },
        "labels": sorted(EXPECTED_LABELS),
        "class_distribution": {
            label: {
                "count": int(count),
                "percentage": round(float(count / len(frame) * 100), 6),
            }
            for label, count in class_counts.items()
        },
        "missing_values": {
            column: int(value) for column, value in frame.isna().sum().items()
        },
        "duplicates": {
            "message_groups": int((message_counts > 1).sum()),
            "message_rows_in_groups": int(message_counts[message_counts > 1].sum()),
            "message_occurrences_beyond_first": int(frame.duplicated("message").sum()),
            "message_label_groups": int((pair_counts > 1).sum()),
            "message_label_rows_in_groups": int(pair_counts[pair_counts > 1].sum()),
            "message_label_occurrences_beyond_first": int(
                frame.duplicated(["label", "message"]).sum()
            ),
            "conflicting_label_message_groups": int((labels_per_message > 1).sum()),
        },
        "text_length": {
            "characters": length_summary(working["length_chars"]),
            "words": length_summary(working["length_words"]),
            "by_label": {
                label: {
                    "characters": length_summary(group["length_chars"]),
                    "words": length_summary(group["length_words"]),
                }
                for label, group in working.groupby("label", sort=True)
            },
        },
        "representative_examples": {
            label: group.head(3)[["row_id", "message"]].to_dict(orient="records")
            for label, group in frame.groupby("label", sort=True)
        },
        "processing": {
            "rows_removed": 0,
            "duplicates_removed": 0,
            "text_normalization": "none",
            "notes": "Only column names and a source row_id were added.",
        },
    }
    return report


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    report_path = args.report.resolve()

    frame = load_raw_dataset(input_path)
    validate_dataset(frame)
    report = build_report(frame, input_path)

    require_output_permission([output_path, report_path], overwrite=args.overwrite)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8", lineterminator="\n")
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nProcessed dataset: {output_path.relative_to(PROJECT_ROOT)}")
    print(f"Statistics report: {report_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
