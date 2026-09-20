"""Tests for output protection and file integrity checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from scamlens.runtime import require_output_permission, sha256, verify_file_hashes


def test_existing_output_requires_explicit_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    output.write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        require_output_permission([output], overwrite=False)
    require_output_permission([output], overwrite=True)


def test_hash_verification_accepts_match_and_rejects_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_text("stable", encoding="utf-8")
    verify_file_hashes({source: sha256(source)})
    with pytest.raises(ValueError, match="Hash mismatch"):
        verify_file_hashes({source: "0" * 64})
