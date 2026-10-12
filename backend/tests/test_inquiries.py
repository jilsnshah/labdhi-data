"""Inquiries as recorded quotations: create, validate, edit, ACTIVE <-> CLOSED, list."""

from __future__ import annotations

import pytest


def _customer_inquiry(client, auth, masters, parties, status=None, **overrides):
    payload = {
        "inquiry_type": "CUSTOMER",
        "customer": {
            "customer_id": parties["customer"],
            "product_id": masters["product_id"],
            "quantity": "20",
            "unit": "MT",
            "rate": "91.50",
            **overrides,
        },
    }
    if status:
        payload["status"] = status
    return client.post("/api/v1/inquiries", json=payload, headers=auth)


def _supplier_inquiry(client, auth, masters, parties, **overrides):
    return client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "SUPPLIER",
            "supplier": {
                "supplier_id": parties["supplier"],
                "product_id": masters["product_id"],
                "quantity": "25",
                "rate": "90.80",
                **overrides,
            },
        },
        headers=auth,
    )


def _transport_inquiry(client, auth, parties, locations, **overrides):
    return client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "TRANSPORT",
            "transport": {
                "transporter_id": parties["transporter"],
                "quantity": "20",
                "pickup_location_id": locations["pickup_id"],
                "delivery_location_id": locations["delivery_id"],
                "price": "18000",
                **overrides,
            },
        },
        headers=auth,
    )


# --------------------------------------------------------------------------- #
# Creating a recorded quotation
# --------------------------------------------------------------------------- #
def test_customer_inquiry_records_the_quote_directly(client, auth, masters, parties, locations):
    response = _customer_inquiry(
        client, auth, masters, parties, location_id=locations["delivery_id"]
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "ACTIVE"
    detail = body["customer_detail"]
    assert detail["customer"]["name"] == "ABC Pipes"
    assert detail["product"]["display_name"] == "Reliance PVC K-67"
    assert detail["rate"] == "91.50"
    assert detail["location"]["city"] == "Rajkot"


def test_supplier_inquiry_records_the_quote_directly(client, auth, masters, parties, locations):
    response = _supplier_inquiry(client, auth, masters, parties, location_id=locations["pickup_id"])
    assert response.status_code == 201, response.text
    detail = response.json()["supplier_detail"]
    assert detail["supplier"]["name"] == "Mahavir Polymers"
    assert detail["rate"] == "90.80"
    assert detail["location"]["city"] == "Ahmedabad"


def test_transport_inquiry_records_the_price_and_route(client, auth, parties, locations):
    response = _transport_inquiry(client, auth, parties, locations)
    assert response.status_code == 201, response.text
    detail = response.json()["transport_detail"]
    assert detail["price"] == "18000.00"
    assert detail["pickup_location"]["city"] == "Ahmedabad"
    assert detail["delivery_location"]["city"] == "Rajkot"


def test_rate_and_location_are_optional(client, auth, masters, parties):
    """A customer asking for our rate is still worth recording."""
    response = _customer_inquiry(client, auth, masters, parties, rate=None)
    assert response.status_code == 201, response.text
    detail = response.json()["customer_detail"]
    assert detail["rate"] is None
    assert detail["location"] is None


def test_an_inquiry_can_be_recorded_already_closed(client, auth, masters, parties):
    response = _customer_inquiry(client, auth, masters, parties, status="CLOSED")
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "CLOSED"
    assert response.json()["closed_at"] is not None


@pytest.mark.parametrize("status", ["OPEN", "QUOTED", "WAITING", "CANCELLED", "IN_PROGRESS"])
def test_only_active_and_closed_exist(client, auth, masters, parties, status):
    response = _customer_inquiry(client, auth, masters, parties, status=status)
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def test_customer_inquiry_must_reference_a_customer(client, auth, masters, parties):
    response = _customer_inquiry(client, auth, masters, parties, customer_id=parties["supplier"])
    assert response.status_code == 422
    assert "a CUSTOMER is required" in response.json()["error"]["message"]


def test_supplier_inquiry_must_reference_a_supplier(client, auth, masters, parties):
    response = _supplier_inquiry(client, auth, masters, parties, supplier_id=parties["customer"])
    assert response.status_code == 422
    assert "a SUPPLIER is required" in response.json()["error"]["message"]


def test_transport_inquiry_requires_transporter_and_distinct_locations(
    client, auth, parties, locations
):
    wrong_party = _transport_inquiry(
        client, auth, parties, locations, transporter_id=parties["customer"]
    )
    assert wrong_party.status_code == 422

    same_location = _transport_inquiry(
        client, auth, parties, locations, delivery_location_id=locations["pickup_id"]
    )
    assert same_location.status_code == 422


def test_detail_block_must_match_inquiry_type(client, auth, masters, parties):
    response = client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "SUPPLIER",
            "customer": {
                "customer_id": parties["customer"],
                "product_id": masters["product_id"],
                "quantity": "20",
            },
        },
        headers=auth,
    )
    assert response.status_code == 422


