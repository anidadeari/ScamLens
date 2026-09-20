import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from scamlens.api.schemas import ExperimentMetrics, PerformanceResponse

router = APIRouter()
ROOT = Path(__file__).resolve().parents[3]


def _read(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("Stored evaluation results are unavailable.") from error
    if not isinstance(value, dict):
        raise RuntimeError("Stored evaluation results have an invalid structure.")
    return value


@router.get("/performance", response_model=PerformanceResponse)
async def performance() -> PerformanceResponse:
    try:
        message_report = _read(ROOT / "artifacts/message/test_metrics.json")
        email_report = _read(ROOT / "artifacts/email/baseline_v1/metrics.json")
        url_report = _read(ROOT / "artifacts/url/baseline_v1/metrics.json")
        message = message_report["selected_pipeline"]["all_rows"]
        email = email_report["logistic_regression"]["test"]
        url = url_report["official_temporal_test"]
        return PerformanceResponse(
            message=ExperimentMetrics(
                experiment="experimental English SMS spam/ham baseline",
                evaluation_scope="held_out_sms_test_split",
                accuracy=message["accuracy"], macro_f1=message["macro_f1"],
                target_recall_label="spam", target_recall=message["per_class"]["spam"]["recall"],
                limitations=["Does not establish performance on phishing, email, fraud, or modern messages."],
            ),
            email=ExperimentMetrics(
                experiment="exploratory three-class email classification",
                evaluation_scope="within_corpus_only",
                accuracy=email["accuracy"], macro_f1=email["macro_f1"],
                target_recall_label="Phishing", target_recall=email["per_class"]["Phishing"]["recall"],
                limitations=["Real-world generalization is not established."],
            ),
            url=ExperimentMetrics(
                experiment="experimental URL-string-only phishing/benign classification",
                evaluation_scope="filtered_official_temporal_test",
                accuracy=url["accuracy"], macro_f1=url["macro_f1"],
                target_recall_label="phish", target_recall=url["per_class"]["phish"]["recall"],
                limitations=["Domain overlap, collection-time confounding, and label noise limit generalization claims."],
            ),
        )
    except (RuntimeError, KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=503, detail="Stored performance results are unavailable.") from error
