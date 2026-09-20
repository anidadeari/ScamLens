"""Prepare a controlled within-corpus Mendeley email experiment without training."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scamlens.email_data import (
    EXPECTED_EMAIL_LABELS,
    canonical_text,
    digest_text,
    redact_text,
    validate_raw_records,
)
from scamlens.message_split import assign_splits
from scamlens.runtime import require_output_permission


RAW_ARCHIVE = (
    PROJECT_ROOT
    / "data/raw/email/mendeley_multilingual_phishing_v1/English_base.zip"
)
OUTPUT_DATA = PROJECT_ROOT / "data/processed/email_mendeley_three_class.csv"
OUTPUT_MANIFEST = PROJECT_ROOT / "data/processed/email_mendeley_split_manifest.csv"
OUTPUT_CONFIG = PROJECT_ROOT / "data/processed/email_mendeley_config.json"
OUTPUT_REPORT = PROJECT_ROOT / "data/processed/email_mendeley_report.json"
SEED = 42
SPLIT_SCOPE = "within_corpus_only"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite", action="store_true", help="Explicitly replace existing outputs."
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_anchor(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        raise FileNotFoundError(f"Raw archive not found: {path}")
    records: list[dict[str, object]] = []
    with zipfile.ZipFile(path) as archive:
        for published_split in ("train", "val", "test"):
            member = f"English_base/{published_split}.json"
            part = json.loads(archive.read(member))
            if not isinstance(part, list):
                raise ValueError(f"Expected a JSON list in {member}")
            records.extend(record | {"published_split": published_split} for record in part)
    validate_raw_records(records)
    return records


def source_feasibility(records: list[dict[str, object]]) -> dict[str, object]:
    by_source: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        by_source[str(record["source"])][str(record["label"])] += 1
    valid_sizes = sorted(
        (sum(counts.values()) for counts in by_source.values() if counts["Valid"]),
        reverse=True,
    )
    signatures = Counter(
        tuple(label for label in ("Valid", "Spam", "Phishing") if counts[label])
        for counts in by_source.values()
    )
    target_holdout = round(len(records) * 0.15)
    container_class_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        source = str(record["source"]).lower()
        container = "mbox" if source.endswith(".mbox") else "eml" if source.endswith(".eml") else "other"
        container_class_counts[container][str(record["label"])] += 1
    return {
        "source_field_documented_as_user_identity": False,
        "documented_user_to_row_mapping_available": False,
        "distinct_source_values": len(by_source),
        "distinct_source_values_by_class": {
            label: sum(bool(counts[label]) for counts in by_source.values())
            for label in ("Valid", "Spam", "Phishing")
        },
        "source_class_signatures": {
            "+".join(signature): count for signature, count in sorted(signatures.items())
        },
        "valid_supporting_source_group_sizes": valid_sizes,
        "rows_by_source_container_and_class": {
            container: {
                label: counts[label] for label in ("Valid", "Spam", "Phishing")
            }
            for container, counts in sorted(container_class_counts.items())
        },
        "target_rows_per_15_percent_holdout": target_holdout,
        "approximately_70_15_15_source_group_split_feasible": False,
        "reason": (
            "Valid occurs in exactly three source values with 1578, 1417, and 692 "
            "rows. Two separate holdouts target about 777 rows each, but only the "
            "692-row Valid group fits either target. Assigning one Valid source to "
            "each split is technically possible but neither proportionally balanced "
            "nor evidence of user-level generalization."
        ),
    }


def leakage_term_audit(records: list[dict[str, object]]) -> dict[str, object]:
    patterns = {
        "phishing": r"\bphish(?:ing|ed)?\b",
        "spam": r"\bspam(?:mer|ming)?\b",
        "valid": r"\bvalid\b",
        "legitimate": r"\blegitimate\b",
        "ham": r"\bham\b",
        "dataset_or_corpus": r"\b(?:dataset|corpus)\b",
        "enron": r"\benron\b",
        "nazario": r"\bnazario\b",
        "known_source_container_names": (
            r"\b(?:category updates|category social|category promotions|"
            r"spam|trash|youmna-promo)\.mbox\b"
        ),
        "explicit_class_annotation": (
            r"\b(?:class|label)\s*[:=]\s*(?:valid|spam|phishing)\b"
        ),
    }
    result: dict[str, object] = {}
    for name, pattern in patterns.items():
        counts = Counter(
            str(record["label"])
            for record in records
            if re.search(
                pattern,
                f"{record.get('subject') or ''}\n{record.get('text') or ''}",
                re.IGNORECASE,
            )
        )
        result[name] = {
            "total_rows": sum(counts.values()),
            "by_class": {label: counts[label] for label in sorted(EXPECTED_EMAIL_LABELS)},
        }
    return result


def prepare(records: list[dict[str, object]]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    prepared_rows: list[dict[str, object]] = []
    manifest_rows: list[dict[str, object]] = []
    redactions: Counter[str] = Counter()
    redactions_by_class: dict[str, Counter[str]] = defaultdict(Counter)

    for row_id, record in enumerate(records, start=1):
        subject, subject_counts = redact_text(record.get("subject"))
        body, body_counts = redact_text(record.get("text"))
        for name, count in subject_counts.items():
            redactions[f"subject_{name}"] += count
            redactions_by_class[str(record["label"])][f"subject_{name}"] += count
        for name, count in body_counts.items():
            redactions[f"body_{name}"] += count
            redactions_by_class[str(record["label"])][f"body_{name}"] += count

        canonical = canonical_text(subject, body)
        duplicate_group = f"email_{digest_text(canonical)[:20]}"
        model_text = f"Subject: {subject}\n\nBody: {body}"
        prepared_rows.append(
            {
                "row_id": row_id,
                "label": record["label"],
                "subject": subject,
                "body": body,
                "model_text": model_text,
                "duplicate_group": duplicate_group,
            }
        )
        raw_source = str(record["source"])
        manifest_rows.append(
            {
                "row_id": row_id,
                "uid": record["uid"],
                "label": record["label"],
                "duplicate_group": duplicate_group,
                "source_hash": digest_text(raw_source),
                "source_container": (
                    "mbox" if raw_source.lower().endswith(".mbox") else "eml"
                    if raw_source.lower().endswith(".eml")
                    else "other"
                ),
                "published_split": record["published_split"],
            }
        )

    data = pd.DataFrame(prepared_rows)
    manifest = pd.DataFrame(manifest_rows)
    group_labels = data.groupby("duplicate_group")["label"].nunique()
    if (group_labels > 1).any():
        raise ValueError("A normalized duplicate group contains conflicting labels")

    split_input = manifest.rename(columns={"duplicate_group": "similarity_group"}).assign(
        exact_message_hash=data["model_text"].map(digest_text)
    )
    assigned = assign_splits(split_input, seed=SEED, folds=20)
    manifest["fold"] = assigned["fold"]
    manifest["split"] = assigned["split"]
    if manifest.groupby("duplicate_group")["split"].nunique().max() != 1:
        raise AssertionError("A duplicate group crosses within-corpus splits")
    if set(manifest["split"]) != {"train", "validation", "test"}:
        raise AssertionError("All three splits are required")
    for split, part in manifest.groupby("split"):
        if set(part["label"]) != EXPECTED_EMAIL_LABELS:
            raise AssertionError(f"Split {split} does not contain all three classes")

    audit = {
        "redaction_counts": dict(sorted(redactions.items())),
        "redaction_counts_by_class": {
            label: dict(sorted(redactions_by_class[label].items()))
            for label in sorted(EXPECTED_EMAIL_LABELS)
        },
        "missing_before_redaction": {
            "subject": sum(not str(record.get("subject") or "").strip() for record in records),
            "body": sum(not str(record.get("text") or "").strip() for record in records),
        },
        "empty_after_redaction": {
            "subject": int(data["subject"].eq("").sum()),
            "body": int(data["body"].eq("").sum()),
        },
        "duplicate_groups": int(data["duplicate_group"].nunique()),
        "rows_in_non_singleton_duplicate_groups": int(
            data["duplicate_group"].map(data["duplicate_group"].value_counts()).gt(1).sum()
        ),
        "duplicate_groups_crossing_splits": 0,
    }
    return data, manifest, audit


def split_stats(manifest: pd.DataFrame) -> dict[str, object]:
    result: dict[str, object] = {}
    for split in ("train", "validation", "test"):
        part = manifest[manifest["split"] == split]
        counts = part["label"].value_counts()
        result[split] = {
            "rows": len(part),
            "duplicate_groups": int(part["duplicate_group"].nunique()),
            "classes": {
                label: {
                    "count": int(counts.get(label, 0)),
                    "percentage": round(float(counts.get(label, 0) / len(part) * 100), 6),
                }
                for label in sorted(EXPECTED_EMAIL_LABELS)
            },
        }
    return result


def main() -> None:
    args = parse_args()
    records = load_anchor(RAW_ARCHIVE)
    data, manifest, audit = prepare(records)
    config = {
        "dataset": "Mendeley Multilingual Phishing Email Dataset, English anchor",
        "version": 1,
        "task": "controlled three-class Valid/Spam/Phishing email experiment",
        "scope": SPLIT_SCOPE,
        "seed": SEED,
        "feature_columns": ["subject", "body"],
        "model_input_column": "model_text",
        "excluded_from_features": [
            "source", "source filename", "uid", "id", "orig_lang",
            "published_split", "source_hash", "source_container", "duplicate_group",
        ],
        "missing_policy": "Missing Subject or Body becomes an empty string; rows are retained.",
        "redaction_policy": (
            "Extract visible text from HTML-like bodies, then consistently replace email "
            "addresses, URLs, IP addresses, phone-like strings, long numeric identifiers, "
            "and names in common greeting forms. This is risk reduction, not guaranteed "
            "de-identification; residual names and contextual identifiers may remain."
        ),
        "duplicate_policy": (
            "Group by SHA-256 of redacted Subject+Body after NFKC, case folding, "
            "punctuation removal, and whitespace collapse. Keep every row and keep each "
            "group in one split. Semantic paraphrases are not guaranteed to be grouped."
        ),
        "translation_policy": "translation_output is excluded entirely.",
        "generalization_claim": "none; this is a within-corpus split",
        "raw_archive_sha256": sha256_file(RAW_ARCHIVE),
    }
    report = {
        "decision": "B",
        "decision_text": (
            "Only a limited within-corpus experiment is supported; generalization "
            "evaluation requires additional provenance-balanced data."
        ),
        "rows": len(data),
        "class_counts": data["label"].value_counts().sort_index().to_dict(),
        "source_split_feasibility": source_feasibility(records),
        "label_leakage_term_audit": leakage_term_audit(records),
        "preparation_audit": audit,
        "within_corpus_splits": split_stats(manifest),
        "within_corpus_source_overlap": {
            "source_hashes_crossing_splits": int(
                (manifest.groupby("source_hash")["split"].nunique() > 1).sum()
            ),
            "note": (
                "Source overlap is intentional in this limited split and prevents it "
                "from measuring source-level generalization. Source hashes are retained "
                "only in the manifest and are excluded from model features."
            ),
        },
        "integrity": {
            "processed_rows_equal_raw_rows": len(data) == len(records),
            "manifest_rows_equal_raw_rows": len(manifest) == len(records),
            "row_ids_match": set(data["row_id"]) == set(manifest["row_id"]),
            "labels_match": data.set_index("row_id")["label"].equals(
                manifest.set_index("row_id")["label"]
            ),
            "uid_unique": bool(manifest["uid"].is_unique),
            "translation_output_used": False,
            "source_metadata_used_as_features": False,
        },
        "limitations": [
            "The source field is not documented as a user identity or source family.",
            "Removing metadata does not remove stylistic or formatting source confounds.",
            "The deterministic redaction rules cannot guarantee removal of every personal name or contextual identifier.",
            "Surface normalization does not detect all semantic paraphrases.",
            "The depositor does not document the label annotation procedure or collection period.",
        ],
    }
    outputs = [OUTPUT_DATA, OUTPUT_MANIFEST, OUTPUT_CONFIG, OUTPUT_REPORT]
    require_output_permission(outputs, overwrite=args.overwrite)
    OUTPUT_DATA.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUTPUT_DATA, index=False, lineterminator="\n")
    manifest.to_csv(OUTPUT_MANIFEST, index=False, lineterminator="\n")
    OUTPUT_CONFIG.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    report["integrity"]["processed_data_sha256"] = sha256_file(OUTPUT_DATA)
    report["integrity"]["manifest_sha256"] = sha256_file(OUTPUT_MANIFEST)
    report["integrity"]["config_sha256"] = sha256_file(OUTPUT_CONFIG)
    OUTPUT_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
