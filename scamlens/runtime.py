"""Runtime integrity and output-safety helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_output_permission(paths: Iterable[Path], *, overwrite: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not overwrite:
        rendered = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            f"Refusing to overwrite existing outputs: {rendered}. "
            "Pass --overwrite only after confirming replacement is intended."
        )


def verify_file_hashes(expected_hashes: dict[Path, str]) -> None:
    for path, expected in expected_hashes.items():
        if not path.is_file():
            raise FileNotFoundError(f"Required integrity-checked file is missing: {path}")
        actual = sha256(path)
        if actual != expected:
            raise ValueError(
                f"Hash mismatch for {path}: expected {expected}, found {actual}"
            )


def source_version_identifier(project_root: Path) -> str:
    """Hash source and dependency declarations when a Git revision is unavailable."""
    candidates = sorted((project_root / "scamlens").glob("*.py"))
    candidates += sorted((project_root / "scripts").glob("*.py"))
    candidates.append(project_root / "requirements.txt")
    digest = hashlib.sha256()
    for path in candidates:
        if path.is_file():
            digest.update(str(path.relative_to(project_root)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return f"source-sha256:{digest.hexdigest()}"
