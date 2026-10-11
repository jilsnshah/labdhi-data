"""End-to-end checks for the critical workflows A-G from the specification."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

FUTURE = (date.today() + timedelta(days=9)).isoformat()


def _soon(hours: int = 3) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


def test_workflow_a_add_product(client, auth):
    """Material -> Grade -> Manufacturer -> Application -> Product -> applications."""
    material = client.post("/api/v1/materials", json={"name": "PP"}, headers=auth).json()
    grade = client.post(
        "/api/v1/grades", json={"material_id": material["id"], "name": "MFI 12"}, headers=auth
    ).json()
    manufacturer = client.post(
        "/api/v1/manufacturers", json={"name": "IOCL", "code": "IOC"}, headers=auth
    ).json()
    raffia = client.post("/api/v1/applications", json={"name": "Raffia"}, headers=auth).json()
    moulding = client.post(
        "/api/v1/applications", json={"name": "Injection Moulding"}, headers=auth
    ).json()
    product = client.post(
        "/api/v1/products",
        json={
            "material_id": material["id"],
            "grade_id": grade["id"],
            "manufacturer_id": manufacturer["id"],
            "application_ids": [raffia["id"]],
        },
        headers=auth,
    )
    assert product.status_code == 201
    product_id = product.json()["id"]

    updated = client.patch(
        f"/api/v1/products/{product_id}",
        json={"application_ids": [raffia["id"], moulding["id"]]},
        headers=auth,
    ).json()
    assert sorted(a["name"] for a in updated["applications"]) == [
        "Injection Moulding",
        "Raffia",
    ]


def test_workflow_b_and_c_add_supplier_and_customer(client, auth, masters):
    """Create party -> add location -> associate products, for both roles."""
    supplier = client.post(
        "/api/v1/parties",
        json={
            "name": "Western Polychem",
            "party_type": "SUPPLIER",
            "phone": "+91 98250 22003",
            "locations": [
                {
                    "location": {"label": "Vapi Warehouse", "city": "Vapi", "state": "Gujarat"},
                    "location_type": "WAREHOUSE",
                }
            ],
            "products": [{"product_id": masters["product_id"]}],
        },
        headers=auth,
    )
    assert supplier.status_code == 201
    assert supplier.json()["products"][0]["relationship_type"] == "SUPPLIES"

    customer = client.post(
        "/api/v1/parties", json={"name": "Kiran Moulders", "party_type": "CUSTOMER"}, headers=auth
    ).json()
    location = client.post(
        f"/api/v1/parties/{customer['id']}/locations",
        json={
            "location": {"label": "Factory", "city": "Vadodara", "state": "Gujarat"},
            "location_type": "FACTORY",
        },
        headers=auth,
    )
    assert location.status_code == 201
    link = client.post(
        f"/api/v1/parties/{customer['id']}/products",
        json={"product_id": masters["product_id"], "relationship_type": "INTERESTED_IN"},
        headers=auth,
    )
    assert link.status_code == 201

    # The sourcing question both links exist to answer.
    suppliers = client.get(
        f"/api/v1/products/{masters['product_id']}/suppliers", headers=auth
    ).json()
    assert [row["party_name"] for row in suppliers] == ["Western Polychem"]
    customers = client.get(
        f"/api/v1/products/{masters['product_id']}/customers", headers=auth
    ).json()
    assert [row["party_name"] for row in customers] == ["Kiran Moulders"]


def test_workflow_d_e_supplier_and_customer_quotes_recorded_directly(
    client, auth, masters, parties
):
    """Unknown supplier -> prospect -> new location -> quote; same for a customer."""
    # A supplier nobody has on file: name and phone only.
    supplier = client.post(
        "/api/v1/parties/prospects",
        json={"party_type": "SUPPLIER", "name": "Gujarat Resins", "phone": "+91 90990 11223"},
        headers=auth,
    ).json()
    assert supplier["stage"] == "PROSPECT"

    # Their godown is not in Master Data yet: add it from the form.
    godown = client.post(
        "/api/v1/locations", json={"label": "Gujarat Resins godown", "city": "Morbi"}, headers=auth
    ).json()

    quote = client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "SUPPLIER",
            "supplier": {
                "supplier_id": supplier["id"],
                "product_id": masters["product_id"],
                "quantity": "25",
                "location_id": godown["id"],
                "rate": "90.25",
            },
        },
        headers=auth,
    )
    assert quote.status_code == 201, quote.text
    assert quote.json()["status"] == "ACTIVE"

    # The customer side uses the same fields, and the same new location is reusable.
    demand = client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "CUSTOMER",
            "customer": {
                "customer_id": parties["customer"],
                "product_id": masters["product_id"],
                "quantity": "20",
                "location_id": godown["id"],
                "rate": "92.00",
            },
        },
        headers=auth,
    ).json()

    listed = client.get(
        "/api/v1/inquiries", params={"product_id": masters["product_id"]}, headers=auth
    ).json()
    rates = {row["party_name"]: row["rate"] for row in listed["items"]}
    assert rates == {"Gujarat Resins": "90.25", "ABC Pipes": "92.00"}

    # Done with it: close, and it leaves the active list.
    client.patch(f"/api/v1/inquiries/{demand['id']}", json={"status": "CLOSED"}, headers=auth)
    active = client.get(
        "/api/v1/inquiries", params={"inquiry_type": "CUSTOMER", "status": "ACTIVE"}, headers=auth
    ).json()
    assert demand["id"] not in [row["id"] for row in active["items"]]

    # The prospect is reusable for the next quote.
    again = client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "SUPPLIER",
            "supplier": {
                "supplier_id": supplier["id"],
                "product_id": masters["product_id"],
                "quantity": "10",
                "rate": "89.90",
            },
        },
        headers=auth,
    )
    assert again.status_code == 201, again.text


def test_workflow_f_transport_quote(client, auth, parties, locations):
    inquiry = client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "TRANSPORT",
            "transport": {
                "transporter_id": parties["transporter"],
                "quantity": "20",
                "unit": "MT",
                "pickup_location_id": locations["pickup_id"],
                "delivery_location_id": locations["delivery_id"],
                "price": "18000",
            },
        },
        headers=auth,
    )
    assert inquiry.status_code == 201, inquiry.text
    body = inquiry.json()
    assert body["transport_detail"]["pickup_location"]["city"] == "Ahmedabad"
    assert body["transport_detail"]["delivery_location"]["city"] == "Rajkot"
    assert body["transport_detail"]["price"] == "18000.00"

    closed = client.patch(
        f"/api/v1/inquiries/{body['id']}", json={"status": "CLOSED"}, headers=auth
    ).json()
    assert closed["status"] == "CLOSED"


def test_workflow_g_customer_activity_chain(client, auth, parties):
    """Schedule -> complete with outcome -> schedule follow-up linked to the parent."""
    first = client.post(
        "/api/v1/activities",
        json={
            "customer_id": parties["customer"],
            "activity_type": "CALL",
            "scheduled_at": _soon(),
            "note": "Follow up regarding the PVC requirement.",
        },
        headers=auth,
    ).json()
    assert first["status"] == "SCHEDULED"

    completed = client.post(
        f"/api/v1/activities/{first['id']}/complete",
        json={
            "outcome": "Customer expects the requirement next week.",
            "follow_up": {
                "activity_type": "CALL",
                "scheduled_at": _soon(hours=24 * 7),
                "note": "Check the requirement again.",
            },
        },
        headers=auth,
    ).json()
    follow_up = completed["follow_up"]
    assert follow_up["parent_activity_id"] == first["id"]

    overview = client.get(f"/api/v1/parties/{parties['customer']}/overview", headers=auth).json()
    assert overview["stats"]["activities"] == 2
    assert [a["id"] for a in overview["upcoming_activities"]] == [follow_up["id"]]
    kinds = {event["kind"] for event in overview["timeline"]}
    assert "activity" in kinds
