"""The authorization matrix for the field role, enforced server-side.

These tests are the security contract: a salesperson may read only the activities
assigned to them, and may write only a completion, a follow-up, or an activity
they log themselves - which is always assigned to them.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.services.activities import business_today, day_bounds

CRM_ENDPOINTS = [
    "/api/v1/parties",
    "/api/v1/parties?party_type=CUSTOMER",
    "/api/v1/products",
    "/api/v1/materials",
    "/api/v1/grades",
    "/api/v1/manufacturers",
    "/api/v1/applications",
    "/api/v1/locations",
    "/api/v1/inquiries",
    "/api/v1/notes",
    "/api/v1/activities",
    "/api/v1/dashboard",
    "/api/v1/search?q=a",
    "/api/v1/audit-logs",
    "/api/v1/users",
    "/api/v1/meta/enums",
]


def _soon(hours: float = 3) -> str:
    """Some time away from now - used where only "future" or "past" matters."""
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


def _later_today() -> str:
    """A time still inside today's business day, so "today" endpoints see it.

    A plain ``now + 3h`` slips into tomorrow when the suite runs in the evening,
    which made the scoping tests fail for reasons that had nothing to do with
    scoping.
    """
    now = datetime.now(UTC)
    _, end_of_day = day_bounds(business_today())
    latest = end_of_day - timedelta(minutes=1)
    return min(now + timedelta(hours=3), max(latest, now + timedelta(seconds=30))).isoformat()


@pytest.fixture
def visit_location(client, auth):
    return client.post(
        "/api/v1/locations",
        json={
            "label": "ABC Pipes Factory",
            "address_line_1": "Shapar Veraval GIDC",
            "city": "Rajkot",
            "state": "Gujarat",
            "pincode": "360024",
            "latitude": "22.1736",
            "longitude": "70.8697",
        },
        headers=auth,
    ).json()


@pytest.fixture
def assigned_visit(client, auth, parties, salesperson, visit_location):
    """A VISIT that the admin assigned to our salesperson."""
    response = client.post(
        "/api/v1/activities",
        json={
            "customer_id": parties["customer"],
            "activity_type": "VISIT",
            "scheduled_at": _later_today(),
            "subject": "Visit ABC Pipes factory",
            "note": "Discuss the monthly PVC requirement.",
            "assigned_salesperson_id": salesperson.id,
            "location_id": visit_location["id"],
        },
        headers=auth,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def other_visit(client, auth, parties, other_salesperson, visit_location):
    """An activity belonging to a different salesperson."""
    return client.post(
        "/api/v1/activities",
        json={
            "customer_id": parties["other_customer"],
            "activity_type": "CALL",
            "scheduled_at": _later_today(),
            "assigned_salesperson_id": other_salesperson.id,
        },
        headers=auth,
    ).json()


# --------------------------------------------------------------------------- #
# Read restrictions
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", CRM_ENDPOINTS)
def test_salesperson_cannot_reach_any_crm_endpoint(client, sales_auth, path):
    response = client.get(path, headers=sales_auth)
    assert response.status_code == 403, f"{path} leaked to a salesperson"
    assert response.json()["error"]["code"] == "forbidden"


def test_salesperson_cannot_read_a_customer_record_directly(client, sales_auth, parties):
    assert (
        client.get(f"/api/v1/parties/{parties['customer']}", headers=sales_auth).status_code == 403
    )
    assert (
        client.get(
            f"/api/v1/parties/{parties['customer']}/overview", headers=sales_auth
        ).status_code
        == 403
    )


def test_salesperson_cannot_write_crm_data(client, sales_auth, parties, masters):
    forbidden_writes = [
        ("/api/v1/parties", {"name": "Hacked Co", "party_type": "CUSTOMER"}),
        ("/api/v1/materials", {"name": "Hacked"}),
        (
            "/api/v1/products",
            {
                "material_id": masters["material_id"],
                "grade_id": masters["grade_id"],
                "manufacturer_id": masters["manufacturer_id"],
            },
        ),
        (
            "/api/v1/inquiries",
            {
                "inquiry_type": "CUSTOMER",
                "customer": {
                    "customer_id": parties["customer"],
                    "product_id": masters["product_id"],
                    "quantity": "5",
                },
            },
        ),
        (
            "/api/v1/parties/prospects",
            {"party_type": "CUSTOMER", "name": "Field Lead", "phone": "+91 90000 00003"},
        ),
        ("/api/v1/notes", {"party_id": parties["customer"], "note": "x"}),
        (
            "/api/v1/activities",
            {"customer_id": parties["customer"], "activity_type": "CALL", "scheduled_at": _soon()},
        ),
    ]
    for path, body in forbidden_writes:
        assert client.post(path, json=body, headers=sales_auth).status_code == 403, path


def test_salesperson_sees_only_own_activities(client, sales_auth, assigned_visit, other_visit):
    today = client.get("/api/v1/salesperson/activities/today", headers=sales_auth).json()
    ids = {item["id"] for item in today}
    assert assigned_visit["id"] in ids
    assert other_visit["id"] not in ids

    visits = client.get("/api/v1/salesperson/visits/today", headers=sales_auth).json()
    assert [item["id"] for item in visits] == [assigned_visit["id"]]


def test_salesperson_cannot_open_another_persons_activity(client, sales_auth, other_visit):
    response = client.get(f"/api/v1/salesperson/activities/{other_visit['id']}", headers=sales_auth)
    # 404, not 403: the API must not confirm that the activity exists.
    assert response.status_code == 404


def test_salesperson_cannot_complete_another_persons_activity(
    client, sales_auth, other_sales_auth, other_visit
):
    response = client.post(
        f"/api/v1/salesperson/activities/{other_visit['id']}/complete",
        json={"outcome_code": "COMPLETED", "completion_note": "not mine"},
        headers=sales_auth,
    )
    assert response.status_code == 404
    # The rightful owner can.
    ok = client.post(
        f"/api/v1/salesperson/activities/{other_visit['id']}/complete",
        json={"outcome_code": "COMPLETED", "completion_note": "done"},
        headers=other_sales_auth,
    )
    assert ok.status_code == 200


def test_salesperson_cannot_probe_unknown_ids(client, sales_auth):
    assert (
        client.get("/api/v1/salesperson/activities/999999", headers=sales_auth).status_code == 404
    )
    assert (
        client.post(
            "/api/v1/salesperson/activities/999999/complete",
            json={"outcome_code": "COMPLETED", "completion_note": "x"},
            headers=sales_auth,
        ).status_code
        == 404
    )


def test_activity_payload_exposes_only_what_is_needed(client, sales_auth, assigned_visit):
    body = client.get(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}", headers=sales_auth
    ).json()
    assert set(body["customer"]) == {"name", "contact_person", "phone"}
    # No ids that could be used to probe the CRM, no CRM collections.
    assert "customer_id" not in body
    assert "gst_number" not in str(body)
    for leaked in ("products", "inquiries", "notes", "party_type"):
        assert leaked not in body


def test_visit_carries_a_google_maps_link(client, sales_auth, assigned_visit):
    body = client.get(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}", headers=sales_auth
    ).json()
    assert body["is_visit"] is True
    location = body["location"]
    assert location["city"] == "Rajkot"
    # Coordinates are preferred over the address when known.
    assert "destination=22.1736,70.8697" in location["maps_url"]  # padding trimmed
    assert location["maps_url"].startswith("https://www.google.com/maps/dir/?api=1")


def test_maps_link_falls_back_to_the_address(client, auth, sales_auth, parties, salesperson):
    location = client.post(
        "/api/v1/locations",
        json={"label": "Plant", "city": "Surat", "state": "Gujarat"},
        headers=auth,
    ).json()
    activity = client.post(
        "/api/v1/activities",
        json={
            "customer_id": parties["customer"],
            "activity_type": "VISIT",
            "scheduled_at": _soon(),
            "assigned_salesperson_id": salesperson.id,
            "location_id": location["id"],
        },
        headers=auth,
    ).json()
    body = client.get(f"/api/v1/salesperson/activities/{activity['id']}", headers=sales_auth).json()
    assert "destination=Plant%2C+Surat%2C+Gujarat" in body["location"]["maps_url"]


# --------------------------------------------------------------------------- #
# Write permissions
# --------------------------------------------------------------------------- #
def test_salesperson_can_complete_own_activity(client, sales_auth, auth, assigned_visit):
    response = client.post(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}/complete",
        json={
            "outcome_code": "FOLLOW_UP_REQUIRED",
            "completion_note": "Customer wants a quotation for 30 MT.",
        },
        headers=sales_auth,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["already_completed"] is False
    assert body["activity"]["status"] == "COMPLETED"
    assert body["activity"]["outcome_code"] == "FOLLOW_UP_REQUIRED"
    assert body["activity"]["completion_note"].startswith("Customer wants")

    # The admin sees the full record, including who reported it.
    admin_view = client.get(f"/api/v1/activities/{assigned_visit['id']}", headers=auth).json()
    assert admin_view["status"] == "COMPLETED"
    assert admin_view["outcome_code"] == "FOLLOW_UP_REQUIRED"
    assert admin_view["completer"]["name"] == "Rahul Field"
    assert admin_view["completed_at"] is not None


def test_completion_is_idempotent_for_retries(client, sales_auth, assigned_visit):
    payload = {
        "outcome_code": "COMPLETED",
        "completion_note": "Visited.",
        "client_token": "abc-123",
    }
    first = client.post(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}/complete",
        json=payload,
        headers=sales_auth,
    )
    second = client.post(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}/complete",
        json=payload,
        headers=sales_auth,
    )
    assert first.json()["already_completed"] is False
    assert second.status_code == 200
    assert second.json()["already_completed"] is True


def test_completion_requires_a_note(client, sales_auth, assigned_visit):
    response = client.post(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}/complete",
        json={"outcome_code": "COMPLETED", "completion_note": ""},
        headers=sales_auth,
    )
    assert response.status_code == 422


def test_salesperson_cannot_complete_a_cancelled_activity(client, auth, sales_auth, assigned_visit):
    client.patch(
        f"/api/v1/activities/{assigned_visit['id']}", json={"status": "CANCELLED"}, headers=auth
    )
    response = client.post(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}/complete",
        json={"outcome_code": "COMPLETED", "completion_note": "late"},
        headers=sales_auth,
    )
    assert response.status_code == 409


def test_follow_up_inherits_customer_assignee_and_parent(
    client, sales_auth, auth, assigned_visit, salesperson, parties
):
    client.post(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}/complete",
        json={"outcome_code": "FOLLOW_UP_REQUIRED", "completion_note": "Wants a quote."},
        headers=sales_auth,
    )
    response = client.post(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}/follow-up",
        json={
            "activity_type": "CALL",
            "scheduled_at": _soon(24 * 3),
            "note": "Call about the October requirement.",
        },
        headers=sales_auth,
    )
    assert response.status_code == 201, response.text
    follow_up = response.json()["activity"]
    assert follow_up["parent_activity_id"] == assigned_visit["id"]
    assert follow_up["status"] == "SCHEDULED"

    # Server-derived fields, checked through the admin view.
    admin_view = client.get(f"/api/v1/activities/{follow_up['id']}", headers=auth).json()
    assert admin_view["party_id"] == parties["customer"]
    assert admin_view["assigned_salesperson_id"] == salesperson.id
    assert admin_view["created_by"] == salesperson.id


def test_follow_up_ignores_any_attempt_to_reassign_or_change_customer(
    client, sales_auth, auth, assigned_visit, other_salesperson, parties, salesperson
):
    response = client.post(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}/follow-up",
        json={
            "activity_type": "CALL",
            "scheduled_at": _soon(24),
            "note": "Mine",
            # These are not part of the schema and must have no effect.
            "assigned_salesperson_id": other_salesperson.id,
            "customer_id": parties["other_customer"],
        },
        headers=sales_auth,
    )
    assert response.status_code == 201
    created = client.get(
        f"/api/v1/activities/{response.json()['activity']['id']}", headers=auth
    ).json()
    assert created["assigned_salesperson_id"] == salesperson.id
    assert created["party_id"] == parties["customer"]


def test_follow_up_type_is_restricted(client, sales_auth, assigned_visit):
    response = client.post(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}/follow-up",
        json={"activity_type": "MEETING", "scheduled_at": _soon(24)},
        headers=sales_auth,
    )
    assert response.status_code == 422
    assert "only schedule" in response.json()["error"]["message"]


def test_follow_up_must_be_in_the_future(client, sales_auth, assigned_visit):
    response = client.post(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}/follow-up",
        json={"activity_type": "CALL", "scheduled_at": _soon(-48)},
        headers=sales_auth,
    )
    assert response.status_code == 422


def test_salesperson_cannot_patch_or_assign_activities(
    client, sales_auth, assigned_visit, other_salesperson
):
    assert (
        client.patch(
            f"/api/v1/activities/{assigned_visit['id']}",
            json={"scheduled_at": _soon(48)},
            headers=sales_auth,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/activities/{assigned_visit['id']}/assign",
            json={"assigned_salesperson_id": other_salesperson.id},
            headers=sales_auth,
        ).status_code
        == 403
    )


def test_salesperson_endpoints_reject_staff_accounts(client, auth, desk_auth):
    for headers in (auth, desk_auth):
        response = client.get("/api/v1/salesperson/dashboard", headers=headers)
        assert response.status_code == 403
        assert "salesperson" in response.json()["error"]["message"].lower()


def test_dashboard_and_history_are_scoped(client, sales_auth, assigned_visit, other_visit):
    dashboard = client.get("/api/v1/salesperson/dashboard", headers=sales_auth).json()
    assert dashboard["profile"]["name"] == "Rahul Field"
    assert dashboard["counts"]["today_total"] == 1
    assert dashboard["counts"]["today_visits"] == 1
    assert dashboard["next_activity"]["id"] == assigned_visit["id"]

    client.post(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}/complete",
        json={"outcome_code": "COMPLETED", "completion_note": "Done."},
        headers=sales_auth,
    )
    history = client.get("/api/v1/salesperson/activities/history", headers=sales_auth).json()
    assert [item["id"] for item in history] == [assigned_visit["id"]]


# --------------------------------------------------------------------------- #
# Admin side of assignment
# --------------------------------------------------------------------------- #
def test_admin_can_assign_and_reassign(
    client, auth, assigned_visit, salesperson, other_salesperson
):
    reassigned = client.post(
        f"/api/v1/activities/{assigned_visit['id']}/assign",
        json={"assigned_salesperson_id": other_salesperson.id},
        headers=auth,
    )
    assert reassigned.status_code == 200
    assert reassigned.json()["assigned_salesperson_id"] == other_salesperson.id

    cleared = client.post(
        f"/api/v1/activities/{assigned_visit['id']}/assign",
        json={"assigned_salesperson_id": None},
        headers=auth,
    )
    assert cleared.json()["assigned_salesperson_id"] is None
    assert salesperson.id  # fixture used


def test_only_salesperson_accounts_can_be_assigned(client, auth, parties, admin, plain_user):
    for user in (admin, plain_user):
        response = client.post(
            "/api/v1/activities",
            json={
                "customer_id": parties["customer"],
                "activity_type": "CALL",
                "scheduled_at": _soon(),
                "assigned_salesperson_id": user.id,
            },
            headers=auth,
        )
        assert response.status_code == 422
        assert "SALESPERSON" in response.json()["error"]["message"]


def test_inactive_salesperson_cannot_be_assigned(client, auth, parties, salesperson):
    client.patch(f"/api/v1/users/{salesperson.id}", json={"status": "INACTIVE"}, headers=auth)
    response = client.post(
        "/api/v1/activities",
        json={
            "customer_id": parties["customer"],
            "activity_type": "CALL",
            "scheduled_at": _soon(),
            "assigned_salesperson_id": salesperson.id,
        },
        headers=auth,
    )
    assert response.status_code == 422
    assert "inactive" in response.json()["error"]["message"]


def test_visit_requires_a_location(client, auth, parties, salesperson):
    response = client.post(
        "/api/v1/activities",
        json={
            "customer_id": parties["customer"],
            "activity_type": "VISIT",
            "scheduled_at": _soon(),
            "assigned_salesperson_id": salesperson.id,
        },
        headers=auth,
    )
    assert response.status_code == 422
    assert "location" in response.json()["error"]["message"].lower()


def test_visit_location_is_snapshotted(client, auth, sales_auth, assigned_visit, visit_location):
    client.patch(
        f"/api/v1/locations/{visit_location['id']}",
        json={"label": "Renamed warehouse", "city": "Jamnagar"},
        headers=auth,
    )
    body = client.get(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}", headers=sales_auth
    ).json()
    # History keeps the address as it was when the visit was scheduled.
    assert body["location"]["city"] == "Rajkot"
    assert body["location"]["label"] == "ABC Pipes Factory"


def test_admin_can_filter_activities_by_salesperson(
    client, auth, assigned_visit, other_visit, salesperson
):
    rows = client.get(
        f"/api/v1/activities?assigned_salesperson_id={salesperson.id}", headers=auth
    ).json()
    assert [item["id"] for item in rows["items"]] == [assigned_visit["id"]]

    unassigned = client.get("/api/v1/activities?unassigned_only=true", headers=auth).json()
    assert assigned_visit["id"] not in {item["id"] for item in unassigned["items"]}
    assert other_visit["id"] not in {item["id"] for item in unassigned["items"]}


def test_workload_and_conflict_warning(client, auth, assigned_visit, salesperson):
    workload = client.get("/api/v1/activities/salespeople/workload", headers=auth).json()
    row = next(item for item in workload if item["id"] == salesperson.id)
    assert row["today_total"] == 1
    assert row["today_pending"] == 1

    conflict = client.get(
        "/api/v1/activities/conflicts/check",
        params={
            "salesperson_id": salesperson.id,
            "scheduled_at": assigned_visit["scheduled_at"],
        },
        headers=auth,
    ).json()
    assert conflict["has_conflict"] is True
    assert conflict["conflicts"][0]["activity_id"] == assigned_visit["id"]

    clear = client.get(
        "/api/v1/activities/conflicts/check",
        params={"salesperson_id": salesperson.id, "scheduled_at": _soon(48)},
        headers=auth,
    ).json()
    assert clear["has_conflict"] is False


def test_admin_sees_assignment_in_the_calendar(client, auth, assigned_visit, salesperson):
    day = assigned_visit["scheduled_at"][:10]
    rows = client.get(
        f"/api/v1/activities/calendar?date_from={day}&date_to={day}", headers=auth
    ).json()
    row = next(item for item in rows if item["id"] == assigned_visit["id"])
    assert row["assigned_salesperson"]["name"] == "Rahul Field"


def test_salesperson_can_start_own_activity(client, sales_auth, assigned_visit):
    response = client.post(
        f"/api/v1/salesperson/activities/{assigned_visit['id']}/start", headers=sales_auth
    )
    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS"
    # Starting twice is harmless.
    assert (
        client.post(
            f"/api/v1/salesperson/activities/{assigned_visit['id']}/start", headers=sales_auth
        ).status_code
        == 200
    )


def test_salesperson_cannot_start_another_persons_activity(client, sales_auth, other_visit):
    response = client.post(
        f"/api/v1/salesperson/activities/{other_visit['id']}/start", headers=sales_auth
    )
    assert response.status_code == 404


def test_salesperson_can_change_own_password(client, sales_auth, salesperson):
    bad = client.post(
        "/api/v1/salesperson/change-password",
        json={"current_password": "wrong", "new_password": "newpass123"},
        headers=sales_auth,
    )
    assert bad.status_code == 422

    ok = client.post(
        "/api/v1/salesperson/change-password",
        json={"current_password": "rahul123", "new_password": "newpass123"},
        headers=sales_auth,
    )
    assert ok.status_code == 200
    relogin = client.post(
        "/api/v1/auth/login",
        json={"email": salesperson.email, "password": "newpass123"},
    )
    assert relogin.status_code == 200


def test_salesperson_cannot_change_other_users_password(client, sales_auth, admin):
    response = client.patch(
        f"/api/v1/users/{admin.id}", json={"password": "hacked123"}, headers=sales_auth
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Logging an activity from the field
# --------------------------------------------------------------------------- #
def _ago(hours: float = 1) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat()


def _log(client, sales_auth, **body):
    payload = {"activity_type": "CALL", "done": True, "outcome_code": "COMPLETED", "note": "x"}
    payload.update(body)
    return client.post("/api/v1/salesperson/activities", json=payload, headers=sales_auth)


def test_a_cold_call_to_someone_new_creates_a_field_prospect(client, auth, sales_auth, salesperson):
    response = _log(
        client,
        sales_auth,
        new_contact={
            "name": "Rajkot Polymers",
            "phone": "+91 90011 22334",
            "party_type": "SUPPLIER",
        },
        outcome_code="CUSTOMER_INTERESTED",
        note="Has 20 MT K-67, wants to quote.",
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["new_contact_created"] is True
    activity = body["activity"]
    assert activity["self_logged"] is True
    assert activity["status"] == "COMPLETED"
    assert activity["outcome_code"] == "CUSTOMER_INTERESTED"
    assert activity["completion_note"] == "Has 20 MT K-67, wants to quote."
    # The payload still exposes no party id.
    assert "id" not in activity["customer"]

    # The office sees it: assigned to and created by the salesperson, and the
    # new contact is a FIELD prospect of the right type.
    rows = client.get(
        "/api/v1/activities", params={"assigned_salesperson_id": salesperson.id}, headers=auth
    ).json()["items"]
    logged = next(row for row in rows if row["id"] == activity["id"])
    assert logged["created_by"] == salesperson.id
    party = client.get(f"/api/v1/parties/{logged['party_id']}", headers=auth).json()
    assert (party["stage"], party["source"], party["party_type"]) == (
        "PROSPECT",
        "FIELD",
        "SUPPLIER",
    )


def test_a_retried_submission_is_logged_once(client, sales_auth):
    body = {"new_contact": {"name": "Retry Co"}, "client_token": "same-token-1"}
    first = _log(client, sales_auth, **body)
    second = _log(client, sales_auth, **body)
    assert first.status_code == second.status_code == 201
    assert second.json()["duplicate"] is True
    assert second.json()["activity"]["id"] == first.json()["activity"]["id"]
    assert second.json()["new_contact_created"] is False


def test_tokens_are_per_salesperson(client, sales_auth, other_sales_auth):
    """Another rep reusing a token string must not see the first rep's activity."""
    mine = _log(client, sales_auth, new_contact={"name": "A Co"}, client_token="shared")
    theirs = _log(client, other_sales_auth, new_contact={"name": "B Co"}, client_token="shared")
    assert theirs.json()["duplicate"] is False
    assert theirs.json()["activity"]["id"] != mine.json()["activity"]["id"]


