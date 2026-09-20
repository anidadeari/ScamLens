"""Audit projected PhreshPhish URL metadata without contacting any URL."""
from __future__ import annotations

import argparse, hashlib, json, sys
from pathlib import Path
from collections import Counter
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scamlens.public_suffix import load_rules, registered_domain
from scamlens.runtime import sha256
from scamlens.url_analysis import URLInputError, normalize_for_audit, parse_url
from scamlens.url_analysis import MAX_URL_CHARACTERS

def digest(value: str) -> str: return hashlib.sha256(value.encode()).hexdigest()
def counts(series: pd.Series) -> dict[str, int]: return {str(k): int(v) for k, v in series.value_counts().items()}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-data", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--psl", type=Path, default=Path("/usr/share/publicsuffix/effective_tld_names.dat"))
    args = parser.parse_args()
    data = pd.read_parquet(args.input)
    rules = load_rules(args.psl)
    normalized, hostnames, domains, parse_errors = [], [], [], Counter()
    for value in data.url:
        try:
            parsed = parse_url(value, enforce_length=False)
            normal = normalize_for_audit(value)
            host, domain = parsed.hostname, registered_domain(parsed.hostname, rules)
        except URLInputError as error:
            normal = host = domain = ""
            parse_errors[str(error)] += 1
        normalized.append(normal); hostnames.append(host); domains.append(domain)
    data["normalized_url"] = normalized
    data["hostname"] = hostnames
    data["registered_domain"] = domains
    valid = data.hostname.ne("")
    train, test = data.official_split.eq("train"), data.official_split.eq("test")
    exact_train, normalized_train = set(data.loc[train, "url"]), set(data.loc[train & valid, "normalized_url"])
    host_train, domain_train = set(data.loc[train & valid, "hostname"]), set(data.loc[train & valid, "registered_domain"])
    normalized_conflicts = int(data.loc[valid].groupby("normalized_url").label.nunique().gt(1).sum())
    time_counts = data.assign(month=data.date.astype(str).str[:7]).groupby(["official_split", "month", "label"]).size()
    shard_counts = data.groupby(["official_split", "source_shard", "label"]).size()
    report = {
        "input_sha256": sha256(args.input), "psl_sha256": sha256(args.psl),
        "rows": int(len(data)), "split_counts": counts(data.official_split),
        "labels": counts(data.label),
        "class_by_split": {split: counts(group.label) for split, group in data.groupby("official_split")},
        "missing": {column: int(data[column].isna().sum()) for column in ["url", "label", "date"]},
        "invalid_or_unparseable": int((~valid).sum()), "parse_error_types": dict(parse_errors),
        "over_runtime_length_limit": int(data.url.str.len().gt(MAX_URL_CHARACTERS).sum()),
        "exact_duplicate_rows": int(data.url.duplicated(keep=False).sum()),
        "exact_duplicate_values": int(data.url.duplicated().sum()),
        "exact_conflicting_label_urls": int(data.groupby("url").label.nunique().gt(1).sum()),
        "normalized_duplicate_rows": int(data.loc[valid, "normalized_url"].duplicated(keep=False).sum()),
        "normalized_duplicate_values": int(data.loc[valid, "normalized_url"].duplicated().sum()),
        "normalized_conflicting_label_urls": normalized_conflicts,
        "unique_hostnames": int(data.loc[valid, "hostname"].nunique()),
        "unique_registered_domains": int(data.loc[valid, "registered_domain"].nunique()),
        "test_overlap": {
            "exact_url_rows": int(data.loc[test, "url"].isin(exact_train).sum()),
            "normalized_url_rows": int(data.loc[test & valid, "normalized_url"].isin(normalized_train).sum()),
            "hostname_rows": int(data.loc[test & valid, "hostname"].isin(host_train).sum()),
            "registered_domain_rows": int(data.loc[test & valid, "registered_domain"].isin(domain_train).sum()),
            "unique_hostnames": int(len(set(data.loc[test & valid, "hostname"]) & host_train)),
            "unique_registered_domains": int(len(set(data.loc[test & valid, "registered_domain"]) & domain_train)),
        },
        "date_ranges": {split: {"min": str(group.date.min()), "max": str(group.date.max())} for split, group in data.groupby("official_split")},
        "class_by_month": {"|".join(index): int(value) for index, value in time_counts.items()},
        "class_by_source_shard": {"|".join(index): int(value) for index, value in shard_counts.items()},
        "label_leakage_audit": {
            "url_contains_literal_benign": int(data.url.str.contains("benign", case=False, regex=False).sum()),
            "url_contains_literal_phish": int(data.url.str.contains("phish", case=False, regex=False).sum()),
            "note": "Literal occurrence is only a screen; semantic annotation leakage is not confirmed.",
        },
    }
    output = data[["official_split", "source_shard", "sha256", "url", "label", "date", "normalized_url", "hostname", "registered_domain"]]
    args.output_data.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output_data, index=False)
    report["output_data_sha256"] = sha256(args.output_data)
    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["rows", "split_counts", "labels", "invalid_or_unparseable", "exact_duplicate_values", "normalized_duplicate_values", "test_overlap", "date_ranges"]}, indent=2))

if __name__ == "__main__": main()
