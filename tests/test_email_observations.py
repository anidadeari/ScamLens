"""Tests for deterministic observations kept separate from email inference."""

from scamlens.email_observations import observe_email_text


SUBJECT = "Urgent: Verify your account immediately"
BODY = """Dear customer,

We detected unusual activity on your account. Your account will be suspended unless
you verify your information immediately.

Please click the link below and confirm your account details.
"""


def test_synthetic_disagreement_example_has_supported_observations() -> None:
    assert observe_email_text(SUBJECT, BODY) == [
        "Urgency language",
        "Account-verification language",
        "Threat of account restriction or suspension",
        "Request to click or follow a link",
    ]


def test_observations_are_general_patterns_not_an_email_classification() -> None:
    assert observe_email_text("Meeting notes", "Agenda attached for tomorrow") == []
    assert observe_email_text("Action needed", "Follow the link to update credentials") == [
        "Account-verification language",
        "Request to click or follow a link",
    ]