def test_contacts_are_only_parties_the_salesperson_has_worked_with(
    client, sales_auth, assigned_visit, other_visit
):
    contacts = client.get("/api/v1/salesperson/contacts", headers=sales_auth).json()
    assert [contact["ref"] for contact in contacts] == [assigned_visit["id"]]
    assert "id" not in contacts[0]
    # Someone else's customer never appears, even by name search.
    other_name = other_visit["party"]["name"]
    found = client.get(
        "/api/v1/salesperson/contacts", params={"q": other_name}, headers=sales_auth
    ).json()
    if other_name != assigned_visit["party"]["name"]:
        assert found == []


def test_a_known_contact_is_addressed_through_an_own_activity(client, sales_auth, assigned_visit):
    response = _log(client, sales_auth, contact_ref=assigned_visit["id"], note="Checked in.")
    assert response.status_code == 201, response.text
    assert response.json()["activity"]["customer"]["name"] == assigned_visit["party"]["name"]
    assert response.json()["new_contact_created"] is False


def test_another_persons_activity_cannot_be_used_as_a_contact(client, sales_auth, other_visit):
    response = _log(client, sales_auth, contact_ref=other_visit["id"])
    assert response.status_code == 404


def test_the_assignee_is_always_the_signed_in_salesperson(
    client, auth, sales_auth, salesperson, other_salesperson
):
    """Extra fields trying to reassign the activity are ignored."""
    response = _log(
        client,
        sales_auth,
        new_contact={"name": "Sneaky Co"},
        assigned_salesperson_id=other_salesperson.id,
        salesperson_id=other_salesperson.id,
    )
    assert response.status_code == 201
    activity_id = response.json()["activity"]["id"]
    row = client.get(f"/api/v1/activities/{activity_id}", headers=auth).json()
    assert row["assigned_salesperson_id"] == salesperson.id


