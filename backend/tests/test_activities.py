"""Activity rules: customers only, completion with outcome, follow-up chains."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _soon(hours: int = 4) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


def _schedule(client, auth, customer_id, **overrides):
    payload = {
        "customer_id": customer_id,
        "activity_type": "CALL",
        "subject": "Confirm PVC requirement",
        "scheduled_at": _soon(),
        "note": "Follow up regarding the PVC requirement.",
        **overrides,
    }
    return client.post("/api/v1/activities", json=payload, headers=auth)


def test_scheduled_activity_is_just_an_activity(client, auth, parties):
    response = _schedule(client, auth, parties["customer"])
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "SCHEDULED"
    assert body["completed_at"] is None
    assert body["note"]


def test_activities_work_for_any_party_type(client, auth, parties):
    """Cold supplier calls and transporter meetings are real work - allow them."""
    for key in ("supplier", "transporter"):
        response = _schedule(client, auth, parties[key])
        assert response.status_code == 201, response.text
        assert response.json()["party_id"] == parties[key]


def test_activity_rejects_an_inactive_party(client, auth, parties):
    client.patch(
        f"/api/v1/parties/{parties['customer']}", json={"status": "INACTIVE"}, headers=auth
    )
    response = _schedule(client, auth, parties["customer"])
    assert response.status_code == 422
    assert "inactive" in response.json()["error"]["message"]


def test_scheduled_activity_requires_a_datetime(client, auth, parties):
    response = client.post(
        "/api/v1/activities",
        json={"customer_id": parties["customer"], "activity_type": "CALL"},
        headers=auth,
    )
    assert response.status_code == 422


def test_complete_records_outcome_and_creates_follow_up_chain(client, auth, parties):
    activity = _schedule(client, auth, parties["customer"]).json()
    response = client.post(
        f"/api/v1/activities/{activity['id']}/complete",
        json={
            "outcome": "Customer expects the requirement next week.",
            "follow_up": {
                "activity_type": "CALL",
                "scheduled_at": _soon(hours=24 * 7),
                "note": "Check the PVC requirement again.",
            },
        },
        headers=auth,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["activity"]["status"] == "COMPLETED"
    assert body["activity"]["completed_at"] is not None
    assert body["activity"]["note"] != body["activity"]["outcome"]
    follow_up = body["follow_up"]
    assert follow_up["parent_activity_id"] == activity["id"]
    assert follow_up["status"] == "SCHEDULED"

    chain = client.get(f"/api/v1/activities/{activity['id']}", headers=auth).json()
    assert [row["id"] for row in chain["follow_ups"]] == [follow_up["id"]]


def test_completed_activity_cannot_be_completed_or_edited_again(client, auth, parties):
    activity = _schedule(client, auth, parties["customer"]).json()
    client.post(
        f"/api/v1/activities/{activity['id']}/complete",
        json={"outcome": "Spoke to the customer."},
        headers=auth,
    )
    again = client.post(
        f"/api/v1/activities/{activity['id']}/complete",
        json={"outcome": "again"},
        headers=auth,
    )
    assert again.status_code == 409
    edit = client.patch(
        f"/api/v1/activities/{activity['id']}", json={"subject": "new"}, headers=auth
    )
    assert edit.status_code == 409


def test_completion_must_go_through_the_complete_endpoint(client, auth, parties):
    activity = _schedule(client, auth, parties["customer"]).json()
    response = client.patch(
        f"/api/v1/activities/{activity['id']}", json={"status": "COMPLETED"}, headers=auth
    )
    assert response.status_code == 422
    assert "complete" in response.json()["error"]["message"]


def test_follow_up_must_belong_to_the_same_customer(client, auth, parties):
    activity = _schedule(client, auth, parties["customer"]).json()
    response = _schedule(client, auth, parties["other_customer"], parent_activity_id=activity["id"])
    assert response.status_code == 422


def test_activity_scopes(client, auth, parties):
    _schedule(client, auth, parties["customer"], scheduled_at=_soon(hours=2))
    _schedule(client, auth, parties["customer"], scheduled_at=_soon(hours=24 * 9))
    overdue = client.post(
        "/api/v1/activities",
        json={
            "customer_id": parties["customer"],
            "activity_type": "CALL",
            "scheduled_at": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
        },
        headers=auth,
    )
    assert overdue.status_code == 201

    upcoming = client.get("/api/v1/activities?scope=upcoming", headers=auth).json()
    assert upcoming["total"] == 2
    overdue_rows = client.get("/api/v1/activities?scope=overdue", headers=auth).json()
    assert overdue_rows["total"] == 1
    history = client.get("/api/v1/activities?scope=history", headers=auth).json()
    assert history["total"] == 0
    bad = client.get("/api/v1/activities?scope=nonsense", headers=auth)
    assert bad.status_code == 422


def test_log_a_past_activity_in_one_call(client, auth, parties):
    response = client.post(
        "/api/v1/activities",
        json={
            "customer_id": parties["customer"],
            "activity_type": "WHATSAPP",
            "status": "COMPLETED",
            "completed_at": datetime.now(UTC).isoformat(),
            "note": "Sent today's PVC market price update.",
            "outcome": "Customer acknowledged.",
        },
        headers=auth,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "COMPLETED"
