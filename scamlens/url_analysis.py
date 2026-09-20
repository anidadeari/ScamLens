"""Purely local URL-string validation, normalization, and observations."""
from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from urllib.parse import SplitResult, urlsplit, urlunsplit

MAX_URL_CHARACTERS = 2_048
SUPPORTED_SCHEMES = {"http", "https"}

class URLInputError(ValueError):
    pass

@dataclass(frozen=True)
class ParsedURL:
    raw: str
    hostname: str
    port: int | None
    split: SplitResult

def parse_url(value: object, *, enforce_length: bool = True) -> ParsedURL:
    if not isinstance(value, str): raise URLInputError("URL must be text.")
    if not value: raise URLInputError("Enter a URL before running the analysis.")
    if value != value.strip(): raise URLInputError("Remove surrounding whitespace from the URL.")
    if enforce_length and len(value) > MAX_URL_CHARACTERS:
        raise URLInputError(f"URL is too long. The limit is {MAX_URL_CHARACTERS:,} characters. Nothing was truncated.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise URLInputError("URL contains unsupported control characters.")
    try:
        split = urlsplit(value)
        scheme = split.scheme.lower()
        hostname = split.hostname
        port = split.port
    except (ValueError, UnicodeError) as error:
        raise URLInputError("URL could not be parsed.") from error
    if scheme not in SUPPORTED_SCHEMES:
        raise URLInputError("URL must include an http:// or https:// scheme.")
    if not hostname:
        raise URLInputError("URL must include a hostname.")
    if any(char.isspace() for char in hostname):
        raise URLInputError("URL hostname contains whitespace.")
    try: hostname_ascii = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as error: raise URLInputError("URL hostname is not valid IDNA.") from error
    return ParsedURL(raw=value, hostname=hostname_ascii, port=port, split=split)

def normalize_for_audit(value: str) -> str:
    """Normalize identity for duplicate audits, never for classifier input."""
    parsed = parse_url(value.strip(), enforce_length=False)
    split = parsed.split
    userinfo = split.netloc.rsplit("@", 1)[0] + "@" if "@" in split.netloc else ""
    host = parsed.hostname
    if ":" in host and not host.startswith("["): host = f"[{host}]"
    default_port = (split.scheme.lower() == "http" and parsed.port == 80) or (split.scheme.lower() == "https" and parsed.port == 443)
    port = "" if parsed.port is None or default_port else f":{parsed.port}"
    return urlunsplit((split.scheme.lower(), f"{userinfo}{host}{port}", split.path, split.query, ""))

def url_properties(parsed: ParsedURL) -> dict[str, int | bool]:
    host = parsed.hostname
    try: ip_literal = bool(ipaddress.ip_address(host))
    except ValueError: ip_literal = False
    default_port = (parsed.split.scheme.lower() == "http" and parsed.port in (None, 80)) or (parsed.split.scheme.lower() == "https" and parsed.port in (None, 443))
    return {
        "url_length": len(parsed.raw), "hostname_length": len(host),
        "dots": host.count("."), "hyphens": parsed.raw.count("-"),
        "digits": sum(char.isdigit() for char in parsed.raw),
        "subdomain_labels": max(0, len(host.rstrip(".").split(".")) - 2) if not ip_literal else 0,
        "ip_literal": ip_literal, "non_default_port": parsed.port is not None and not default_port,
        "percent_encodings": parsed.raw.count("%"), "path_length": len(parsed.split.path),
        "query_length": len(parsed.split.query), "query_parameters": parsed.split.query.count("&") + bool(parsed.split.query),
        "userinfo": parsed.split.username is not None, "punycode": any(part.startswith("xn--") for part in host.split(".")),
        "has_query": bool(parsed.split.query),
    }

def observe_url(value: str) -> list[str]:
    props = url_properties(parse_url(value))
    observations = []
    if props["ip_literal"]: observations.append("Hostname is an IP literal")
    if props["url_length"] > 200: observations.append("URL is unusually long (over 200 characters)")
    if props["subdomain_labels"] >= 4: observations.append("Hostname has many subdomain labels (4 or more)")
    if props["non_default_port"]: observations.append("URL specifies a non-default port")
    if props["percent_encodings"] >= 4: observations.append("URL contains heavy percent encoding (4 or more percent signs)")
    if props["punycode"]: observations.append("Hostname contains punycode/IDN representation")
    if props["userinfo"]: observations.append("URL contains a userinfo (@) component")
    if props["digits"] >= 10: observations.append("URL contains many digits (10 or more)")
    if props["hyphens"] >= 6: observations.append("URL contains many hyphens (6 or more)")
    if props["query_parameters"] >= 8: observations.append("URL has a complex query (8 or more parameters)")
    return observations
