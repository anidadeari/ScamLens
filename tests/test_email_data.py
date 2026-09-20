"""Focused tests for safe Mendeley email preparation helpers."""

from __future__ import annotations

import pytest

from scamlens.email_data import canonical_text, redact_text, validate_raw_records


def valid_records() -> list[dict[str, object]]:
    return [
        {"id": 1, "uid": "u1", "source": "a", "label": "Valid"},
        {"id": 2, "uid": "u2", "source": "b", "label": "Spam"},
        {"id": 3, "uid": "u3", "source": "c", "label": "Phishing"},
    ]


def test_redaction_removes_supported_identifiers_without_following_html_links() -> None:
    text = (
        '<html><script>hidden@example.com</script><body>Dear Alice, '
        '<a href="https://hidden.example">visit https://shown.example/x</a> '
        'or mail person@example.com and call +1 (202) 555-0199.</body></html>'
    )
    redacted, counts = redact_text(text)
    assert "hidden.example" not in redacted
    assert "shown.example" not in redacted
    assert "person@example.com" not in redacted
    assert "Alice" not in redacted
    assert "[URL]" in redacted
    assert "[EMAIL]" in redacted
    assert "[PHONE]" in redacted
    assert counts["html_documents"] == 1


def test_redaction_is_deterministic_and_class_independent() -> None:
    first = redact_text("Hello Bob, use bob@example.org")
    second = redact_text("Hello Bob, use bob@example.org")
    assert first == second


def test_redaction_does_not_treat_an_ordinary_date_as_a_phone_number() -> None:
    redacted, counts = redact_text("Conference dates: 23-24, 2024")
    assert "23-24, 2024" in redacted
    assert counts["phone_numbers"] == 0


def test_canonical_grouping_ignores_case_punctuation_and_whitespace() -> None:
    assert canonical_text("Hello!", "A  test.") == canonical_text(
        " hello ", "a test"
    )


def test_valid_records_are_accepted() -> None:
    validate_raw_records(valid_records())


@pytest.mark.parametrize("field", ["id", "uid"])
def test_duplicate_identifiers_are_rejected(field: str) -> None:
    records = valid_records()
    records[1][field] = records[0][field]
    with pytest.raises(ValueError, match="must be unique"):
        validate_raw_records(records)


def test_invalid_label_set_is_rejected() -> None:
    records = valid_records()
    records[0]["label"] = "Ham"
    with pytest.raises(ValueError, match="Expected labels"):
        validate_raw_records(records)