@pytest.mark.parametrize("field,value", [("quantity", "0"), ("rate", "0"), ("rate", "-5")])
def test_quantity_and_rate_must_be_positive(client, auth, masters, parties, field, value):
    response = _customer_inquiry(client, auth, masters, parties, **{field: value})
    assert response.status_code == 422


def test_inactive_customer_cannot_raise_an_inquiry(client, auth, masters, parties):
    client.patch(
        f"/api/v1/parties/{parties['customer']}", json={"status": "INACTIVE"}, headers=auth
    )
    response = _customer_inquiry(client, auth, masters, parties)
    assert response.status_code == 422
    assert "inactive" in response.json()["error"]["message"]


def test_unknown_location_is_refused(client, auth, masters, parties):
    response = _customer_inquiry(client, auth, masters, parties, location_id=999999)
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Locations are independent of parties
# --------------------------------------------------------------------------- #
def test_any_location_may_be_used_whatever_the_party(client, auth, masters, parties):
    """The supplier has no link to this location; it must be selectable anyway."""
    elsewhere = client.post(
        "/api/v1/locations", json={"label": "Kandla Port", "city": "Gandhidham"}, headers=auth
    ).json()
    response = _supplier_inquiry(client, auth, masters, parties, location_id=elsewhere["id"])
    assert response.status_code == 201, response.text
    assert response.json()["supplier_detail"]["location"]["city"] == "Gandhidham"


def test_a_location_added_from_a_form_is_reusable(client, auth, masters, parties):
    created = client.post(
        "/api/v1/locations", json={"label": "Morbi godown", "city": "Morbi"}, headers=auth
    )
    assert created.status_code == 201, created.text
    location_id = created.json()["id"]
    listed = client.get("/api/v1/locations", params={"q": "Morbi"}, headers=auth).json()
    assert location_id in [row["id"] for row in listed["items"]]
    for _ in range(2):
        response = _customer_inquiry(client, auth, masters, parties, location_id=location_id)
        assert response.status_code == 201, response.text


# --------------------------------------------------------------------------- #
# Editing and status
# --------------------------------------------------------------------------- #
def test_status_switches_between_active_and_closed(client, auth, masters, parties):
    inquiry = _customer_inquiry(client, auth, masters, parties).json()

    closed = client.patch(
        f"/api/v1/inquiries/{inquiry['id']}", json={"status": "CLOSED"}, headers=auth
    ).json()
    assert closed["status"] == "CLOSED"
    assert closed["closed_at"] is not None
    assert closed["closer"]["name"] == "Test Admin"

    reopened = client.patch(
        f"/api/v1/inquiries/{inquiry['id']}", json={"status": "ACTIVE"}, headers=auth
    ).json()
    assert reopened["status"] == "ACTIVE"
    assert reopened["closed_at"] is None


def test_every_field_can_be_edited(client, auth, masters, parties, locations):
    other_customer = parties["other_customer"]
    inquiry = _customer_inquiry(client, auth, masters, parties).json()
    response = client.patch(
        f"/api/v1/inquiries/{inquiry['id']}",
        json={
            "party_id": other_customer,
            "quantity": "12.5",
            "unit": "KG",
            "rate": "93.25",
            "location_id": locations["pickup_id"],
        },
        headers=auth,
    )
    assert response.status_code == 200, response.text
    detail = response.json()["customer_detail"]
    assert detail["customer"]["id"] == other_customer
    assert detail["quantity"] == "12.500"
    assert detail["unit"] == "KG"
    assert detail["rate"] == "93.25"
    assert detail["location"]["city"] == "Ahmedabad"


def test_a_location_can_be_cleared(client, auth, masters, parties, locations):
    inquiry = _customer_inquiry(
        client, auth, masters, parties, location_id=locations["pickup_id"]
    ).json()
    response = client.patch(
        f"/api/v1/inquiries/{inquiry['id']}", json={"location_id": None}, headers=auth
    )
    assert response.json()["customer_detail"]["location"] is None


