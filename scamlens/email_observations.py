"""Deterministic, non-model textual observations for email decision support."""

from __future__ import annotations

import re


_INDICATOR_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "Urgency language",
        re.compile(
            r"\b(?:urgent(?:ly)?|immediately|act now|right away|time[- ]sensitive|"
            r"without delay|as soon as possible)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Account-verification language",
        re.compile(
            r"\b(?:verify|confirm|validate|update)\b.{0,50}\b(?:account|identity|"
            r"information|details|credentials|password)\b|"
            r"\b(?:account|identity|information|details|credentials|password)\b"
            r".{0,50}\b(?:verify|confirm|validate|update)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "Threat of account restriction or suspension",
        re.compile(
            r"\b(?:account|access|service)\b.{0,60}\b(?:suspend(?:ed|ing)?|"
            r"disable(?:d)?|restrict(?:ed)?|lock(?:ed)?|clos(?:e|ed)|terminat(?:e|ed))\b|"
            r"\b(?:suspend(?:ed|ing)?|disable(?:d)?|restrict(?:ed)?|lock(?:ed)?|"
            r"clos(?:e|ed)|terminat(?:e|ed))\b.{0,60}\b(?:account|access|service)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "Request to click or follow a link",
        re.compile(
            r"\b(?:click|follow|open|visit|use|tap)\b.{0,35}\b(?:link|button|url)\b|"
            r"\b(?:link|button|url)\b.{0,35}\b(?:below|provided|attached)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
)


def observe_email_text(subject: str, body: str) -> list[str]:
    """Return explainable textual matches without assigning risk or a class."""
    text = f"{subject}\n{body}"
    return [label for label, pattern in _INDICATOR_PATTERNS if pattern.search(text)]
