"""Integrity checks for prepared email data and its fixed split manifest."""

from __future__ import annotations

import pandas as pd

from scamlens.email_data import EXPECTED_EMAIL_LABELS


EXPECTED_SPLITS = {"train", "validation", "test"}
MODEL_DATA_COLUMNS = {
    "row_id", "label", "subject", "body", "model_text", "duplicate_group"
}
FORBIDDEN_FEATURE_COLUMNS = {
    "source", "uid", "id", "orig_lang", "published_split", "source_hash",
    "source_container", "duplicate_group", "fold", "split",
}


def validate_email_dataset_manifest(
    dataset: pd.DataFrame, manifest: pd.DataFrame
) -> pd.DataFrame:
    if set(dataset.columns) != MODEL_DATA_COLUMNS:
        raise ValueError(
            f"Prepared dataset columns must be exactly {sorted(MODEL_DATA_COLUMNS)}"
        )
    required_manifest = {
        "row_id", "uid", "label", "duplicate_group", "source_hash",
        "source_container", "published_split", "fold", "split",
    }
    if set(manifest.columns) != required_manifest:
        raise ValueError("Split manifest has an unexpected schema")
    for name, frame in (("dataset", dataset), ("manifest", manifest)):
        if frame["row_id"].isna().any() or not frame["row_id"].is_unique:
            raise ValueError(f"{name} row_id values must be present and unique")
        if frame["label"].isna().any() or set(frame["label"]) != EXPECTED_EMAIL_LABELS:
            raise ValueError(f"{name} labels must be exactly Valid, Spam, and Phishing")
    if set(dataset["row_id"]) != set(manifest["row_id"]):
        raise ValueError("Dataset and manifest row_id sets differ")
    data_labels = dataset.set_index("row_id")["label"].sort_index()
    manifest_labels = manifest.set_index("row_id")["label"].sort_index()
    if not data_labels.equals(manifest_labels):
        raise ValueError("Dataset and manifest labels differ by row_id")
    if set(manifest["split"]) != EXPECTED_SPLITS:
        raise ValueError("Manifest must contain exactly train, validation, and test")
    if manifest[["uid", "duplicate_group", "source_hash"]].isna().any().any():
        raise ValueError("Manifest linkage/group fields cannot be missing")
    if not manifest["uid"].is_unique:
        raise ValueError("Manifest uid values must be unique")
    for split in sorted(EXPECTED_SPLITS):
        if set(manifest.loc[manifest["split"] == split, "label"]) != EXPECTED_EMAIL_LABELS:
            raise ValueError(f"Split {split} must contain all three classes")
    if manifest.groupby("duplicate_group")["split"].nunique().max() != 1:
        raise ValueError("Duplicate groups cross split boundaries")
    expected_model_text = (
        "Subject: " + dataset["subject"] + "\n\nBody: " + dataset["body"]
    )
    if not dataset["model_text"].equals(expected_model_text):
        raise ValueError("model_text must be derived only from Subject and Body")
    merged = dataset.merge(
        manifest.drop(columns=["label", "duplicate_group"]),
        on="row_id",
        how="inner",
        validate="one_to_one",
    )
    if len(merged) != len(dataset):
        raise ValueError("Dataset/manifest merge changed row count")
    return merged


def validate_feature_columns(columns: list[str]) -> None:
    if columns != ["subject", "body"]:
        raise ValueError("Email model features must be exactly Subject and Body")
    forbidden = set(columns) & FORBIDDEN_FEATURE_COLUMNS
    if forbidden:
        raise ValueError(f"Forbidden metadata selected as features: {sorted(forbidden)}")

