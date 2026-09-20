"""Local Streamlit UI for ScamLens' established experimental baselines."""
from __future__ import annotations

import json
from pathlib import Path
import streamlit as st

from scamlens.email_inference import (MAX_EMAIL_CHARACTERS, EmailArtifactError,
    EmailInputError, load_email_artifact, predict_email)
from scamlens.email_observations import observe_email_text
from scamlens.message_inference import (ArtifactLoadError, MAX_MESSAGE_CHARACTERS,
    MessageInputError, load_trusted_artifact, predict_message)
from scamlens.url_analysis import MAX_URL_CHARACTERS, URLInputError, observe_url
from scamlens.url_inference import URLArtifactError, load_url_artifact, predict_url
from scamlens.screenshot_analysis import (
    MAX_UPLOAD_BYTES, OCRProcessingError, ScreenshotValidationError,
    analyze_reviewed_text, apply_ocr_to_state, clear_analysis_state,
    extract_english_text, validate_screenshot,
)

ROOT = Path(__file__).resolve().parent
MESSAGE_MODEL = ROOT / "artifacts/message/sms_spam_ham_pipeline.joblib"
EMAIL_MODEL = ROOT / "artifacts/email/baseline_v1/email_pipeline.joblib"
MESSAGE_METRICS = ROOT / "artifacts/message/test_metrics.json"
EMAIL_METRICS = ROOT / "artifacts/email/baseline_v1/metrics.json"
URL_MODEL = ROOT / "artifacts/url/baseline_v1/url_pipeline.joblib"
URL_METRICS = ROOT / "artifacts/url/baseline_v1/metrics.json"

APP_CSS = """
<style>
.scamlens-brand {
  border: 1px solid rgba(128,128,128,.28); border-radius: 16px;
  padding: 1.15rem 1.25rem; margin: 0 0 1.25rem 0;
  background: linear-gradient(135deg, rgba(28,91,153,.12), rgba(23,140,112,.08));
}
.scamlens-brand h1 { margin: 0; font-size: clamp(1.8rem, 5vw, 2.55rem); }
.scamlens-brand p { margin: .35rem 0 0; max-width: 52rem; }
.scamlens-eyebrow { font-size: .78rem; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; opacity: .72; margin-bottom: .25rem; }
.scamlens-step { font-size: .82rem; font-weight: 700; letter-spacing: .055em;
  text-transform: uppercase; opacity: .68; margin: 1.15rem 0 .25rem; }
.scamlens-flow { border: 1px solid rgba(128,128,128,.25); border-radius: 12px;
  padding: .75rem 1rem; margin: .35rem 0 1rem; font-weight: 600; }
@media (max-width: 640px) { .scamlens-brand { padding: .9rem; } }
</style>
"""

def render_brand() -> None:
    st.markdown(APP_CSS,unsafe_allow_html=True)
    st.markdown("""<div class="scamlens-brand"><div class="scamlens-eyebrow">Local decision support</div><h1>ScamLens</h1><p>Review messages, emails, screenshots, and URL strings with transparent experimental baselines.</p><p><strong>Results are evidence-support tools—not proof of fraud or safety.</strong></p></div>""",unsafe_allow_html=True)

def page_intro(category: str, title: str, description: str) -> None:
    st.markdown(f'<div class="scamlens-eyebrow">{category}</div>',unsafe_allow_html=True)
    st.header(title)
    st.write(description)

def step(label: str) -> None:
    st.markdown(f'<div class="scamlens-step">{label}</div>',unsafe_allow_html=True)

@st.cache_resource
def get_message_model() -> dict[str, object]:
    return load_trusted_artifact(MESSAGE_MODEL)

@st.cache_resource
def get_email_model() -> dict[str, object]:
    return load_email_artifact(EMAIL_MODEL)

@st.cache_resource
def get_url_model() -> dict[str, object]:
    return load_url_artifact(URL_MODEL)

@st.cache_data
def load_report(path: Path) -> dict[str, object]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"The local report {path.name} could not be loaded.") from error
    if not isinstance(report, dict):
        raise RuntimeError(f"The local report {path.name} has an invalid structure.")
    return report

def clear_message() -> None:
    st.session_state.pop("message_result", None)
    st.session_state.pop("analyzed_message", None)

