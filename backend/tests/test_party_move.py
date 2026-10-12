"""Moving a party between the books.

A trader's counterparty is not fixed: the shop you sell PVC to today sells you
their surplus tomorrow, and a thousand rows imported from a ledger all arrive
as customers until someone says otherwise. Moving one must keep its history,
its notes and what it deals in - and must not quietly leave a live quote in a
book it no longer belongs to.
"""

from __future__ import annotations

import pytest


def move(client, auth, party_id: int, party_type: str):
    return client.post(
        f"/api/v1/parties/{party_id}/move", json={"party_type": party_type}, headers=auth
    )


def test_a_customer_becomes_a_supplier(client, auth, parties):
    response = move(client, auth, parties["customer"], "SUPPLIER")
    assert response.status_code == 200, response.text
    assert response.json()["party"]["party_type"] == "SUPPLIER"

    # It is in the supplier book now, and out of the customer book.
    suppliers = client.get("/api/v1/parties", params={"party_type": "SUPPLIER"}, headers=auth)
    assert parties["customer"] in [row["id"] for row in suppliers.json()["items"]]
    customers = client.get("/api/v1/parties", params={"party_type": "CUSTOMER"}, headers=auth)
    assert parties["customer"] not in [row["id"] for row in customers.json()["items"]]


def test_a_supplier_becomes_a_customer(client, auth, parties):
    response = move(client, auth, parties["supplier"], "CUSTOMER")
    assert response.status_code == 200, response.text
    assert response.json()["party"]["party_type"] == "CUSTOMER"


def test_the_party_keeps_everything_that_is_not_about_its_type(client, auth, masters, parties):
    party_id = parties["customer"]
    client.post(
        f"/api/v1/parties/{party_id}/locations",
        json={"location": {"label": "Works", "city": "Rajkot"}, "location_type": "FACTORY"},
        headers=auth,
    )
    note = client.post(
        "/api/v1/notes",
        json={"party_id": party_id, "note": "Pays on time."},
        headers=auth,
    )
    assert note.status_code == 201, note.text
    before = client.get(f"/api/v1/parties/{party_id}", headers=auth).json()

    move(client, auth, party_id, "SUPPLIER")
    after = client.get(f"/api/v1/parties/{party_id}", headers=auth).json()

    assert after["name"] == before["name"]
    assert after["gst_number"] == before["gst_number"]
    assert len(after["locations"]) == len(before["locations"])
    notes = client.get("/api/v1/notes", params={"party_id": party_id}, headers=auth).json()
    assert notes["total"] == 1, "notes follow the party"


def test_what_they_bought_is_what_they_now_supply(client, auth, masters, parties):
    party_id = parties["customer"]
    client.post(
        f"/api/v1/parties/{party_id}/products",
        json={"product_id": masters["product_id"], "relationship_type": "PURCHASES"},
        headers=auth,
    )

    response = move(client, auth, party_id, "SUPPLIER")
    assert response.json()["products_repointed"] == 1

    party = client.get(f"/api/v1/parties/{party_id}", headers=auth).json()
    assert [link["relationship_type"] for link in party["products"]] == ["SUPPLIES"]


def test_two_links_to_one_product_collapse_into_one(client, auth, masters, parties):
    """A customer may both buy a product and be interested in it; a supplier
    simply supplies it, and the link is unique per relationship."""
    party_id = parties["customer"]
    for relationship in ("PURCHASES", "INTERESTED_IN"):
        client.post(
            f"/api/v1/parties/{party_id}/products",
            json={"product_id": masters["product_id"], "relationship_type": relationship},
            headers=auth,
        )

    response = move(client, auth, party_id, "SUPPLIER")
    assert response.status_code == 200, response.text
    assert response.json()["products_repointed"] == 1
    party = client.get(f"/api/v1/parties/{party_id}", headers=auth).json()
    assert len(party["products"]) == 1


def test_a_live_quote_blocks_the_move(client, auth, masters, parties):
    inquiry = client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "CUSTOMER",
            "customer": {
                "customer_id": parties["customer"],
                "product_id": masters["product_id"],
                "quantity": "10",
                "rate": "92.50",
            },
        },
        headers=auth,
    )
    assert inquiry.status_code == 201, inquiry.text

    blocked = move(client, auth, parties["customer"], "SUPPLIER")
    assert blocked.status_code == 422
    assert "active customer" in blocked.json()["error"]["message"]

    # Closed, it is history: the move goes through and the record stays put.
    client.patch(
        f"/api/v1/inquiries/{inquiry.json()['id']}", json={"status": "CLOSED"}, headers=auth
    )
    assert move(client, auth, parties["customer"], "SUPPLIER").status_code == 200
    closed = client.get(f"/api/v1/inquiries/{inquiry.json()['id']}", headers=auth).json()
    assert closed["customer_detail"]["customer_id"] == parties["customer"]


def test_the_name_must_be_free_in_the_book_it_moves_into(client, auth, parties):
    client.post(
        "/api/v1/parties",
        json={"name": "ABC Pipes", "party_type": "SUPPLIER"},
        headers=auth,
    )
    response = move(client, auth, parties["customer"], "SUPPLIER")
    assert response.status_code == 409
    assert "already exists" in response.json()["error"]["message"]


def test_a_transporter_cannot_carry_product_links(client, auth, masters, parties):
    client.post(
        f"/api/v1/parties/{parties['customer']}/products",
        json={"product_id": masters["product_id"], "relationship_type": "PURCHASES"},
        headers=auth,
    )
    response = move(client, auth, parties["customer"], "TRANSPORTER")
    assert response.status_code == 422
    assert "cannot be linked to products" in response.json()["error"]["message"]


def test_moving_a_party_to_the_book_it_is_already_in_is_refused(client, auth, parties):
    response = move(client, auth, parties["customer"], "CUSTOMER")
    assert response.status_code == 422
    assert "already a customer" in response.json()["error"]["message"]


def test_the_move_is_written_to_the_audit_log(client, auth, parties):
    move(client, auth, parties["customer"], "SUPPLIER")
    rows = client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "party", "entity_id": parties["customer"]},
        headers=auth,
    ).json()
    entry = next(row for row in rows["items"] if row["action"] == "UPDATE")
    assert entry["old_value"]["party_type"] == "CUSTOMER"
    assert entry["new_value"]["party_type"] == "SUPPLIER"


@pytest.mark.parametrize("headers_name", ["sales_auth"])
def test_a_salesperson_cannot_move_a_party(client, parties, request, headers_name):
    headers = request.getfixturevalue(headers_name)
    response = client.post(
        f"/api/v1/parties/{parties['customer']}/move",
        json={"party_type": "SUPPLIER"},
        headers=headers,
    )
    assert response.status_code == 403
