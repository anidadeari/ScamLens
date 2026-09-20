"""Focused tests for leakage-aware SMS splitting."""

from __future__ import annotations

import pandas as pd
import pytest

from scamlens.message_split import (
    SimilarityConfig,
    assert_no_group_overlap,
    assign_splits,
    build_similarity_groups,
    message_hash,
)
from scripts.create_message_splits import count_cross_split_audit_pairs


def test_exact_and_near_duplicates_share_a_group() -> None:
    frame = pd.DataFrame(
        {
            "row_id": [1, 2, 3, 4],
            "label": ["spam", "spam", "spam", "ham"],
            "message": [
                "Claim your cash prize today by calling 0900 now",
                "Claim your cash prize today by calling 0900 now",
                "Claim your cash prize today by calling 0901 now",
                "Are we still meeting for lunch tomorrow?",
            ],
        }
    )
    grouped, _ = build_similarity_groups(
        frame, SimilarityConfig(grouping_threshold=0.85, audit_threshold=0.80)
    )

    assert grouped.loc[0, "similarity_group"] == grouped.loc[1, "similarity_group"]
    assert grouped.loc[0, "similarity_group"] == grouped.loc[2, "similarity_group"]
    assert grouped.loc[0, "similarity_group"] != grouped.loc[3, "similarity_group"]


def test_grouped_split_has_no_overlap_and_is_reproducible() -> None:
    rows = []
    for index in range(80):
        label = "spam" if index % 4 == 0 else "ham"
        message = f"unique {label} example number {index} token-{index * 7919}"
        rows.append(
            {
                "row_id": index + 1,
                "label": label,
                "message": message,
                "exact_message_hash": message_hash(message),
                "similarity_group": f"group_{index:03d}",
            }
        )
    rows.append(rows[0] | {"row_id": 81})
    frame = pd.DataFrame(rows)

    first = assign_splits(frame, seed=42)
    second = assign_splits(frame, seed=42)

    assert first["split"].tolist() == second["split"].tolist()
    assert_no_group_overlap(first)
    assert set(first["split"]) == {"train", "validation", "test"}


@pytest.mark.parametrize(
    ("audit", "grouping"),
    [(-0.1, 0.9), (0.9, 0.8), (0.8, 1.1), (float("nan"), 0.9), (0.8, float("inf"))],
)
def test_invalid_similarity_thresholds_are_rejected(
    audit: float, grouping: float
) -> None:
    with pytest.raises(ValueError):
        SimilarityConfig(audit_threshold=audit, grouping_threshold=grouping)


def test_current_split_implementation_rejects_other_fold_counts() -> None:
    frame = pd.DataFrame(
        {
            "label": ["ham", "spam"],
            "similarity_group": ["a", "b"],
        }
    )
    with pytest.raises(ValueError, match="requires folds=20"):
        assign_splits(frame, folds=10)


def test_similarity_audit_requires_every_row_id_in_manifest() -> None:
    pairs = pd.DataFrame({"left_row_id": [1], "right_row_id": [99]})
    assigned = pd.DataFrame({"row_id": [1, 2], "split": ["train", "test"]})
    with pytest.raises(ValueError, match="absent from manifest"):
        count_cross_split_audit_pairs(pairs, assigned)


def test_similarity_audit_accepts_known_row_ids() -> None:
    pairs = pd.DataFrame({"left_row_id": [1], "right_row_id": [2]})
    assigned = pd.DataFrame({"row_id": [1, 2], "split": ["train", "test"]})
    assert count_cross_split_audit_pairs(pairs, assigned) == 1
