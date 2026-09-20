"""Validated, network-free inference for the URL-string baseline."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import warnings, joblib
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.pipeline import Pipeline
from scamlens.url_analysis import ParsedURL, parse_url
from scamlens.url_model import URL_LABELS

URL_TASK="experimental URL-string-only phishing/benign classification"
class URLArtifactError(RuntimeError): pass
@dataclass(frozen=True)
class URLPrediction:
    label:str
    scores:dict[str,float]
    parsed:ParsedURL

def load_url_artifact(path:Path)->dict[str,object]:
    if not path.is_file(): raise URLArtifactError("The trusted local URL artifact is missing.")
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always",InconsistentVersionWarning); bundle=joblib.load(path)
    except Exception as error: raise URLArtifactError("The URL artifact could not be loaded.") from error
    if any(issubclass(w.category,InconsistentVersionWarning) for w in caught): raise URLArtifactError("The URL artifact uses an incompatible sklearn version.")
    required={"pipeline","labels","task","feature_scope","evaluation_scope"}
    if not isinstance(bundle,dict) or not required.issubset(bundle): raise URLArtifactError("The URL artifact has an invalid structure.")
    if not isinstance(bundle["pipeline"],Pipeline) or bundle["labels"]!=URL_LABELS or bundle["task"]!=URL_TASK or bundle["feature_scope"]!="raw_url_string_only": raise URLArtifactError("The URL artifact metadata is incompatible.")
    classifier=bundle["pipeline"].named_steps.get("classifier")
    if classifier is None or list(classifier.classes_)!=URL_LABELS: raise URLArtifactError("The URL artifact has incompatible classes.")
    return bundle

def predict_url(bundle:dict[str,object],value:object)->URLPrediction:
    parsed=parse_url(value)
    try:
        pipeline=bundle["pipeline"]; probabilities=pipeline.predict_proba([parsed.raw])[0]
        scores={str(label):float(score) for label,score in zip(pipeline.named_steps["classifier"].classes_,probabilities)}
        label=str(pipeline.predict([parsed.raw])[0])
    except Exception as error: raise URLArtifactError("The URL artifact is incompatible with inference.") from error
    if label not in URL_LABELS or set(scores)!=set(URL_LABELS): raise URLArtifactError("The URL prediction has an invalid class schema.")
    return URLPrediction(label,{key:scores[key] for key in URL_LABELS},parsed)
