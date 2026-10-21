"""The WhatsApp service: one job, sending messages.

It knows nothing about bids, parties or the desk. It takes a number and a
message, hands it to Meta's Cloud API, and reports what happened. Everything
that decides *what* to say lives elsewhere.

These tests never touch the network: the transport is swapped for a double
that records what would have gone out, which is also how the rest of the
suite keeps a bid from texting anybody.
"""

from __future__ import annotations

import pytest

from app.services import whatsapp


# --- the number ------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("typed", "sent"),
    [
        ("7801833884", "917801833884"),
        ("+91 78018 33884", "917801833884"),
        ("+917801833884", "917801833884"),
        ("078018-33884", "917801833884"),
        ("91 9925552909", "919925552909"),
        ("(+91) 99255 52909", "919925552909"),
    ],
)
def test_an_indian_number_is_dialled_the_way_meta_wants_it(typed, sent):
    """Traders write a number six different ways; WhatsApp accepts one."""
    assert whatsapp.to_e164(typed) == sent


@pytest.mark.parametrize("typed", ["", "   ", None, "12345", "not a phone", "+1 555 0100 x3"])
def test_a_number_that_cannot_be_dialled_is_refused(typed):
    """Better to report an unsendable number than to post nonsense to Meta."""
    assert whatsapp.to_e164(typed) is None


def test_a_number_from_another_country_keeps_its_own_code():
    assert whatsapp.to_e164("+971 50 123 4567") == "971501234567"


# --- sending ---------------------------------------------------------------- #
def test_a_message_goes_out_and_comes_back_with_an_id(whatsapp_outbox):
    result = whatsapp.send_text("7801833884", "Bid #12 is open.")

    assert result.ok is True
    assert result.message_id
    assert result.error is None
    assert whatsapp_outbox.sent == [("917801833884", "Bid #12 is open.")]


def test_the_service_reports_a_refusal_rather_than_raising(whatsapp_outbox):
    """A failed message must never take down whatever was sending it."""
    whatsapp_outbox.fail_with = "131030: recipient not in allowed list"

    result = whatsapp.send_text("7801833884", "Bid #12 is open.")

    assert result.ok is False
    assert result.message_id is None
    assert "131030" in result.error


def test_an_undialable_number_never_reaches_the_network(whatsapp_outbox):
    result = whatsapp.send_text("not a phone", "Bid #12 is open.")

    assert result.ok is False
    assert "number" in result.error.lower()
    assert whatsapp_outbox.sent == [], "nothing was attempted"


def test_nothing_is_sent_when_whatsapp_is_not_configured(whatsapp_unconfigured):
    """Before the credentials arrive, the desk still works - quietly."""
    result = whatsapp.send_text("7801833884", "Bid #12 is open.")

    assert result.ok is False
    assert result.skipped is True
    assert "not configured" in result.error.lower()


def test_a_template_carries_its_variables_in_order(whatsapp_outbox):
    """Business-initiated messages must use a template Meta has approved."""
    result = whatsapp.send_template(
        "9925552909",
        template="bid_invitation",
        params=["Patel Roadways", "500 MT PVC K-67", "https://example.test/portal/abc/12"],
    )

    assert result.ok is True
    assert whatsapp_outbox.templates == [
        (
            "919925552909",
            "bid_invitation",
            ["Patel Roadways", "500 MT PVC K-67", "https://example.test/portal/abc/12"],
        )
    ]


def test_the_request_meta_would_receive(whatsapp_outbox):
    """Pin the payload shape, so a Cloud API change is caught here."""
    body = whatsapp.build_template_payload(
        "917801833884", "bid_invitation", ["Jay Transport", "20 MT", "https://example.test/x"]
    )

    assert body["messaging_product"] == "whatsapp"
    assert body["to"] == "917801833884"
    assert body["type"] == "template"
    assert body["template"]["name"] == "bid_invitation"
    assert body["template"]["language"]["code"] == whatsapp.settings.whatsapp_language
    parameters = body["template"]["components"][0]["parameters"]
    assert [p["text"] for p in parameters] == ["Jay Transport", "20 MT", "https://example.test/x"]
    assert all(p["type"] == "text" for p in parameters)


def test_a_template_with_no_variables_sends_no_components(whatsapp_outbox):
    """Meta's own hello_world template takes none, and rejects an empty list."""
    body = whatsapp.build_template_payload("917801833884", "hello_world", [])
    assert "components" not in body["template"]
