"""Create deterministic, leakage-aware train/validation/test SMS splits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scamlens.message_split import (
    SimilarityConfig,
    assert_no_group_overlap,
    assign_splits,
    build_similarity_groups,
)
from scamlens.runtime import require_output_permission


INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "uci_sms_spam_baseline.csv"
MANIFEST_PATH = PROJECT_ROOT / "data" / "processed" / "message_split_manifest.csv"
REPORT_PATH = PROJECT_ROOT / "data" / "processed" / "message_split_report.json"
SEED = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite", action="store_true", help="Explicitly replace existing outputs."
    )
    return parser.parse_args()


def distribution(frame: pd.DataFrame) -> dict[str, object]:
    counts = frame["label"].value_counts().sort_index()
    return {
        "rows": int(len(frame)),
        "exact_message_groups": int(frame["exact_message_hash"].nunique()),
        "similarity_groups": int(frame["similarity_group"].nunique()),
        "labels": {
            label: {
                "count": int(count),
                "percentage": round(float(count / len(frame) * 100), 6),
            }
            for label, count in counts.items()
        },
    }


def count_cross_split_audit_pairs(
    pair_frame: pd.DataFrame, assigned: pd.DataFrame
) -> int:
    if pair_frame.empty:
        return 0
    row_to_split = assigned.set_index("row_id")["split"]
    audited = pair_frame.copy()
    audited["left_split"] = audited["left_row_id"].map(row_to_split)
    audited["right_split"] = audited["right_row_id"].map(row_to_split)
    if audited[["left_split", "right_split"]].isna().any().any():
        missing_ids = sorted(
            set(audited.loc[audited["left_split"].isna(), "left_row_id"])
            | set(audited.loc[audited["right_split"].isna(), "right_row_id"])
        )
        raise ValueError(
            f"Similarity audit references row_id values absent from manifest: {missing_ids}"
        )
    return int((audited["left_split"] != audited["right_split"]).sum())


def main() -> None:
    args = parse_args()
    frame = pd.read_csv(INPUT_PATH, keep_default_na=False)
    config = SimilarityConfig()
    grouped, near_pairs = build_similarity_groups(frame, config)

    group_label_counts = grouped.groupby("similarity_group")["label"].nunique()
    conflicting_groups = int((group_label_counts > 1).sum())
    if conflicting_groups:
        raise ValueError(f"Found {conflicting_groups} similarity groups with mixed labels")

    assigned = assign_splits(grouped, seed=SEED)
    assert_no_group_overlap(assigned)

    pair_frame = pd.DataFrame(near_pairs)
    cross_split_audit_pairs = count_cross_split_audit_pairs(pair_frame, assigned)

    report = {
        "task": "experimental English SMS spam/ham baseline",
        "seed": SEED,
        "requested_ratio": {"train": 0.70, "validation": 0.15, "test": 0.15},
        "method": (
            "Exact texts and char_wb TF-IDF cosine-similarity connected components "
            "are assigned through 20-fold StratifiedGroupKFold. A deterministic search "
            "selects three validation and three test folds to minimize row-count and "
            "per-class count drift from 15%; the other fourteen folds form train."
        ),
        "similarity": {
            "analyzer": config.analyzer,
            "ngram_range": [config.ngram_min, config.ngram_max],
            "lowercase": config.lowercase,
            "grouping_threshold": config.grouping_threshold,
            "audit_threshold": config.audit_threshold,
            "pairs_at_or_above_audit_threshold": len(near_pairs),
            "pairs_at_or_above_grouping_threshold": sum(
                bool(pair["grouped"]) for pair in near_pairs
            ),
            "cross_split_pairs_between_audit_and_grouping_thresholds": cross_split_audit_pairs,
            "mixed_label_similarity_groups": conflicting_groups,
        },
        "overall": distribution(assigned),
        "splits": {
            split: distribution(assigned[assigned["split"] == split])
            for split in ("train", "validation", "test")
        },
        "fold_assignment": {
            split: sorted(
                int(value)
                for value in assigned.loc[assigned["split"] == split, "fold"].unique()
            )
            for split in ("train", "validation", "test")
        },
        "overlap_checks": {
            "exact_message_groups_across_splits": 0,
            "similarity_groups_across_splits": 0,
        },
        "limitations": [
            "Cosine similarity is a lexical approximation and cannot identify every semantic variant.",
            "Pairs below 0.90 may remain across splits, including some pairs found by the 0.80 audit.",
            "Connected components can merge texts transitively even when every pair is not directly similar.",
            "The source has no timestamps, so a temporal split is impossible.",
        ],
    }

    manifest = assigned[
        [
            "row_id",
            "label",
            "exact_message_hash",
            "similarity_group",
            "fold",
            "split",
        ]
    ].sort_values("row_id")
    require_output_permission(
        [MANIFEST_PATH, REPORT_PATH], overwrite=args.overwrite
    )
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(MANIFEST_PATH, index=False, lineterminator="\n")
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
