"""Leakage-aware splitting utilities for the experimental SMS baseline."""

from __future__ import annotations

import hashlib
from itertools import combinations
from dataclasses import dataclass
import math

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neighbors import NearestNeighbors


@dataclass(frozen=True)
class SimilarityConfig:
    analyzer: str = "char_wb"
    ngram_min: int = 3
    ngram_max: int = 5
    lowercase: bool = True
    grouping_threshold: float = 0.90
    audit_threshold: float = 0.80

    def __post_init__(self) -> None:
        thresholds = (self.audit_threshold, self.grouping_threshold)
        if not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in thresholds
        ):
            raise ValueError("Similarity thresholds must be finite numbers")
        if not 0.0 <= self.audit_threshold <= self.grouping_threshold <= 1.0:
            raise ValueError(
                "Thresholds must satisfy 0 <= audit_threshold <= "
                "grouping_threshold <= 1"
            )


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[max(left_root, right_root)] = min(left_root, right_root)


def message_hash(message: str) -> str:
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def _similarity_pairs(
    matrix: object, threshold: float
) -> list[tuple[int, int, float]]:
    neighbors = NearestNeighbors(metric="cosine", algorithm="brute", n_jobs=-1)
    neighbors.fit(matrix)
    distances, indices = neighbors.radius_neighbors(
        matrix, radius=1.0 - threshold + 1e-12, return_distance=True, sort_results=True
    )
    pairs: list[tuple[int, int, float]] = []
    for left, (row_distances, row_indices) in enumerate(zip(distances, indices)):
        for distance, right in zip(row_distances, row_indices):
            right = int(right)
            if right > left:
                pairs.append((left, right, 1.0 - float(distance)))
    return pairs


def build_similarity_groups(
    frame: pd.DataFrame, config: SimilarityConfig
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    """Group exact and high-similarity texts without changing dataset rows."""
    unique = frame.drop_duplicates("message", keep="first").reset_index(drop=True)
    vectorizer = TfidfVectorizer(
        analyzer=config.analyzer,
        ngram_range=(config.ngram_min, config.ngram_max),
        lowercase=config.lowercase,
    )
    matrix = vectorizer.fit_transform(unique["message"])
    audit_pairs = _similarity_pairs(matrix, config.audit_threshold)

    union_find = UnionFind(len(unique))
    for left, right, similarity in audit_pairs:
        if similarity + 1e-12 >= config.grouping_threshold:
            union_find.union(left, right)

    component_members: dict[int, list[int]] = {}
    for index in range(len(unique)):
        component_members.setdefault(union_find.find(index), []).append(index)

    component_ids: dict[int, str] = {}
    for root, members in component_members.items():
        minimum_row_id = int(unique.iloc[members]["row_id"].min())
        component_ids[root] = f"similarity_{minimum_row_id:05d}"

    unique = unique.assign(
        exact_message_hash=unique["message"].map(message_hash),
        similarity_group=[component_ids[union_find.find(i)] for i in range(len(unique))],
    )
    mapping = unique.set_index("message")[["exact_message_hash", "similarity_group"]]
    enriched = frame.join(mapping, on="message", validate="many_to_one")

    pair_records = [
        {
            "left_row_id": int(unique.iloc[left]["row_id"]),
            "right_row_id": int(unique.iloc[right]["row_id"]),
            "left_label": str(unique.iloc[left]["label"]),
            "right_label": str(unique.iloc[right]["label"]),
            "cosine_similarity": round(similarity, 8),
            "grouped": similarity + 1e-12 >= config.grouping_threshold,
        }
        for left, right, similarity in audit_pairs
    ]
    return enriched, pair_records


def assign_splits(
    frame: pd.DataFrame, *, seed: int = 42, folds: int = 20
) -> pd.DataFrame:
    """Assign 14/3/3 CV folds while minimizing row and class-ratio drift."""
    if folds != 20:
        raise ValueError("The current 14/3/3 implementation requires folds=20")
    splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
    fold_assignment = np.full(len(frame), -1, dtype=int)
    for fold, (_, held_indices) in enumerate(
        splitter.split(frame, frame["label"], groups=frame["similarity_group"])
    ):
        fold_assignment[held_indices] = fold
    if (fold_assignment < 0).any():
        raise RuntimeError("At least one row was not assigned to a fold")

    labels = sorted(frame["label"].unique())
    fold_vectors: dict[int, np.ndarray] = {}
    for fold in range(folds):
        fold_frame = frame.iloc[np.flatnonzero(fold_assignment == fold)]
        fold_vectors[fold] = np.array(
            [len(fold_frame)]
            + [int((fold_frame["label"] == label).sum()) for label in labels],
            dtype=float,
        )
    total = sum(fold_vectors.values())
    target = total * 0.15

    def deviation(selected: tuple[int, ...]) -> float:
        observed = sum((fold_vectors[fold] for fold in selected), np.zeros_like(total))
        return float(np.square((observed - target) / np.maximum(target, 1.0)).sum())

    best: tuple[float, tuple[int, ...], tuple[int, ...]] | None = None
    all_folds = tuple(range(folds))
    for validation_folds in combinations(all_folds, 3):
        remaining = tuple(fold for fold in all_folds if fold not in validation_folds)
        validation_deviation = deviation(validation_folds)
        for test_folds in combinations(remaining, 3):
            candidate = (
                validation_deviation + deviation(test_folds),
                validation_folds,
                test_folds,
            )
            if best is None or candidate < best:
                best = candidate
    assert best is not None
    _, validation_folds, test_folds = best
    split = np.full(len(frame), "train", dtype=object)
    split[np.isin(fold_assignment, validation_folds)] = "validation"
    split[np.isin(fold_assignment, test_folds)] = "test"
    return frame.assign(split=split, fold=fold_assignment)


def assert_no_group_overlap(frame: pd.DataFrame) -> None:
    exact_overlap = frame.groupby("exact_message_hash")["split"].nunique().max()
    similarity_overlap = frame.groupby("similarity_group")["split"].nunique().max()
    if exact_overlap != 1:
        raise AssertionError("An exact-message group appears in multiple splits")
    if similarity_overlap != 1:
        raise AssertionError("A similarity group appears in multiple splits")
