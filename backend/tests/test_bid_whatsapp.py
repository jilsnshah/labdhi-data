"""Opening a bid tells the room, over WhatsApp.

Each participant gets their own link, because the link *is* their identity on
the portal. Sending must never decide whether a bid opens: the desk pressed
Open, so the bid opens, and whatever the phone network did is recorded beside
each participant for the desk to see and retry.

An invitation goes as plain text, which is what a trader expects to read on
their phone. WhatsApp delivers it to anyone who has written to the business
number in the last 24 hours; for anyone who has not it accepts the call, hands
back a message id, and never delivers - verified against a real handset in both
directions. Hence the line in the message asking them to reply, and the
``template_mode`` fixture for the desks that would rather not depend on it.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def reachable(client, auth, parties):
    """Our two test handsets, on the transporters Meta will deliver to."""
    numbers = {parties["transporter"]: "7801833884"}
    second = client.post(
        "/api/v1/parties",
        json={"name": "Second Carrier", "party_type": "TRANSPORTER", "phone": "9925552909"},
        headers=auth,
    ).json()
    numbers[second["id"]] = "9925552909"
    client.patch(
        f"/api/v1/parties/{parties['transporter']}",
        json={"phone": "7801833884"},
        headers=auth,
    )
    return numbers


def make_bid(client, auth, locations, party_ids):
    return client.post(
        "/api/v1/bids",
        json={
            "bid_type": "TRANSPORT",
            "quantity": "20",
            "pickup_location_id": locations["pickup_id"],
            "delivery_location_id": locations["delivery_id"],
            "party_ids": list(party_ids),
        },
        headers=auth,
    ).json()


def test_opening_a_bid_messages_everyone_with_a_number(
    client, auth, locations, reachable, whatsapp_outbox
):
    bid = make_bid(client, auth, locations, reachable)
    assert whatsapp_outbox.sent == [], "a draft tells nobody"

    client.post(f"/api/v1/bids/{bid['id']}/publish", headers=auth)

    assert len(whatsapp_outbox.sent) == 2
    assert {to for to, _ in whatsapp_outbox.sent} == {"917801833884", "919925552909"}


def test_each_participant_is_sent_their_own_link(
    client, auth, locations, reachable, whatsapp_outbox
):
    """The link is the identity; sending the wrong one would hand over a seat."""
    bid = make_bid(client, auth, locations, reachable)
    client.post(f"/api/v1/bids/{bid['id']}/publish", headers=auth)

    rows = client.get(f"/api/v1/bids/{bid['id']}/participants", headers=auth).json()["items"]
    by_phone = {row["party"]["phone"].replace(" ", ""): row["bid_link"] for row in rows}
    links = []
    for to, body in whatsapp_outbox.sent:
        link = next(line for line in body.splitlines() if line.startswith("http"))
        assert link == by_phone[to[2:]], "each number got the link belonging to that party"
        links.append(link)
    assert len(set(links)) == 2, "no two participants share a link"


def test_what_the_message_actually_says(client, auth, locations, reachable, whatsapp_outbox):
    """Who it is for, what is on offer, their own link - and the ask to reply."""
    bid = make_bid(client, auth, locations, reachable)
    client.post(f"/api/v1/bids/{bid['id']}/publish", headers=auth)

    _to, body = whatsapp_outbox.sent[0]
    assert body.startswith("Hello ")
    assert "Jay Transport" in body or "Second Carrier" in body
    assert "20 MT" in body
    assert "/portal/" in body
    assert "revise your offer" in body
    assert "Reply to this message" in body, "the one line that opens the next window"


def test_a_participant_without_a_number_is_recorded_not_messaged(
    client, auth, locations, parties, reachable, whatsapp_outbox
):
    silent = client.post(
        "/api/v1/parties",
        json={"name": "No Phone Carriers", "party_type": "TRANSPORTER"},
        headers=auth,
    ).json()
    bid = make_bid(client, auth, locations, [*reachable, silent["id"]])
    client.post(f"/api/v1/bids/{bid['id']}/publish", headers=auth)

    assert len(whatsapp_outbox.sent) == 2, "the one without a number is skipped"
    rows = client.get(f"/api/v1/bids/{bid['id']}/participants", headers=auth).json()["items"]
    row = next(r for r in rows if r["party"]["id"] == silent["id"])
    assert row["notify_status"] == "SKIPPED"
    assert "number" in row["notify_error"].lower()


def test_a_refusal_from_meta_does_not_stop_the_bid_opening(
    client, auth, locations, reachable, whatsapp_outbox
):
    """The desk pressed Open. The bid opens, whatever the network says."""
    whatsapp_outbox.fail_with = "131030: recipient not in allowed list"
    bid = make_bid(client, auth, locations, reachable)

    opened = client.post(f"/api/v1/bids/{bid['id']}/publish", headers=auth)

    assert opened.status_code == 200
    assert opened.json()["status"] == "OPEN"
    rows = client.get(f"/api/v1/bids/{bid['id']}/participants", headers=auth).json()["items"]
    assert all(row["notify_status"] == "FAILED" for row in rows)
    assert all("131030" in row["notify_error"] for row in rows)


def test_the_template_carries_the_same_facts(
    client, auth, locations, reachable, whatsapp_outbox, template_mode
):
    """Switched to template mode: no window to depend on, same three facts."""
    bid = make_bid(client, auth, locations, reachable)
    client.post(f"/api/v1/bids/{bid['id']}/publish", headers=auth)

    assert whatsapp_outbox.sent == []
    assert len(whatsapp_outbox.templates) == 2
    to, name, params = whatsapp_outbox.templates[0]
    assert name == "bid_invitation"
    assert params[0] in {"Jay Transport", "Second Carrier"}
    assert params[1] == "20 MT"
    assert "/portal/" in params[2]


def test_a_closed_service_window_falls_back_to_the_template(
    client, auth, locations, reachable, whatsapp_outbox, monkeypatch
):
    """131047 is Meta admitting the window is shut - the one detectable case."""
    original = whatsapp_outbox.post

    def refuse_text(payload):
        if payload["type"] == "text":
            from app.services.whatsapp import WhatsAppError

            raise WhatsAppError("131047: Message failed to send, 24 hours have passed")
        return original(payload)

    monkeypatch.setattr(whatsapp_outbox, "post", refuse_text)

    bid = make_bid(client, auth, locations, reachable)
    client.post(f"/api/v1/bids/{bid['id']}/publish", headers=auth)

    assert whatsapp_outbox.sent == [], "no text got through"
    assert len(whatsapp_outbox.templates) == 2, "the template carried it instead"
    rows = client.get(f"/api/v1/bids/{bid['id']}/participants", headers=auth).json()["items"]
    assert all(row["notify_status"] == "SENT" for row in rows)


def test_the_room_is_told_once(client, auth, locations, reachable, whatsapp_outbox):
    """Publishing an open bid again must not message everybody a second time."""
    bid = make_bid(client, auth, locations, reachable)
    client.post(f"/api/v1/bids/{bid['id']}/publish", headers=auth)
    client.post(f"/api/v1/bids/{bid['id']}/publish", headers=auth)

    assert len(whatsapp_outbox.sent) == 2


def test_someone_invited_later_is_told_when_they_are_invited(
    client, auth, locations, parties, reachable, whatsapp_outbox
):
    """A bid already running: the newcomer is messaged, the room is not again."""
    bid = make_bid(client, auth, locations, reachable)
    client.post(f"/api/v1/bids/{bid['id']}/publish", headers=auth)
    whatsapp_outbox.sent.clear()

    latecomer = client.post(
        "/api/v1/parties",
        json={"name": "Late Carrier", "party_type": "TRANSPORTER", "phone": "7801833884"},
        headers=auth,
    ).json()
    client.post(
        f"/api/v1/bids/{bid['id']}/participants",
        json={"party_ids": [latecomer["id"]]},
        headers=auth,
    )

    assert len(whatsapp_outbox.sent) == 1
    assert "Late Carrier" in whatsapp_outbox.sent[0][1]


def test_inviting_to_a_draft_tells_nobody(
    client, auth, locations, reachable, whatsapp_outbox, parties
):
    make_bid(client, auth, locations, reachable)
    assert whatsapp_outbox.sent == []
    assert whatsapp_outbox.templates == []


def test_the_desk_can_retry_a_failed_message(client, auth, locations, reachable, whatsapp_outbox):
    whatsapp_outbox.fail_with = "131030: recipient not in allowed list"
    bid = make_bid(client, auth, locations, reachable)
    client.post(f"/api/v1/bids/{bid['id']}/publish", headers=auth)

    whatsapp_outbox.fail_with = None
    response = client.post(f"/api/v1/bids/{bid['id']}/notify", headers=auth)

    assert response.status_code == 200
    assert response.json()["sent"] == 2
    rows = client.get(f"/api/v1/bids/{bid['id']}/participants", headers=auth).json()["items"]
    assert all(row["notify_status"] == "SENT" for row in rows)


def test_without_credentials_the_bid_still_opens(
    client, auth, locations, reachable, whatsapp_unconfigured
):
    """How the desk runs until Meta is set up: links are copied by hand."""
    bid = make_bid(client, auth, locations, reachable)
    opened = client.post(f"/api/v1/bids/{bid['id']}/publish", headers=auth)

    assert opened.json()["status"] == "OPEN"
    rows = client.get(f"/api/v1/bids/{bid['id']}/participants", headers=auth).json()["items"]
    assert all(row["notify_status"] == "SKIPPED" for row in rows)
