"""Streamlit interaction tests for the minimal user interface."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from scamlens.email_inference import MAX_EMAIL_CHARACTERS
from scamlens.message_inference import MAX_MESSAGE_CHARACTERS


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def load_app() -> AppTest:
    app = AppTest.from_file(str(APP_PATH)).run()
    assert not app.exception
    return app


def test_empty_whitespace_and_oversized_inputs_show_errors() -> None:
    app = load_app()
    app.button[0].click().run()
    assert "Enter a message" in app.error[0].value

    app.text_area[0].set_value("   ").run()
    app.button[0].click().run()
    assert "Enter a message" in app.error[0].value

    app.text_area[0].set_value("x" * (MAX_MESSAGE_CHARACTERS + 1)).run()
    app.button[0].click().run()
    assert "Nothing was truncated" in app.error[0].value


def test_valid_analysis_and_input_change_clear_stale_result() -> None:
    app = load_app()
    app.text_area[0].set_value("You have won a prize. Reply now to claim.").run()
    app.button[0].click().run()
    assert app.warning[0].value == "Predicted class: Spam"
    assert app.metric[0].label == "Model spam score"

    app.text_area[0].set_value("Are we meeting for lunch?").run()
    assert len(app.warning) == 0
    assert len(app.metric) == 0


def test_ham_result_is_neutral_and_does_not_imply_safety() -> None:
    app = load_app()
    app.text_area[0].set_value("Are we meeting for lunch?").run()
    app.button[0].click().run()

    markdown_values = [element.value for element in app.markdown]
    caption_values = [element.value for element in app.caption]
    assert "**Predicted class: Ham (non-spam)**" in markdown_values
    assert any("does not confirm" in value for value in caption_values)
    assert len(app.success) == 0


def test_message_analysis_remains_the_default_view() -> None:
    app = load_app()
    assert app.sidebar.radio[0].value == "Message Analysis"
    assert app.sidebar.radio[0].options == [
        "Message Analysis",
        "Email Analysis",
        "Screenshot Analysis",
        "URL Analysis",
        "Model Performance",
    ]
    assert app.text_area[0].label == "Message"
    assert app.button[0].label == "Analyze message"


def test_application_identity_uses_evidence_support_language() -> None:
    app = load_app()
    rendered = "\n".join(element.value for element in app.markdown)
    assert "ScamLens" in rendered
    assert "evidence-support tools" in rendered
    assert "not proof of fraud or safety" in rendered


def load_email_view() -> AppTest:
    app = load_app()
    app.sidebar.radio[0].set_value("Email Analysis").run()
    assert not app.exception
    return app


def test_email_analysis_is_separate_and_validates_input() -> None:
    app = load_email_view()
    assert app.text_input[0].label == "Subject"
    assert app.text_area[0].label == "Body"
    assert app.button[0].label == "Analyze email"
    app.button[0].click().run()
    assert "Subject or Body" in app.error[0].value
    app.text_area[0].set_value("x" * (MAX_EMAIL_CHARACTERS + 1)).run()
    app.button[0].click().run()
    assert "character limit" in app.error[0].value


def test_email_analysis_has_three_scores_and_clears_stale_result() -> None:
    app = load_email_view()
    app.text_input[0].set_value("Account security alert").run()
    app.text_area[0].set_value("Verify your credentials immediately.").run()
    app.button[0].click().run()
    displayed = [item.value for item in app.warning] + [item.value for item in app.markdown]
    assert any("Predicted class:" in value for value in displayed)
    assert [metric.label for metric in app.metric] == [
        "Valid score", "Spam score", "Phishing score"
    ]
    app.text_area[0].set_value("Changed email body").run()
    assert len(app.metric) == 0


def test_valid_prediction_with_indicators_shows_disagreement_and_guidance() -> None:
    app = load_email_view()
    app.text_input[0].set_value("Urgent: Verify your account immediately").run()
    app.text_area[0].set_value(
        "Dear customer,\n\nWe detected unusual activity on your account. Your "
        "account will be suspended unless you verify your information immediately.\n\n"
        "Please click the link below and confirm your account details.\n\nThank you,\n"
        "Account Security Team"
    ).run()
    app.button[0].click().run()

    assert "**Predicted class: Valid**" in [item.value for item in app.markdown]
    assert [metric.label for metric in app.metric] == [
        "Valid score", "Spam score", "Phishing score"
    ]
    subheaders = [item.value for item in app.subheader]
    assert "Observed indicators" in subheaders
    assert "What should I do next?" in subheaders
    markdown = "\n".join(item.value for item in app.markdown)
    assert "Urgency language" in markdown
    assert "Account-verification language" in markdown
    assert "Threat of account restriction or suspension" in markdown
    assert "Request to click or follow a link" in markdown
    assert any(
        "classifier predicted Valid" in item.value
        and "additional verification" in item.value
        for item in app.warning
    )


def test_model_performance_is_a_separate_stored_results_view() -> None:
    app = load_app()
    app.sidebar.radio[0].set_value("Model Performance").run()
    assert not app.exception
    assert len(app.text_area) == 0
    assert len(app.button) == 0
    assert [metric.label for metric in app.metric] == [
        "Accuracy", "Macro F1", "Spam recall",
        "Accuracy", "Macro F1", "Phishing recall",
        "Accuracy", "Macro F1", "Phishing recall",
    ]
    subheaders = [item.value for item in app.subheader]
    assert any("SMS test split" in value for value in subheaders)
    assert any("within-corpus test split" in value for value in subheaders)
    assert any("official temporal test" in value for value in subheaders)


def load_url_view() -> AppTest:
    app=load_app(); app.sidebar.radio[0].set_value("URL Analysis").run(); assert not app.exception; return app


def test_url_view_validation_disagreement_and_stale_result():
    app=load_url_view()
    assert "URL string only" in app.info[0].value
    app.button[0].click().run(); assert "Enter a URL" in app.error[0].value
    value="https://example.com/login?item0=value&item1=value&item2=value&item3=value&item4=value&item5=value&item6=value&item7=value"
    app.text_input[0].set_value(value).run(); app.button[0].click().run()
    assert "**Model prediction: Benign**" in [item.value for item in app.markdown]
    assert [item.label for item in app.metric]==["Benign score","Phishing score"]
    assert "Observed URL indicators" in [item.value for item in app.subheader]
    assert any("classifier predicted Benign" in item.value for item in app.warning)
    app.text_input[0].set_value("https://example.com/login").run(); assert len(app.metric)==0


def test_url_view_can_show_phishing_without_observations():
    app=load_url_view(); app.text_input[0].set_value("https://example.com").run(); app.button[0].click().run()
    assert any(item.value=="Model prediction: Phishing" for item in app.warning)
    assert any("No supported string-level indicators" in item.value for item in app.markdown)


def test_screenshot_view_renders_as_a_separate_review_first_mode():
    app=load_app(); app.sidebar.radio[0].set_value("Screenshot Analysis").run()
    assert not app.exception
    assert app.sidebar.radio[0].value=="Screenshot Analysis"
    assert any("review and correct" in item.value for item in app.info)
    assert any("never classified automatically" in item.value for item in app.warning)
    assert len(app.metric)==0
