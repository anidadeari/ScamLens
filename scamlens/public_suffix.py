"""Minimal offline Public Suffix List matching for audit grouping."""
from __future__ import annotations
from pathlib import Path

def load_rules(path: Path) -> tuple[set[str], set[str], set[str]]:
    exact, wildcard, exception = set(), set(), set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        rule = raw.strip().lower()
        if not rule or rule.startswith("//"): continue
        if rule.startswith("!"): exception.add(rule[1:])
        elif rule.startswith("*."): wildcard.add(rule[2:])
        else: exact.add(rule)
    return exact, wildcard, exception

def registered_domain(hostname: str, rules: tuple[set[str], set[str], set[str]]) -> str:
    labels = hostname.lower().rstrip(".").split(".")
    if len(labels) < 2: return hostname.lower().rstrip(".")
    exact, wildcard, exception = rules
    suffix_length = 1
    for index in range(len(labels)):
        candidate = ".".join(labels[index:])
        if candidate in exception:
            suffix_length = len(labels) - index - 1
            break
        if candidate in exact: suffix_length = max(suffix_length, len(labels) - index)
        if index + 1 < len(labels) and ".".join(labels[index + 1:]) in wildcard:
            suffix_length = max(suffix_length, len(labels) - index)
    return ".".join(labels[-min(len(labels), suffix_length + 1):])
