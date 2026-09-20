"""Contract, parity, privacy, and safety tests for the local FastAPI layer."""
from __future__ import annotations

import asyncio
from io import BytesIO
import socket
import urllib.request

import httpx
from PIL import Image
import requests

from scamlens.api.app import LOCAL_FRONTEND_ORIGINS, app
from scamlens.api.dependencies import email_model, message_model, url_model
from scamlens.email_inference import MAX_EMAIL_CHARACTERS, predict_email
from scamlens.email_observations import observe_email_text
from scamlens.message_inference import MAX_MESSAGE_CHARACTERS, predict_message
from scamlens.screenshot_analysis import MAX_UPLOAD_BYTES
from scamlens.url_analysis import MAX_URL_CHARACTERS, observe_url
from scamlens.url_inference import predict_url

class ASGITestClient:
    """Small synchronous facade over HTTPX's socket-free ASGI transport."""

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        async def send() -> httpx.Response:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as session:
                return await session.request(method, path, **kwargs)

        return asyncio.run(send())

    def get(self, path: str, **kwargs) -> httpx.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        return self.request("POST", path, **kwargs)


client = ASGITestClient()


def _png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (80, 30), "white").save(output, format="PNG")
    return output.getvalue()


def test_health_contract_is_small_and_deterministic() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "scamlens-local-api"}


def test_message_result_matches_existing_inference() -> None:
    text = "You have won a prize. Reply now to claim."
    expected = predict_message(message_model(), text)
    response = client.post("/api/analyze/message", json={"text": text})
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_type"] == "message"
    assert data["prediction"] == expected.label
    assert data["scores"] == {"spam": expected.spam_score, "threshold": expected.threshold}
    assert "probability" not in str(data).lower()


def test_message_rejects_empty_wrong_type_extra_and_oversized_input() -> None:
    for payload in (
        {"text": "   "}, {"text": 123}, {"text": "ok", "extra": True},
        {"text": "x" * (MAX_MESSAGE_CHARACTERS + 1)},
    ):
        response = client.post("/api/analyze/message", json=payload)
        assert response.status_code == 422
        assert "traceback" not in response.text.lower()


def test_email_result_and_observations_match_existing_behavior() -> None:
    subject = "Urgent: Verify your account immediately"
    body = "Your account will be suspended unless you verify it. Click the link below."
    expected = predict_email(email_model(), subject=subject, body=body)
    expected_observations = observe_email_text(subject, body)
    response = client.post("/api/analyze/email", json={"subject": subject, "body": body})
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] == expected.label
    assert data["classifier_outputs"] == expected.scores
    assert data["observed_indicators"] == expected_observations
    assert data["evaluation_scope"] == "within_corpus_only"
    assert data["generalization_status"] == "not_established"
    assert data["disagreement"] == (expected.label == "Valid" and bool(expected_observations))
    if data["disagreement"]:
        assert "predicted Valid" in data["disagreement_message"]
        assert data["prediction"] == "Valid"


def test_email_rejects_empty_and_combined_oversized_input() -> None:
    assert client.post("/api/analyze/email", json={"subject": " ", "body": ""}).status_code == 422
    response = client.post(
        "/api/analyze/email", json={"subject": "x", "body": "y" * MAX_EMAIL_CHARACTERS}
    )
    assert response.status_code == 422


def test_url_result_matches_existing_inference_without_network(monkeypatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    value = "https://127.0.0.1:8443/login?one=1&two=2"
    expected = predict_url(url_model(), value)
    response = client.post("/api/analyze/url", json={"url": value})
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] == expected.label
    assert data["classifier_outputs"] == expected.scores
    assert data["observed_indicators"] == observe_url(value)
    assert any("never visits" in item for item in data["limitations"])
    assert any("HTTPS is not evidence" in item for item in data["limitations"])


def test_url_rejects_malformed_and_oversized_values() -> None:
    for value in ("example.com", "https://", " https://example.com", "x" * (MAX_URL_CHARACTERS + 1)):
        response = client.post("/api/analyze/url", json={"url": value})
        assert response.status_code == 422
        assert "traceback" not in response.text.lower()


def test_ocr_valid_upload_returns_review_text_without_classification(monkeypatch) -> None:
    from scamlens.api.routes import screenshot as route

    async def extracted(_image, _timeout):
        return "Review this extracted text"
    monkeypatch.setattr(route, "_extract_without_blocking", extracted)
    response = client.post("/api/ocr", files={"file": ("shot.png", _png_bytes(), "image/png")})
    assert response.status_code == 200
    assert response.json() == {
        "analysis_type": "ocr",
        "extracted_text": "Review this extracted text",
        "usable_text": True,
        "classification_performed": False,
        "review_required": True,
        "limitations": response.json()["limitations"],
    }
    assert "prediction" not in response.json()
    assert "scores" not in response.json()


def test_ocr_empty_output_is_review_only_and_unusable(monkeypatch) -> None:
    from scamlens.api.routes import screenshot as route

    async def extracted(_image, _timeout):
        return "   "
    monkeypatch.setattr(route, "_extract_without_blocking", extracted)
    response = client.post("/api/ocr", files={"file": ("shot.png", _png_bytes(), "image/png")})
    assert response.status_code == 200
    assert response.json()["usable_text"] is False
    assert response.json()["classification_performed"] is False


def test_ocr_rejects_corrupt_mismatched_and_oversized_uploads(monkeypatch) -> None:
    from starlette.formparsers import MultiPartParser

    # Keep the bounded fixture in memory; this workspace's temporary-file worker
    # bridge is not part of the application behavior under test.
    monkeypatch.setattr(MultiPartParser, "spool_max_size", MAX_UPLOAD_BYTES + 2)
    cases = [
        ("bad.png", b"not an image", "image/png"),
        ("shot.jpg", _png_bytes(), "image/jpeg"),
        ("huge.png", b"x" * (MAX_UPLOAD_BYTES + 1), "image/png"),
    ]
    for filename, data, mime in cases:
        response = client.post("/api/ocr", files={"file": (filename, data, mime)})
        assert response.status_code == 422
        assert "traceback" not in response.text.lower()


def test_performance_returns_separate_stored_experiments() -> None:
    response = client.get("/api/performance")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "stored_artifacts"
    assert data["experiments_are_directly_comparable"] is False
    assert set(data) == {"source", "experiments_are_directly_comparable", "message", "email", "url"}
    assert data["email"]["evaluation_scope"] == "within_corpus_only"


def test_openapi_has_explicit_response_schemas_and_local_cors_only() -> None:
    schema = client.get("/openapi.json").json()
    for path in (
        "/api/health", "/api/analyze/message", "/api/analyze/email",
        "/api/analyze/url", "/api/ocr", "/api/performance",
    ):
        assert path in schema["paths"]
    assert set(LOCAL_FRONTEND_ORIGINS) == {
        "http://localhost:3000", "http://127.0.0.1:3000"
    }
    assert "*" not in LOCAL_FRONTEND_ORIGINS


def test_invalid_json_error_is_sanitized() -> None:
    response = client.post(
        "/api/analyze/message", content=b'{"text":', headers={"content-type": "application/json"}
    )
    assert response.status_code == 422
    assert "traceback" not in response.text.lower()
    assert '"input"' not in response.text
