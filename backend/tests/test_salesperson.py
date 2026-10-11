"""The authorization matrix for the field role, enforced server-side.

These tests are the security contract: a salesperson may read only the activities
assigned to them and may write only a completion or a follow-up.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

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
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


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
            "scheduled_at": _soon(),
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
            "scheduled_at": _soon(4),
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