def test_a_closed_inquiry_can_still_be_corrected(client, auth, masters, parties):
    inquiry = _customer_inquiry(client, auth, masters, parties, status="CLOSED").json()
    response = client.patch(
        f"/api/v1/inquiries/{inquiry['id']}", json={"rate": "92.00"}, headers=auth
    )
    assert response.status_code == 200, response.text
    assert response.json()["customer_detail"]["rate"] == "92.00"
    assert response.json()["status"] == "CLOSED"


def test_transport_route_and_price_can_be_edited(client, auth, parties, locations):
    inquiry = _transport_inquiry(client, auth, parties, locations).json()
    swapped = client.patch(
        f"/api/v1/inquiries/{inquiry['id']}",
        json={
            "pickup_location_id": locations["delivery_id"],
            "delivery_location_id": locations["pickup_id"],
            "price": "21000",
        },
        headers=auth,
    )
    assert swapped.status_code == 200, swapped.text
    detail = swapped.json()["transport_detail"]
    assert detail["pickup_location"]["city"] == "Rajkot"
    assert detail["price"] == "21000.00"

    same = client.patch(
        f"/api/v1/inquiries/{inquiry['id']}",
        json={"delivery_location_id": locations["delivery_id"]},
        headers=auth,
    )
    assert same.status_code == 422


@pytest.mark.parametrize(
    "kind,body",
    [
        ("customer", {"price": "100"}),
        ("customer", {"pickup_location_id": 1}),
        ("transport", {"rate": "90"}),
        ("transport", {"product_id": 1}),
        ("transport", {"location_id": 1}),
    ],
)
def test_fields_from_another_inquiry_type_are_refused(
    client, auth, masters, parties, locations, kind, body
):
    inquiry = (
        _customer_inquiry(client, auth, masters, parties)
        if kind == "customer"
        else _transport_inquiry(client, auth, parties, locations)
    ).json()
    response = client.patch(f"/api/v1/inquiries/{inquiry['id']}", json=body, headers=auth)
    assert response.status_code == 422


def test_required_fields_cannot_be_emptied(client, auth, masters, parties):
    inquiry = _customer_inquiry(client, auth, masters, parties).json()
    response = client.patch(
        f"/api/v1/inquiries/{inquiry['id']}", json={"product_id": None}, headers=auth
    )
    assert response.status_code == 422


def test_edits_are_audited(client, auth, masters, parties):
    inquiry = _customer_inquiry(client, auth, masters, parties).json()
    client.patch(f"/api/v1/inquiries/{inquiry['id']}", json={"rate": "95.00"}, headers=auth)
    logs = client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "inquiry", "entity_id": inquiry["id"]},
        headers=auth,
    ).json()
    changes = [log for log in logs["items"] if log["action"] == "UPDATE"]
    assert changes and changes[0]["new_value"] == {"rate": "95.00"}
    assert changes[0]["old_value"] == {"rate": "91.50"}


# --------------------------------------------------------------------------- #
# Removed workflow
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "path", ["responses", "close", "ask-supplier", "ask-transporter", "counterparties"]
)
def test_the_request_and_response_workflow_is_gone(client, auth, masters, parties, path):
    inquiry = _customer_inquiry(client, auth, masters, parties).json()
    response = client.post(f"/api/v1/inquiries/{inquiry['id']}/{path}", json={}, headers=auth)
    assert response.status_code in (404, 405)


# --------------------------------------------------------------------------- #
# Listing
# --------------------------------------------------------------------------- #
def test_inquiry_filters_and_search(client, auth, masters, parties, locations):
    _customer_inquiry(client, auth, masters, parties, location_id=locations["delivery_id"])
    _customer_inquiry(client, auth, masters, parties, status="CLOSED")

    active = client.get(
        "/api/v1/inquiries",
        params={
            "inquiry_type": "CUSTOMER",
            "party_id": parties["customer"],
            "product_id": masters["product_id"],
            "status": "ACTIVE",
        },
        headers=auth,
    ).json()
    assert active["total"] == 1
    row = active["items"][0]
    assert row["party_name"] == "ABC Pipes"
    assert row["rate"] == "91.50"
    assert row["location_name"] == "Rajkot Factory, Rajkot"

    closed = client.get("/api/v1/inquiries", params={"status": "CLOSED"}, headers=auth).json()
    assert closed["total"] == 1

    by_location = client.get(
        "/api/v1/inquiries", params={"location_id": locations["delivery_id"]}, headers=auth
    ).json()
    assert by_location["total"] == 1

    by_name = client.get("/api/v1/inquiries", params={"q": "ABC"}, headers=auth).json()
    assert by_name["total"] == 2