def clear_email() -> None:
    st.session_state.pop("email_result", None)
    st.session_state.pop("analyzed_email", None)

def clear_url() -> None:
    st.session_state.pop("url_result", None)
    st.session_state.pop("analyzed_url", None)

def clear_screenshot_result() -> None:
    clear_analysis_state(st.session_state)

def message_view() -> None:
    page_intro("Message workflow", "Message Analysis", "Classify reviewed English message text with the established SMS spam/ham baseline.")
    st.info("This prototype is a decision-support demonstration. Its output is not a guarantee that a message is safe, harmful, legitimate, or fraudulent.")
    try:
        bundle = get_message_model()
    except ArtifactLoadError as error:
        st.error(str(error)); return
    with st.expander("Illustrative examples"):
        st.caption("These examples only demonstrate the interface. They are not evidence of model accuracy and do not guarantee the result for similar messages.")
        st.markdown("- **Illustrative ham-style text:** “Are we still meeting for lunch today?”\n- **Illustrative spam-style text:** “You have won a prize. Reply now to claim.”")
    step("A · Input")
    with st.container(border=True):
        message = st.text_area("Message", key="message_input",
            placeholder="Paste an English SMS message here...",
            help=f"Maximum {MAX_MESSAGE_CHARACTERS:,} characters. Text is never truncated.",
            height=180, on_change=clear_message)
        st.caption("English text only · Maximum 5,000 characters · Processed locally")
        analyze_message=st.button("Analyze message", type="primary")
    if analyze_message:
        try:
            result = predict_message(bundle, message)
        except (MessageInputError, ArtifactLoadError) as error:
            clear_message(); st.error(str(error))
        else:
            st.session_state["message_result"] = result
            st.session_state["analyzed_message"] = message
    result = st.session_state.get("message_result")
    if result is not None and st.session_state.get("analyzed_message") == message:
        step("B · Model result")
        label = "Spam" if result.label == "spam" else "Ham (non-spam)"
        if result.label == "spam":
            st.warning(f"Predicted class: {label}")
        else:
            with st.container(border=True):
                st.markdown(f"**Predicted class: {label}**")
                st.caption("A Ham (non-spam) classification does not confirm that this message is safe.")
        step("C · Classifier output")
        with st.container(border=True):
            st.metric("Model spam score", f"{result.spam_score:.3f}")
            st.caption(f"The configured classification threshold is {result.threshold:.2f}.")
            st.write("The model spam score is a classifier output, not a verified probability of fraud, harm, or message safety.")
            st.caption("This version does not identify or explain specific reasons for its prediction.")
        step("D · Recommended verification steps")
        st.markdown("- Independently verify unexpected or consequential requests.\n- Avoid replying, paying, or sharing credentials based only on this result.\n- Use a known contact method when a message claims to represent an organization.")
    step("Limitations · Interpretation and privacy")
    with st.container(border=True):
        st.markdown("- Trained on an older English-language SMS spam/ham dataset.\n- Not validated for phishing, emails, job scams, fraud, or other languages.\n- The application does not automatically detect the input language.\n- Messages are processed locally for inference and are not written to files, logged by this application, or sent to external services.")

