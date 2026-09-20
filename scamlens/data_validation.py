"""Strict data and manifest validation for the SMS baseline."""

from __future__ import annotations

import pandas as pd


EXPECTED_LABELS = {"ham", "spam"}
EXPECTED_SPLITS = {"train", "validation", "test"}
GROUP_COLUMNS = {"exact_message_hash", "similarity_group"}


def _validate_row_ids(frame: pd.DataFrame, name: str) -> None:
    if "row_id" not in frame.columns:
        raise ValueError(f"{name} is missing the row_id column")
    if frame["row_id"].isna().any():
        raise ValueError(f"{name} contains missing row_id values")
    if not frame["row_id"].is_unique:
        raise ValueError(f"{name} contains duplicate row_id values")


def _validate_labels(frame: pd.DataFrame, name: str) -> None:
    if "label" not in frame.columns:
        raise ValueError(f"{name} is missing the label column")
    if frame["label"].isna().any():
        raise ValueError(f"{name} contains missing labels")
    unexpected = set(frame["label"].unique()) - EXPECTED_LABELS
    if unexpected:
        raise ValueError(f"{name} contains invalid labels: {sorted(unexpected)}")


def validate_and_merge_dataset_manifest(
    dataset: pd.DataFrame, manifest: pd.DataFrame
) -> pd.DataFrame:
    """Validate both inputs completely before performing a one-to-one merge."""
    _validate_row_ids(dataset, "dataset")
    _validate_row_ids(manifest, "manifest")
    _validate_labels(dataset, "dataset")
    _validate_labels(manifest, "manifest")

    if "message" not in dataset.columns:
        raise ValueError("dataset is missing the message column")
    invalid_text = ~dataset["message"].map(
        lambda value: isinstance(value, str) and bool(value.strip())
    )
    if invalid_text.any():
        raise ValueError("dataset messages must be non-empty strings")

    dataset_ids = set(dataset["row_id"])
    manifest_ids = set(manifest["row_id"])
    if dataset_ids != manifest_ids:
        missing_from_manifest = len(dataset_ids - manifest_ids)
        missing_from_dataset = len(manifest_ids - dataset_ids)
        raise ValueError(
            "dataset and manifest row_id sets differ: "
            f"{missing_from_manifest} missing from manifest, "
            f"{missing_from_dataset} missing from dataset"
        )

    dataset_labels = dataset.set_index("row_id")["label"].sort_index()
    manifest_labels = manifest.set_index("row_id")["label"].sort_index()
    if not dataset_labels.equals(manifest_labels):
        raise ValueError("dataset and manifest labels do not match by row_id")

    if "split" not in manifest.columns:
        raise ValueError("manifest is missing the split column")
    if manifest["split"].isna().any():
        raise ValueError("manifest contains missing split values")
    actual_splits = set(manifest["split"].unique())
    if actual_splits != EXPECTED_SPLITS:
        raise ValueError(
            f"manifest splits must be exactly {sorted(EXPECTED_SPLITS)}, "
            f"found {sorted(actual_splits)}"
        )

    missing_group_columns = GROUP_COLUMNS - set(manifest.columns)
    if missing_group_columns:
        raise ValueError(
            f"manifest is missing group columns: {sorted(missing_group_columns)}"
        )
    for column in sorted(GROUP_COLUMNS):
        invalid_group = manifest[column].isna() | ~manifest[column].map(
            lambda value: isinstance(value, str) and bool(value.strip())
        )
        if invalid_group.any():
            raise ValueError(f"manifest column {column} contains missing/empty values")

    for split in sorted(EXPECTED_SPLITS):
        split_labels = set(manifest.loc[manifest["split"] == split, "label"])
        if split_labels != EXPECTED_LABELS:
            raise ValueError(
                f"split {split} must be non-empty and contain ham and spam; "
                f"found {sorted(split_labels)}"
            )

    merged = dataset.merge(
        manifest.drop(columns="label"), on="row_id", how="inner", validate="one_to_one"
    )
    if len(merged) != len(dataset) or len(merged) != len(manifest):
        raise ValueError("merge changed the number of rows")
    if set(merged["row_id"]) != dataset_ids:
        raise ValueError("merge changed the row_id set")
    return merged