def test_a_done_activity_needs_an_outcome_and_a_note(client, sales_auth):
    assert _log(client, sales_auth, new_contact={"name": "X"}, outcome_code=None).status_code == 422
    assert _log(client, sales_auth, new_contact={"name": "X"}, note="  ").status_code == 422


def test_done_cannot_be_in_the_future_or_older_than_a_week(client, sales_auth):
    future = _log(client, sales_auth, new_contact={"name": "X"}, at=_soon(3))
    old = _log(client, sales_auth, new_contact={"name": "X"}, at=_ago(24 * 8))
    earlier_today = _log(client, sales_auth, new_contact={"name": "X"}, at=_ago(2))
    assert future.status_code == 422
    assert old.status_code == 422
    assert earlier_today.status_code == 201


def test_a_planned_activity_needs_a_future_time(client, sales_auth, assigned_visit):
    planned = _log(
        client, sales_auth, contact_ref=assigned_visit["id"], done=False, at=_soon(24), note="Prep"
    )
    assert planned.status_code == 201, planned.text
    assert planned.json()["activity"]["status"] == "SCHEDULED"
    assert planned.json()["activity"]["purpose"] == "Prep"
    past = _log(client, sales_auth, contact_ref=assigned_visit["id"], done=False, at=_ago(2))
    missing = _log(client, sales_auth, contact_ref=assigned_visit["id"], done=False)
    assert past.status_code == missing.status_code == 422