def email_view() -> None:
    page_intro("Email workflow · Experimental", "Email Analysis", "Review Subject and Body text with an exploratory three-class within-corpus baseline.")
    st.warning("Experimental: performance is measured only within the model's source corpus. Generalization to real-world email is not established.")
    st.info("Predictions are decision-support outputs, not proof that an email is safe, legitimate, spam, or phishing. Do not act on this result alone.")
    try:
        bundle = get_email_model()
    except EmailArtifactError as error:
        st.error(str(error)); return
    step("A · Input")
    with st.container(border=True):
        subject = st.text_input("Subject", key="email_subject_input",
            placeholder="Paste the email subject (optional if Body is provided)", on_change=clear_email)
        body = st.text_area("Body", key="email_body_input",
            placeholder="Paste the email body (optional if Subject is provided)",
            help=f"Subject and Body together may contain at most {MAX_EMAIL_CHARACTERS:,} characters. Input is not truncated.",
            height=240, on_change=clear_email)
        analyze_email=st.button("Analyze email", type="primary")
    if analyze_email:
        try:
            result = predict_email(bundle, subject=subject, body=body)
        except (EmailInputError, EmailArtifactError) as error:
            clear_email(); st.error(str(error))
        else:
            st.session_state["email_result"] = result
            st.session_state["analyzed_email"] = (subject, body)
    result = st.session_state.get("email_result")
    if result is not None and st.session_state.get("analyzed_email") == (subject, body):
        observations = observe_email_text(subject, body)
        step("B · Model result")
        if result.label == "Valid":
            with st.container(border=True):
                st.markdown("**Predicted class: Valid**")
                st.caption("A Valid classification does not confirm that this email is safe.")
        else:
            st.warning(f"Predicted class: {result.label}")
        step("C · Classifier outputs")
        with st.container(border=True):
            for column, label in zip(st.columns(3), ("Valid", "Spam", "Phishing")):
                column.metric(f"{label} score", f"{result.scores[label]:.3f}")
            st.caption("Scores are model outputs that sum to 1; they are not verified probabilities of safety, fraud, or harm.")
        step("D · Deterministic observations")
        st.subheader("Observed indicators")
        st.caption(
            "These are deterministic text-pattern matches, separate from the ML "
            "prediction. They do not change the predicted class or scores."
        )
        if observations:
            st.markdown("\n".join(f"- {item}" for item in observations))
            if result.label == "Valid":
                st.warning(
                    "The classifier predicted Valid, but the text contains indicators "
                    "that warrant additional verification."
                )
        else:
            st.write(
                "No supported textual indicators were detected. This does not confirm "
                "that the email is safe."
            )
        step("E · Recommended verification steps")
        st.subheader("What should I do next?")
        if observations:
            st.markdown(
                "- Do not use links, buttons, contact details, or instructions in the email.\n"
                "- Verify the request through an independently trusted website, app, "
                "phone number, or known contact.\n"
                "- If the message concerns an account, open the service directly and "
                "check for alerts there.\n"
                "- Report or delete the email if independent verification fails."
            )
        else:
            st.markdown(
                "- Treat the classifier result as one limited signal, not a safety check.\n"
                "- Independently verify unexpected or consequential requests before acting.\n"
                "- Avoid using email-provided links or contact details when in doubt."
            )
    step("Limitations · Interpretation and privacy")
    with st.container(border=True):
        st.markdown("- This is an exploratory three-class baseline evaluated within one corpus.\n- It may rely on dataset-specific writing or formatting patterns.\n- It does not inspect links, attachments, images, sender identity, or headers.\n- Subject and Body are processed locally by the existing model and are not written to files, logged by this application, or sent to external services.")

