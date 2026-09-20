"""Safe preparation helpers for the Mendeley three-class email experiment."""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import re
import unicodedata


EXPECTED_EMAIL_LABELS = frozenset({"Valid", "Spam", "Phishing"})

_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>\"']+")
_IP_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d .()\-/]{6,}\d)(?!\w)")
_LONG_ID_RE = re.compile(r"(?<!\w)\d{8,}(?!\w)")
_GREETING_NAME_RE = re.compile(
    r"(?im)^(\s*(?:dear|hello|hi|attention|attn)\s+)([^,\n:]{1,80})([, :])"
)
_HTML_HINT_RE = re.compile(r"(?i)<\s*/?\s*(?:html|body|div|p|a|table|br)\b")


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style"}:
            self.hidden_depth += 1
        elif tag.lower() in {"br", "p", "div", "tr", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self.hidden_depth:
            self.hidden_depth -= 1
        elif tag.lower() in {"p", "div", "tr", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)


def visible_text(value: str) -> tuple[str, bool]:
    """Extract visible text from HTML-like bodies without following any resources."""
    if not _HTML_HINT_RE.search(value):
        return value, False
    parser = _VisibleTextParser()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts), True


def redact_text(value: str | None) -> tuple[str, dict[str, int]]:
    """Apply the same deterministic identifier redaction rules to every class."""
    text = "" if value is None else str(value)
    text, parsed_html = visible_text(text)
    counts: dict[str, int] = {"html_documents": int(parsed_html)}
    rules = (
        ("email_addresses", _EMAIL_RE, "[EMAIL]"),
        ("urls", _URL_RE, "[URL]"),
        ("ip_addresses", _IP_RE, "[IP_ADDRESS]"),
        ("long_numeric_identifiers", _LONG_ID_RE, "[NUMERIC_ID]"),
    )
    for name, pattern, replacement in rules:
        text, counts[name] = pattern.subn(replacement, text)

    phone_count = 0

    def replace_phone(match: re.Match[str]) -> str:
        nonlocal phone_count
        candidate = match.group(0)
        digits = sum(character.isdigit() for character in candidate)
        # Avoid treating ordinary dates as phones. International prefixes can be
        # shorter, while unprefixed candidates must contain at least ten digits.
        if digits >= 10 or (candidate.lstrip().startswith("+") and digits >= 8):
            phone_count += 1
            return "[PHONE]"
        return candidate

    text = _PHONE_RE.sub(replace_phone, text)
    counts["phone_numbers"] = phone_count

    def replace_greeting(match: re.Match[str]) -> str:
        return f"{match.group(1)}[NAME]{match.group(3)}"

    text, counts["greeting_names"] = _GREETING_NAME_RE.subn(replace_greeting, text)
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text, counts


def canonical_text(subject: str, body: str) -> str:
    combined = f"{subject}\n{body}"
    normalized = unicodedata.normalize("NFKC", combined).casefold()
    return " ".join(re.findall(r"\w+", normalized, flags=re.UNICODE))


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_raw_records(records: list[dict[str, object]]) -> None:
    if not records:
        raise ValueError("Email dataset is empty")
    labels = {record.get("label") for record in records}
    if labels != EXPECTED_EMAIL_LABELS:
        raise ValueError(
            f"Expected labels {sorted(EXPECTED_EMAIL_LABELS)}, found {sorted(map(str, labels))}"
        )
    for field in ("id", "uid", "source"):
        values = [record.get(field) for record in records]
        if any(value is None or not str(value).strip() for value in values):
            raise ValueError(f"Field {field} contains missing/empty values")
        if field in {"id", "uid"} and len(set(values)) != len(values):
            raise ValueError(f"Field {field} must be unique")
