"""Trusted local artifact dependencies shared by API routes."""
from functools import lru_cache
from pathlib import Path

from scamlens.email_inference import load_email_artifact
from scamlens.message_inference import load_trusted_artifact
from scamlens.url_inference import load_url_artifact

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def message_model() -> dict[str, object]:
    return load_trusted_artifact(ROOT / "artifacts/message/sms_spam_ham_pipeline.joblib")


@lru_cache(maxsize=1)
def email_model() -> dict[str, object]:
    return load_email_artifact(ROOT / "artifacts/email/baseline_v1/email_pipeline.joblib")


@lru_cache(maxsize=1)
def url_model() -> dict[str, object]:
    return load_url_artifact(ROOT / "artifacts/url/baseline_v1/url_pipeline.joblib")

