"""Artifact and network-safety tests for URL inference."""
from pathlib import Path
import joblib,pytest,requests,socket
from scamlens.url_inference import URLArtifactError,load_url_artifact,predict_url

MODEL=Path(__file__).resolve().parents[1]/"artifacts/url/baseline_v1/url_pipeline.joblib"

def test_artifact_loading_deterministic_inference_and_scores():
    bundle=load_url_artifact(MODEL); first=predict_url(bundle,"https://example.com/login"); second=predict_url(bundle,"https://example.com/login")
    assert first==second
    assert first.label in {"benign","phish"}
    assert list(first.scores)==["benign","phish"]
    assert sum(first.scores.values())==pytest.approx(1.0)

def test_malformed_artifact_is_rejected(tmp_path):
    path=tmp_path/"bad.joblib"; joblib.dump({"pipeline":"bad"},path)
    with pytest.raises(URLArtifactError): load_url_artifact(path)

def test_inference_has_no_network_dependency(monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError("network access attempted")
    monkeypatch.setattr(socket,"create_connection",forbidden)
    monkeypatch.setattr(requests.sessions.Session,"request",forbidden)
    result=predict_url(load_url_artifact(MODEL),"https://example.com/login")
    assert result.label in {"benign","phish"}

def test_benign_prediction_can_disagree_with_observations():
    result=predict_url(load_url_artifact(MODEL),"https://example.com/login?item0=value&item1=value&item2=value&item3=value&item4=value&item5=value&item6=value&item7=value")
    assert result.label=="benign"

def test_phishing_prediction_can_have_no_observations():
    result=predict_url(load_url_artifact(MODEL),"https://example.com")
    assert result.label=="phish"