def url_view() -> None:
    page_intro("URL workflow · String only", "URL Analysis", "Inspect lexical URL-string patterns with the frozen experimental baseline.")
    st.info("ScamLens analyzes the URL string only. It does not visit the website, inspect its content, check reputation, or verify ownership.")
    st.warning("This experimental classifier cannot establish that a website is safe or malicious. Do not open a link solely to test it.")
    try:
        bundle=get_url_model()
    except URLArtifactError as error:
        st.error(str(error)); return
    step("A · Input")
    with st.container(border=True):
        value=st.text_input("URL",key="url_input",placeholder="https://example.com/path",
            help=f"Include http:// or https://. Maximum {MAX_URL_CHARACTERS:,} characters. Input is not rewritten.",on_change=clear_url)
        st.caption("The literal URL string is processed locally and is not opened.")
        analyze_url=st.button("Analyze URL",type="primary")
    if analyze_url:
        try: result=predict_url(bundle,value)
        except (URLInputError,URLArtifactError) as error:
            clear_url(); st.error(str(error))
        else:
            st.session_state["url_result"]=result; st.session_state["analyzed_url"]=value
    result=st.session_state.get("url_result")
    if result is not None and st.session_state.get("analyzed_url")==value:
        step("B · Model result")
        label="Benign" if result.label=="benign" else "Phishing"
        if result.label=="phish": st.warning(f"Model prediction: {label}")
        else:
            with st.container(border=True):
                st.markdown("**Model prediction: Benign**")
                st.caption("A Benign prediction does not confirm that this URL or website is safe.")
        step("C · Classifier outputs")
        with st.container(border=True):
            cols=st.columns(2); cols[0].metric("Benign score",f"{result.scores['benign']:.3f}"); cols[1].metric("Phishing score",f"{result.scores['phish']:.3f}")
            st.caption("Classifier scores are model outputs, not verified probabilities of safety, phishing, or harm.")
        observations=observe_url(value)
        step("D · Deterministic observations")
        st.subheader("Observed URL indicators")
        st.caption("Deterministic string-level observations are separate from the ML prediction. They are not reputation checks and do not change the class or scores.")
        if observations:
            st.markdown("\n".join(f"- {item}" for item in observations))
            if result.label=="benign": st.warning("The classifier predicted Benign, but the URL contains string-level indicators that warrant additional verification.")
        else: st.write("No supported string-level indicators were detected. This does not confirm that the URL is safe.")
        step("E · Recommended verification steps")
        st.subheader("What should I do next?")
        st.markdown("- Do not open a suspicious link solely to test it.\n- Independently navigate to the organization's official site or app.\n- Verify the sender or request through a trusted channel.\n- Avoid entering credentials or payment information when uncertain.")
    step("Limitations · Interpretation and privacy")
    with st.container(border=True):
        st.markdown("- Analysis uses the submitted URL string only; it does not inspect the webpage.\n- No reputation, DNS, WHOIS, certificate, ownership, or domain-age lookup is performed.\n- A prediction does not guarantee safety or maliciousness. HTTPS is not treated as proof of legitimacy.\n- The submitted URL is processed locally in this version and is not written to files or sent to external services.")

def screenshot_view() -> None:
    page_intro("Screenshot workflow · Local OCR", "Screenshot Analysis", "Extract English text locally, review it, then choose whether to analyze the corrected text.")
    st.markdown('<div class="scamlens-flow">1. Upload screenshot &nbsp;→&nbsp; 2. Local OCR &nbsp;→&nbsp; 3. Review text &nbsp;→&nbsp; 4. Analyze explicitly</div>',unsafe_allow_html=True)
    st.info("Upload screenshot → review and correct local OCR text → explicitly click Analyze reviewed text.")
    st.warning("English OCR can make transcription errors. Verify and correct all extracted text before analysis; OCR output is never classified automatically.")
    step("A · Upload and local OCR")
    with st.container(border=True):
        upload=st.file_uploader("Screenshot",type=["png","jpg","jpeg","webp"],
            help=f"PNG, JPEG/JPG, or WEBP; maximum {MAX_UPLOAD_BYTES // (1024*1024)} MiB. Images are not stored by this application.")
    ready=False
    if upload is not None:
        data=upload.getvalue()
        try: screenshot=validate_screenshot(data,upload.type)
        except ScreenshotValidationError as error:
            st.session_state.pop("screenshot_fingerprint",None); st.session_state.pop("reviewed_ocr_text",None); clear_screenshot_result(); st.error(str(error))
        else:
            if st.session_state.get("screenshot_fingerprint")!=screenshot.sha256:
                clear_screenshot_result()
                try: text=extract_english_text(screenshot)
                except OCRProcessingError as error:
                    st.session_state.pop("reviewed_ocr_text",None); st.error(str(error))
                else:
                    apply_ocr_to_state(st.session_state,fingerprint=screenshot.sha256,text=text)
            ready="reviewed_ocr_text" in st.session_state
    else:
        st.session_state.pop("screenshot_fingerprint",None); st.session_state.pop("reviewed_ocr_text",None); clear_screenshot_result()
    if ready:
        step("B · Review and edit extracted text")
        reviewed=st.text_area("Extracted text — review and correct before analysis",key="reviewed_ocr_text",height=240,on_change=clear_screenshot_result)
        if not reviewed.strip(): st.error("OCR did not produce usable text. Enter or correct the text before analysis.")
        step("C · Analyze action")
        if st.button("Analyze reviewed text",type="primary",disabled=not reviewed.strip()):
            try: result=analyze_reviewed_text(get_message_model(),reviewed)
            except (MessageInputError,ArtifactLoadError) as error:
                clear_screenshot_result(); st.error(str(error))
            else:
                st.session_state["screenshot_result"]=result; st.session_state["analyzed_reviewed_text"]=reviewed
        result=st.session_state.get("screenshot_result")
        if result is not None and st.session_state.get("analyzed_reviewed_text")==reviewed:
            step("D · Model result")
            label="Spam" if result.label=="spam" else "Ham (non-spam)"
            if result.label=="spam": st.warning(f"Predicted class: {label}")
            else:
                with st.container(border=True):
                    st.markdown(f"**Predicted class: {label}**")
                    st.caption("A Ham (non-spam) classification does not confirm that this text or screenshot is safe.")
            step("E · Classifier output")
            with st.container(border=True):
                st.metric("Model spam score",f"{result.spam_score:.3f}")
                st.caption(f"The existing message model threshold is {result.threshold:.2f}. This is an experimental English SMS spam/ham output, not a phishing, fraud, authenticity, or safety determination.")
            step("F · Recommended verification steps")
            st.markdown("- Verify the corrected text against the screenshot before relying on it.\n- Independently confirm unexpected requests through a known contact channel.\n- Do not open OCR-detected links solely to investigate them.")
    step("Limitations · Interpretation and privacy")
    with st.container(border=True):
        st.markdown("- OCR is English-only and may omit, alter, or invent characters.\n- Classification uses only the text you review and submit; it does not analyze visual layout, sender identity, authenticity, image manipulation, logos, QR-code safety, or website legitimacy.\n- URLs appearing in OCR text are never opened or fetched.\n- Screenshots and extracted text are processed locally and are not stored, intentionally logged, or sent to external services by this application.")

