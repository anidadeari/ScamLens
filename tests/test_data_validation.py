"""Tests for strict dataset/manifest pre-merge validation."""

from __future__ import annotations

import pandas as pd
import pytest

from scamlens.data_validation import validate_and_merge_dataset_manifest


def valid_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    dataset = pd.DataFrame(
        {
            "row_id": [1, 2, 3, 4, 5, 6],
            "label": ["ham", "spam", "ham", "spam", "ham", "spam"],
            "message": [f"message {index}" for index in range(1, 7)],
        }
    )
    manifest = pd.DataFrame(
        {
            "row_id": [1, 2, 3, 4, 5, 6],
            "label": ["ham", "spam", "ham", "spam", "ham", "spam"],
            "exact_message_hash": [f"hash-{index}" for index in range(1, 7)],
            "similarity_group": [f"group-{index}" for index in range(1, 7)],
            "split": ["train", "train", "validation", "validation", "test", "test"],
        }
    )
    return dataset, manifest


def test_valid_dataset_and_manifest_are_merged_without_row_changes() -> None:
    dataset, manifest = valid_inputs()
    merged = validate_and_merge_dataset_manifest(dataset, manifest)
    assert len(merged) == len(dataset) == len(manifest)
    assert set(merged["row_id"]) == set(dataset["row_id"])


@pytest.mark.parametrize("target", ["dataset", "manifest"])
def test_duplicate_row_ids_are_rejected(target: str) -> None:
    dataset, manifest = valid_inputs()
    frame = dataset if target == "dataset" else manifest
    frame.loc[1, "row_id"] = frame.loc[0, "row_id"]
    with pytest.raises(ValueError, match="duplicate row_id"):
        validate_and_merge_dataset_manifest(dataset, manifest)


@pytest.mark.parametrize("target", ["dataset", "manifest"])
def test_missing_row_ids_are_rejected(target: str) -> None:
    dataset, manifest = valid_inputs()
    frame = dataset if target == "dataset" else manifest
    frame.loc[0, "row_id"] = None
    with pytest.raises(ValueError, match="missing row_id"):
        validate_and_merge_dataset_manifest(dataset, manifest)


def test_different_row_id_sets_are_rejected() -> None:
    dataset, manifest = valid_inputs()
    manifest.loc[5, "row_id"] = 99
    with pytest.raises(ValueError, match="row_id sets differ"):
        validate_and_merge_dataset_manifest(dataset, manifest)


def test_label_mismatch_is_rejected_before_merge() -> None:
    dataset, manifest = valid_inputs()
    manifest.loc[0, "label"] = "spam"
    with pytest.raises(ValueError, match="labels do not match"):
        validate_and_merge_dataset_manifest(dataset, manifest)


def test_invalid_label_is_rejected() -> None:
    dataset, manifest = valid_inputs()
    dataset.loc[0, "label"] = "unknown"
    with pytest.raises(ValueError, match="invalid labels"):
        validate_and_merge_dataset_manifest(dataset, manifest)


@pytest.mark.parametrize("bad_message", ["", "   ", 123, None])
def test_invalid_message_is_rejected(bad_message: object) -> None:
    dataset, manifest = valid_inputs()
    dataset.loc[0, "message"] = bad_message
    with pytest.raises(ValueError, match="non-empty strings"):
        validate_and_merge_dataset_manifest(dataset, manifest)


def test_invalid_or_incomplete_splits_are_rejected() -> None:
    dataset, manifest = valid_inputs()
    manifest.loc[manifest["split"] == "test", "split"] = "holdout"
    with pytest.raises(ValueError, match="splits must be exactly"):
        validate_and_merge_dataset_manifest(dataset, manifest)

    dataset, manifest = valid_inputs()
    manifest.loc[manifest["split"] == "test", "label"] = "ham"
    dataset.loc[dataset["row_id"] == 6, "label"] = "ham"
    with pytest.raises(ValueError, match="must be non-empty and contain ham and spam"):
        validate_and_merge_dataset_manifest(dataset, manifest)


def test_missing_group_value_is_rejected() -> None:
    dataset, manifest = valid_inputs()
    manifest.loc[0, "similarity_group"] = None
    with pytest.raises(ValueError, match="missing/empty"):
        validate_and_merge_dataset_manifest(dataset, manifest)
