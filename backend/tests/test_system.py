"""Auth, search, notes, dashboard and audit-log behaviour."""

from __future__ import annotations


def test_endpoints_require_authentication(client):
    for path in ("/api/v1/parties", "/api/v1/inquiries", "/api/v1/dashboard"):
        assert client.get(path).status_code == 401


def test_login_rejects_bad_credentials(client, admin):
    response = client.post("/api/v1/auth/login", json={"email": admin.email, "password": "wrong"})
    assert response.status_code == 401


def test_me_returns_the_signed_in_user(client, auth, admin):
    body = client.get("/api/v1/auth/me", headers=auth).json()
    assert body["email"] == admin.email
    assert body["role"] == "ADMIN"


def test_audit_logs_are_admin_only(client, desk_auth, auth):
    assert client.get("/api/v1/audit-logs", headers=desk_auth).status_code == 403
    assert client.get("/api/v1/audit-logs", headers=auth).status_code == 200


def test_audit_trail_records_status_changes(client, auth, masters):
    client.patch(
        f"/api/v1/products/{masters['product_id']}", json={"status": "INACTIVE"}, headers=auth
    )
    rows = client.get(
        f"/api/v1/audit-logs?entity_type=product&entity_id={masters['product_id']}",
        headers=auth,
    ).json()["items"]
    actions = {row["action"] for row in rows}
    assert "STATUS_CHANGE" in actions
    change = next(row for row in rows if row["action"] == "STATUS_CHANGE")
    assert change["old_value"]["status"] == "ACTIVE"
    assert change["new_value"]["status"] == "INACTIVE"


def test_search_finds_products_by_grade_and_manufacturer(client, auth, masters, parties):
    by_grade = client.get("/api/v1/search?q=K-67", headers=auth).json()
    assert [hit["label"] for hit in by_grade["products"]] == ["Reliance PVC K-67"]
    assert [hit["label"] for hit in by_grade["grades"]] == ["K-67"]

    by_manufacturer = client.get("/api/v1/search?q=Reliance", headers=auth).json()
    assert by_manufacturer["manufacturers"]
    assert by_manufacturer["products"]

    by_party = client.get("/api/v1/search?q=ABC", headers=auth).json()
    assert [hit["label"] for hit in by_party["parties"]] == ["ABC Pipes"]


def test_notes_are_separate_from_activities(client, auth, parties):
    created = client.post(
        "/api/v1/notes",
        json={
            "party_id": parties["customer"],
            "note": "Customer is expanding a second factory.",
        },
        headers=auth,
    )
    assert created.status_code == 201
    note_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/notes/{note_id}",
        json={"note": "Second factory live from November."},
        headers=auth,
    )
    assert updated.json()["note"].startswith("Second factory")
    rows = client.get(f"/api/v1/notes?party_id={parties['customer']}", headers=auth).json()
    assert rows["total"] == 1
    # Notes for a supplier are supported too (design is party based).
    supplier_note = client.post(
        "/api/v1/notes",
        json={"party_id": parties["supplier"], "note": "Best K-67 rates ex-Ahmedabad."},
        headers=auth,
    )
    assert supplier_note.status_code == 201


def test_pagination_metadata(client, auth, parties):
    page = client.get("/api/v1/parties?page=1&page_size=2", headers=auth).json()
    assert page["page"] == 1
    assert page["page_size"] == 2
    assert page["total"] == 4
    assert page["pages"] == 2
    assert len(page["items"]) == 2


def test_dashboard_counts(client, auth, masters, parties):
    client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "CUSTOMER",
            "customer": {
                "customer_id": parties["customer"],
                "product_id": masters["product_id"],
                "quantity": "20",
            },
        },
        headers=auth,
    )
    counts = client.get("/api/v1/dashboard", headers=auth).json()["counts"]
    assert counts["open_customer_inquiries"] == 1
    assert counts["active_customers"] == 2
    assert counts["active_suppliers"] == 1


def test_meta_enums_expose_state_machine(client, auth):
    body = client.get("/api/v1/meta/enums", headers=auth).json()
    assert body["inquiry_status"] == ["ACTIVE", "CLOSED"]
    assert "closure_reason" not in body
    assert "inquiry_transitions" not in body["rules"]
    assert body["rules"]["party_product_relationships"]["TRANSPORTER"] == []