def performance_view() -> None:
    page_intro("Evaluation reference", "Model Performance", "Read stored evaluation results in their original experimental scope.")
    st.info("These are stored evaluation results from the existing local artifacts. Opening this view does not run training or evaluation.")
    try:
        message = load_report(MESSAGE_METRICS)
        email_report = load_report(EMAIL_METRICS)
        url_report = load_report(URL_METRICS)
        sms = message["selected_pipeline"]["all_rows"]
        email = email_report["logistic_regression"]["test"]
        url = url_report["official_temporal_test"]
    except (RuntimeError, KeyError, TypeError) as error:
        st.error(f"Performance reports are unavailable: {error}"); return
    for title,values,third_label,third_value,scope in (
        ("Message Analysis — held-out SMS test split",sms,"Spam recall",sms['per_class']['spam']['recall'],f"{message['test_rows']:,} rows; experimental English SMS spam/ham baseline on its held-out test split."),
        ("Email Analysis — held-out within-corpus test split",email,"Phishing recall",email['per_class']['Phishing']['recall'],"776 rows; Valid/Spam/Phishing baseline. Within-corpus only; real-world generalization is not established."),
        ("URL Analysis — filtered official temporal test",url,"Phishing recall",url['per_class']['phish']['recall'],"166,494 URL-string-only rows after documented filters. Substantial domain overlap, collection-time confounding, and label noise remain limitations."),
    ):
        with st.container(border=True):
            st.subheader(title); cols=st.columns(3); cols[0].metric("Accuracy",f"{values['accuracy']:.3f}"); cols[1].metric("Macro F1",f"{values['macro_f1']:.3f}"); cols[2].metric(third_label,f"{third_value:.3f}"); st.caption(scope)
    st.warning("These models use different datasets, labels, and evaluation designs. Their metrics are not directly comparable and do not measure real-world safety.")

st.set_page_config(page_title="ScamLens", page_icon="🔎", layout="centered")
render_brand()
st.sidebar.markdown("## ScamLens")
st.sidebar.caption("Choose one analysis workflow or review stored evaluation results.")
view = st.sidebar.radio("Workspace", ("Message Analysis", "Email Analysis", "Screenshot Analysis", "URL Analysis", "Model Performance"), index=0)
st.sidebar.divider()
st.sidebar.caption("Local application workflows · Experimental models · No safety guarantees")
if view == "Message Analysis": message_view()
elif view == "Email Analysis": email_view()
elif view == "Screenshot Analysis": screenshot_view()
elif view == "URL Analysis": url_view()
else: performance_view()
