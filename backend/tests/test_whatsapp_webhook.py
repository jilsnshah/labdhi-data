"""Meta's webhook: what happens when somebody writes to the desk's number.

The two things worth testing here are both about a public endpoint that writes
to the database.

A payload has to be proved to come from Meta, by a signature over the raw body
- not over the parsed JSON, which is a different string of bytes.

And the same message has to land once however often it arrives. Meta retries a
webhook until it gets a 200, so a blip means the whole payload comes again, and
the desk seeing one reply three times would be worse than seeing none.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from app.core.config import settings
from app.models.whatsapp_message import WhatsAppMessage

URL = "/api/v1/webhooks/whatsapp"
SECRET = "test-app-secret"


@pytest.fixture
def signed(monkeypatch):
    """Webhook configured the way production is: a secret and a verify token."""
    monkeypatch.setattr(settings, "whatsapp_app_secret", SECRET, raising=False)
    monkeypatch.setattr(settings, "whatsapp_verify_token", "let-me-in", raising=False)


def sign(body: bytes, secret: str = SECRET) -> dict[str, str]:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {"X-Hub-Signature-256": f"sha256={digest}", "Content-Type": "application/json"}


def message(
    wa_id: str = "wamid.TEST1",
    sender: str = "917801833884",
    text: str | None = "Yes, send me the rate.",
    name: str = "Jay Transport",
    kind: str = "text",
) -> dict:
    """One message in the envelope Meta actually sends."""
    body: dict = {
        "id": wa_id,
        "from": sender,
        "timestamp": "1790000000",
        "type": kind,
    }
    if kind == "text" and text is not None:
        body["text"] = {"body": text}
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "200000000000002",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550001111",
                                "phone_number_id": "100000000000001",
                            },
                            "contacts": [{"profile": {"name": name}, "wa_id": sender}],
                            "messages": [body],
                        },
                    }
                ],
            }
        ],
    }


def post(client, payload: dict, secret: str | None = SECRET):
    raw = json.dumps(payload).encode()
    headers = sign(raw, secret) if secret else {"Content-Type": "application/json"}
    return client.post(URL, content=raw, headers=headers)


def stored(db_session) -> list[WhatsAppMessage]:
    return list(db_session.query(WhatsAppMessage).order_by(WhatsAppMessage.id).all())


# --- the handshake ----------------------------------------------------------- #
def test_the_subscribe_handshake_echoes_the_challenge(client, signed):
    """Meta calls this once, when the URL is saved in their dashboard."""
    response = client.get(
        URL,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "let-me-in",
            "hub.challenge": "1158201444",
        },
    )

    assert response.status_code == 200
    assert response.text == "1158201444", "bare text; a quoted JSON string is refused by Meta"


def test_a_wrong_verify_token_is_refused(client, signed):
    response = client.get(
        URL,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "guessed",
            "hub.challenge": "1158201444",
        },
    )
    assert response.status_code == 403


def test_nothing_verifies_before_a_token_is_configured(client):
    """An unconfigured webhook cannot be talked into confirming itself."""
    response = client.get(
        URL,
        params={"hub.mode": "subscribe", "hub.verify_token": "", "hub.challenge": "x"},
    )
    assert response.status_code == 403


# --- proving it came from Meta ------------------------------------------------ #
def test_a_signed_payload_is_accepted(client, signed, db_session):
    assert post(client, message()).status_code == 200
    assert len(stored(db_session)) == 1


def test_an_unsigned_payload_is_refused(client, signed, db_session):
    response = post(client, message(), secret=None)

    assert response.status_code == 403
    assert stored(db_session) == [], "nothing a stranger sends is written down"


def test_a_payload_signed_with_the_wrong_secret_is_refused(client, signed, db_session):
    response = post(client, message(), secret="not-our-secret")

    assert response.status_code == 403
    assert stored(db_session) == []


def test_the_signature_covers_the_body_that_was_sent(client, signed, db_session):
    """Signing one body and sending another is the attack this stops."""
    raw = json.dumps(message()).encode()
    headers = sign(raw)
    tampered = json.dumps(message(wa_id="wamid.OTHER", text="Ignore that, I said yes")).encode()

    response = client.post(URL, content=tampered, headers=headers)

    assert response.status_code == 403
    assert stored(db_session) == []


def test_production_without_a_secret_accepts_nothing(client, monkeypatch, db_session):
    """A deployment nobody finished configuring refuses rather than trusts."""
    monkeypatch.setattr(settings, "whatsapp_app_secret", "", raising=False)
    monkeypatch.setattr(settings, "environment", "production", raising=False)

    response = post(client, message(), secret=None)

    assert response.status_code == 403
    assert stored(db_session) == []


# --- writing it down once ----------------------------------------------------- #
def test_what_is_kept_from_a_message(client, signed, db_session):
    post(client, message())

    row = stored(db_session)[0]
    assert row.wa_message_id == "wamid.TEST1"
    assert row.from_number == "917801833884"
    assert row.message_type == "text"
    assert row.body == "Yes, send me the rate."
    assert row.profile_name == "Jay Transport"
    assert row.phone_number_id == "100000000000001"
    assert row.sent_at.year == 2026
    assert row.raw["id"] == "wamid.TEST1", "kept as it arrived"


def test_the_same_message_twice_is_stored_once(client, signed, db_session):
    """Meta retries until it gets a 200, so this happens after every blip."""
    first = post(client, message())
    second = post(client, message())

    assert first.json() == {"received": 1, "stored": 1, "duplicates": 0}
    assert second.json() == {"received": 1, "stored": 0, "duplicates": 1}
    assert len(stored(db_session)) == 1


def test_a_retry_carrying_one_new_message_stores_only_that_one(client, signed, db_session):
    post(client, message(wa_id="wamid.A"))

    payload = message(wa_id="wamid.A")
    second = dict(payload["entry"][0]["changes"][0]["value"]["messages"][0])
    second["id"] = "wamid.B"
    second["text"] = {"body": "And the freight?"}
    payload["entry"][0]["changes"][0]["value"]["messages"].append(second)

    assert post(client, payload).json() == {"received": 2, "stored": 1, "duplicates": 1}
    assert [row.wa_message_id for row in stored(db_session)] == ["wamid.A", "wamid.B"]


def test_a_known_number_is_matched_to_its_party(client, auth, signed, db_session, parties):
    client.patch(
        f"/api/v1/parties/{parties['transporter']}",
        json={"phone": "+91 78018 33884"},
        headers=auth,
    )
    post(client, message(sender="917801833884"))

    row = stored(db_session)[0]
    assert row.party_id == parties["transporter"], "written half a dozen ways, still one number"


def test_a_number_we_do_not_know_is_still_kept(client, signed, db_session):
    """Anyone at all can write to a WhatsApp number; that is not an error."""
    post(client, message(sender="919000000000", name="Nobody We Know"))

    row = stored(db_session)[0]
    assert row.party_id is None
    assert row.profile_name == "Nobody We Know"


# --- everything else Meta sends ----------------------------------------------- #
def test_a_message_with_no_words_is_kept_for_its_kind(client, signed, db_session):
    post(client, message(kind="image", text=None, wa_id="wamid.IMG"))

    row = stored(db_session)[0]
    assert row.message_type == "image"
    assert row.body is None


def test_a_button_reply_keeps_what_they_tapped(client, signed, db_session):
    payload = message(kind="button", text=None, wa_id="wamid.BTN")
    payload["entry"][0]["changes"][0]["value"]["messages"][0]["button"] = {
        "text": "Send me the rate",
        "payload": "RATE",
    }
    post(client, payload)

    assert stored(db_session)[0].body == "Send me the rate"


def test_a_delivery_receipt_is_acknowledged_and_stored_as_nothing(client, signed, db_session):
    """Statuses for messages *we* sent arrive here too. Not messages, not kept."""
    payload = message()
    value = payload["entry"][0]["changes"][0]["value"]
    del value["messages"]
    value["statuses"] = [
        {
            "id": "wamid.OURS",
            "status": "delivered",
            "timestamp": "1790000001",
            "recipient_id": "917801833884",
        }
    ]

    response = post(client, payload)

    assert response.status_code == 200, "a non-200 makes Meta retry it forever"
    assert response.json()["stored"] == 0
    assert stored(db_session) == []


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"entry": []},
        {"entry": [{"changes": [{"value": {}}]}]},
        {"entry": [{"changes": [{"value": {"messages": [{"from": "917801833884"}]}}]}]},
        {"entry": [{"changes": [{"value": {"messages": ["not an object"]}}]}]},
    ],
)
def test_a_payload_we_cannot_read_is_still_answered(client, signed, db_session, payload):
    """Anything but a 200 and Meta retries, then disables the webhook."""
    response = post(client, payload)

    assert response.status_code == 200
    assert stored(db_session) == []


def test_a_body_that_is_not_json_is_answered_too(client, signed):
    raw = b"not json at all"
    response = client.post(URL, content=raw, headers=sign(raw))

    assert response.status_code == 200
    assert response.json() == {"received": 0, "stored": 0, "duplicates": 0}