def test_transport_rows_show_the_route(client, auth, parties, locations):
    _transport_inquiry(client, auth, parties, locations)
    row = client.get(
        "/api/v1/inquiries", params={"inquiry_type": "TRANSPORT"}, headers=auth
    ).json()["items"][0]
    assert row["pickup_name"] == "Ahmedabad Warehouse, Ahmedabad"
    assert row["delivery_name"] == "Rajkot Factory, Rajkot"
    assert row["price"] == "18000.00"


# --------------------------------------------------------------------------- #
# Area and product-attribute filters
# --------------------------------------------------------------------------- #
def _set_area(client, auth, location_id, area):
    response = client.patch(f"/api/v1/locations/{location_id}", json={"area": area}, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


def test_a_location_carries_a_tidied_area(client, auth):
    created = client.post(
        "/api/v1/locations",
        json={"label": "ABC Factory", "area": "  Shapar   Veraval ", "city": "Rajkot"},
        headers=auth,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["area"] == "Shapar Veraval"
    assert body["display_name"] == "ABC Factory - Shapar Veraval - Rajkot"


def test_areas_in_use_are_listed_once_each(client, auth, locations):
    _set_area(client, auth, locations["pickup_id"], "Narol")
    _set_area(client, auth, locations["delivery_id"], "Shapar")
    client.post("/api/v1/locations", json={"city": "Ahmedabad", "area": "Narol"}, headers=auth)
    assert client.get("/api/v1/locations/areas", headers=auth).json() == ["Narol", "Shapar"]
    narol = client.get("/api/v1/locations", params={"area": "narol"}, headers=auth).json()
    assert narol["total"] == 2


def test_inquiries_filter_by_area_including_either_end_of_a_route(
    client, auth, masters, parties, locations
):
    _set_area(client, auth, locations["pickup_id"], "Narol")
    _set_area(client, auth, locations["delivery_id"], "Shapar")
    supplier = _supplier_inquiry(
        client, auth, masters, parties, location_id=locations["pickup_id"]
    ).json()
    customer = _customer_inquiry(
        client, auth, masters, parties, location_id=locations["delivery_id"]
    ).json()
    transport = _transport_inquiry(client, auth, parties, locations).json()

    def ids(area):
        rows = client.get("/api/v1/inquiries", params={"area": area}, headers=auth).json()
        return {row["id"] for row in rows["items"]}

    assert ids("Narol") == {supplier["id"], transport["id"]}
    assert ids("shapar") == {customer["id"], transport["id"]}
    assert ids("Udhna") == set()

    row = client.get("/api/v1/inquiries", params={"inquiry_type": "SUPPLIER"}, headers=auth).json()[
        "items"
    ][0]
    assert row["location_name"] == "Ahmedabad Warehouse, Narol, Ahmedabad"
    assert (row["location_area"], row["location_city"]) == ("Narol", "Ahmedabad")


def test_inquiries_filter_by_material_grade_brand_and_application(
    client, auth, masters, parties, locations
):
    other_product = client.post(
        "/api/v1/products",
        json={
            "material_id": masters["other_material_id"],
            "grade_id": masters["other_grade_id"],
            "manufacturer_id": masters["manufacturer_id"],
        },
        headers=auth,
    ).json()
    pvc = _customer_inquiry(client, auth, masters, parties).json()
    hdpe = _supplier_inquiry(client, auth, masters, parties, product_id=other_product["id"]).json()
    _transport_inquiry(client, auth, parties, locations)

    def ids(**params):
        rows = client.get("/api/v1/inquiries", params=params, headers=auth).json()
        return {row["id"] for row in rows["items"]}

    assert ids(material_id=masters["material_id"]) == {pvc["id"]}
    assert ids(material_id=masters["other_material_id"]) == {hdpe["id"]}
    assert ids(grade_id=masters["grade_id"]) == {pvc["id"]}
    # Same brand on both products; transport has no product, so it never matches.
    assert ids(manufacturer_id=masters["manufacturer_id"]) == {pvc["id"], hdpe["id"]}
    # Only the PVC product is tagged for the PVC Pipes application.
    assert ids(application_id=masters["application_id"]) == {pvc["id"]}
    assert ids(material_id=masters["material_id"], grade_id=masters["other_grade_id"]) == set()