def test_a_cold_visit_needs_somewhere_to_be(client, auth, sales_auth):
    nowhere = _log(client, sales_auth, activity_type="VISIT", new_contact={"name": "Shop"})
    assert nowhere.status_code == 422

    typed = _log(
        client,
        sales_auth,
        activity_type="VISIT",
        new_contact={"name": "Shop"},
        place="Opposite bus stand, Gondal Road",
    )
    assert typed.status_code == 201, typed.text
    assert typed.json()["activity"]["location"]["formatted"] == "Opposite bus stand, Gondal Road"

    pinned = _log(
        client,
        sales_auth,
        activity_type="VISIT",
        new_contact={"name": "Shop 2"},
        latitude="21.96",
        longitude="70.80",
    )
    assert pinned.status_code == 201, pinned.text
    assert pinned.json()["activity"]["location"]["maps_url"].endswith("21.96,70.8")

    # The office sees where it happened too.
    office = client.get(f"/api/v1/activities/{pinned.json()['activity']['id']}", headers=auth)
    snapshot = office.json()["location_snapshot"]
    assert (snapshot["latitude"], snapshot["longitude"]) == ("21.96", "70.80")


def test_logged_types_are_restricted(client, sales_auth):
    assert (
        _log(client, sales_auth, activity_type="MEETING", new_contact={"name": "X"}).status_code
        == 422
    )


def test_exactly_one_way_of_saying_who(client, sales_auth, assigned_visit):
    neither = _log(client, sales_auth)
    both = _log(client, sales_auth, contact_ref=assigned_visit["id"], new_contact={"name": "X"})
    assert neither.status_code == both.status_code == 422


def test_staff_cannot_use_the_field_logging_endpoints(client, auth):
    assert _log(client, auth, new_contact={"name": "X"}).status_code == 403
    assert client.get("/api/v1/salesperson/contacts", headers=auth).status_code == 403
    assert client.get("/api/v1/salesperson/stats", headers=auth).status_code == 403


def test_stats_count_only_own_work(client, sales_auth, other_sales_auth):
    _log(client, sales_auth, new_contact={"name": "Mine 1"})
    _log(client, sales_auth, activity_type="VISIT", new_contact={"name": "Mine 2"}, place="Here")
    _log(client, other_sales_auth, new_contact={"name": "Theirs"})

    stats = client.get("/api/v1/salesperson/stats", headers=sales_auth).json()
    assert stats["completed_7d"] == 2
    assert stats["calls_7d"] == 1
    assert stats["visits_7d"] == 1
    assert stats["self_logged_7d"] == 2
    assert stats["new_contacts_7d"] == 2
    assert len(stats["days"]) == 7
    assert stats["days"][-1]["completed"] == 2


def test_office_assigned_work_is_not_marked_self_logged(client, sales_auth, assigned_visit):
    row = client.get(f"/api/v1/salesperson/activities/{assigned_visit['id']}", headers=sales_auth)
    assert row.json()["self_logged"] is False
