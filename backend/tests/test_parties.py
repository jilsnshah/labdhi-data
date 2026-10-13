"""Party rules: type-specific product relationships, locations, 360 view."""

from __future__ import annotations

import pytest


def test_customer_product_defaults_to_purchases(client, auth, masters, parties):
    response = client.post(
        f"/api/v1/parties/{parties['customer']}/products",
        json={"product_id": masters["product_id"]},
        headers=auth,
    )
    assert response.status_code == 201
    assert response.json()["relationship_type"] == "PURCHASES"


def test_supplier_product_defaults_to_supplies(client, auth, masters, parties):
    response = client.post(
        f"/api/v1/parties/{parties['supplier']}/products",
        json={"product_id": masters["product_id"]},
        headers=auth,
    )
    assert response.json()["relationship_type"] == "SUPPLIES"


def test_supplier_cannot_purchase(client, auth, masters, parties):
    response = client.post(
        f"/api/v1/parties/{parties['supplier']}/products",
        json={"product_id": masters["product_id"], "relationship_type": "PURCHASES"},
        headers=auth,
    )
    assert response.status_code == 422
    assert "not valid for a SUPPLIER" in response.json()["error"]["message"]


def test_transporter_cannot_have_products(client, auth, masters, parties):
    response = client.post(
        f"/api/v1/parties/{parties['transporter']}/products",
        json={"product_id": masters["product_id"]},
        headers=auth,
    )
    assert response.status_code == 422
    assert "cannot be linked to products" in response.json()["error"]["message"]


def test_duplicate_party_product_link_is_rejected(client, auth, masters, parties):
    payload = {"product_id": masters["product_id"]}
    client.post(f"/api/v1/parties/{parties['customer']}/products", json=payload, headers=auth)
    second = client.post(
        f"/api/v1/parties/{parties['customer']}/products", json=payload, headers=auth
    )
    assert second.status_code == 409


def test_create_party_with_inline_location_and_products(client, auth, masters):
    response = client.post(
        "/api/v1/parties",
        json={
            "name": "Shreeji Profiles",
            "party_type": "CUSTOMER",
            "phone": "+91 98250 11003",
            "locations": [
                {
                    "location": {"label": "Plant", "city": "Surat", "state": "Gujarat"},
                    "location_type": "FACTORY",
                }
            ],
            "products": [
                {"product_id": masters["product_id"], "relationship_type": "INTERESTED_IN"}
            ],
        },
        headers=auth,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["locations"][0]["is_primary"] is True  # first location becomes primary
    assert body["locations"][0]["location"]["city"] == "Surat"
    assert body["products"][0]["relationship_type"] == "INTERESTED_IN"


def test_only_one_primary_location_per_party(client, auth, parties):
    first = client.post(
        f"/api/v1/parties/{parties['customer']}/locations",
        json={"location": {"label": "HO", "city": "Rajkot"}, "location_type": "HEAD_OFFICE"},
        headers=auth,
    ).json()
    second = client.post(
        f"/api/v1/parties/{parties['customer']}/locations",
        json={
            "location": {"label": "Factory", "city": "Shapar"},
            "location_type": "FACTORY",
            "is_primary": True,
        },
        headers=auth,
    ).json()
    links = client.get(f"/api/v1/parties/{parties['customer']}/locations", headers=auth).json()
    flags = {link["id"]: link["is_primary"] for link in links}
    assert flags[first["id"]] is False
    assert flags[second["id"]] is True


def test_duplicate_party_name_per_type_is_rejected(client, auth, parties):
    response = client.post(
        "/api/v1/parties", json={"name": "abc pipes", "party_type": "CUSTOMER"}, headers=auth
    )
    assert response.status_code == 409
    # Same name under a different party type is allowed.
    allowed = client.post(
        "/api/v1/parties", json={"name": "ABC Pipes", "party_type": "SUPPLIER"}, headers=auth
    )
    assert allowed.status_code == 201


def test_product_supplier_and_customer_lookups(client, auth, masters, parties):
    client.post(
        f"/api/v1/parties/{parties['supplier']}/products",
        json={"product_id": masters["product_id"]},
        headers=auth,
    )
    client.post(
        f"/api/v1/parties/{parties['customer']}/products",
        json={"product_id": masters["product_id"], "relationship_type": "INTERESTED_IN"},
        headers=auth,
    )
    suppliers = client.get(
        f"/api/v1/products/{masters['product_id']}/suppliers", headers=auth
    ).json()
    customers = client.get(
        f"/api/v1/products/{masters['product_id']}/customers", headers=auth
    ).json()
    assert [row["party_name"] for row in suppliers] == ["Mahavir Polymers"]
    assert [row["relationship_type"] for row in customers] == ["INTERESTED_IN"]


def test_party_overview_shape(client, auth, parties):
    body = client.get(f"/api/v1/parties/{parties['customer']}/overview", headers=auth).json()
    assert body["party"]["name"] == "ABC Pipes"
    assert body["deals"] == []  # extension point for the future trading module
    for key in ("open_inquiries", "inquiry_history", "activities", "notes", "timeline"):
        assert key in body


@pytest.mark.parametrize("party_key", ["customer", "supplier", "transporter"])
def test_overview_loads_for_every_party_type(client, auth, parties, party_key):
    """The 360 view must work for all three types.

    It once keyed its inquiry lookup by InquiryType while passing a PartyType:
    CUSTOMER and SUPPLIER matched by string value, TRANSPORTER did not, so every
    transporter page returned a 500.
    """
    response = client.get(f"/api/v1/parties/{parties[party_key]}/overview", headers=auth)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["party"]["id"] == parties[party_key]
    for key in ("stats", "open_inquiries", "inquiry_history", "notes"):
        assert key in body


def test_transporter_overview_includes_its_transport_inquiries(
    client, auth, parties, masters, locations
):
    inquiry = client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "TRANSPORT",
            "transport": {
                "transporter_id": parties["transporter"],
                "quantity": "20",
                "pickup_location_id": locations["pickup_id"],
                "delivery_location_id": locations["delivery_id"],
            },
        },
        headers=auth,
    )
    assert inquiry.status_code == 201, inquiry.text

    overview = client.get(f"/api/v1/parties/{parties['transporter']}/overview", headers=auth).json()
    assert [item["id"] for item in overview["open_inquiries"]] == [inquiry.json()["id"]]
    assert overview["stats"]["open_inquiries"] == 1


# --- End-uses a party works in ---------------------------------------------
def _link_application(client, auth, party_id, application_id):
    response = client.post(
        f"/api/v1/parties/{party_id}/applications",
        json={"application_id": application_id},
        headers=auth,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_an_end_use_can_be_linked_listed_and_unlinked(client, auth, masters, parties):
    link = _link_application(client, auth, parties["supplier"], masters["application_id"])

    listed = client.get(f"/api/v1/parties/{parties['supplier']}/applications", headers=auth)
    assert [row["application"]["name"] for row in listed.json()] == ["PVC Pipes"]

    detail = client.get(f"/api/v1/parties/{parties['supplier']}", headers=auth).json()
    assert detail["applications"][0]["application"]["name"] == "PVC Pipes"

    removed = client.delete(
        f"/api/v1/parties/{parties['supplier']}/applications/{link['id']}", headers=auth
    )
    assert removed.status_code == 200, removed.text
    assert (
        client.get(f"/api/v1/parties/{parties['supplier']}/applications", headers=auth).json() == []
    )


def test_the_same_end_use_cannot_be_linked_twice(client, auth, masters, parties):
    _link_application(client, auth, parties["supplier"], masters["application_id"])
    again = client.post(
        f"/api/v1/parties/{parties['supplier']}/applications",
        json={"application_id": masters["application_id"]},
        headers=auth,
    )
    assert again.status_code == 409, again.text


def test_book_summary_counts_the_whole_book_not_one_page(client, auth, parties):
    """The cards above the table must not read their figures off the loaded page."""
    for index, city in enumerate(["Morbi", "Morbi", "Rajkot"]):
        client.post(
            "/api/v1/parties",
            json={
                "name": f"Bulk Customer {index}",
                "party_type": "CUSTOMER",
                "locations": [{"location": {"city": city, "state": "Gujarat"}}],
            },
            headers=auth,
        )
    client.post(
        "/api/v1/parties/prospects",
        json={"name": "Met at the gate", "party_type": "CUSTOMER", "phone": "+91 90000 11111"},
        headers=auth,
    )

    summary = client.get(
        "/api/v1/parties/summary", params={"party_type": "CUSTOMER"}, headers=auth
    ).json()
    listed = client.get(
        "/api/v1/parties", params={"party_type": "CUSTOMER", "page_size": 2}, headers=auth
    ).json()

    assert summary["total"] == listed["total"], "the page size must not change the figures"
    assert summary["total"] > len(listed["items"])
    assert summary["prospects"] == 1
    assert summary["verified"] == summary["total"] - 1
    assert summary["cities"] == 2, "distinct cities, not one per party"

    other = client.get(
        "/api/v1/parties/summary", params={"party_type": "SUPPLIER"}, headers=auth
    ).json()
    assert other["total"] < summary["total"], "each book is counted on its own"


def test_book_summary_is_staff_only(client, sales_auth):
    response = client.get(
        "/api/v1/parties/summary", params={"party_type": "CUSTOMER"}, headers=sales_auth
    )
    assert response.status_code == 403


def test_parties_are_found_by_what_they_deal_in(client, auth, masters, parties):
    """ "Who deals in PVC?" - asked of the products linked to a party."""
    client.post(
        f"/api/v1/parties/{parties['customer']}/products",
        json={"product_id": masters["product_id"], "relationship_type": "PURCHASES"},
        headers=auth,
    )

    def found(**params) -> list[str]:
        params.setdefault("party_type", "CUSTOMER")
        rows = client.get("/api/v1/parties", params=params, headers=auth).json()["items"]
        return [row["name"] for row in rows]

    assert found(material_id=masters["material_id"]) == ["ABC Pipes"]
    assert found(grade_id=masters["grade_id"]) == ["ABC Pipes"]
    assert found(manufacturer_id=masters["manufacturer_id"]) == ["ABC Pipes"]
    assert found(product_id=masters["product_id"]) == ["ABC Pipes"]
    # A material they do not deal in finds nobody.
    assert found(material_id=masters["other_material_id"]) == []


def test_an_end_use_counts_whether_declared_or_implied(client, auth, masters, parties):
    """A party may say "I make pipes", or simply deal in a pipe-grade product."""
    implied, declared = parties["customer"], parties["other_customer"]
    client.post(
        f"/api/v1/parties/{implied}/products",
        json={"product_id": masters["product_id"], "relationship_type": "PURCHASES"},
        headers=auth,
    )
    client.post(
        f"/api/v1/parties/{declared}/applications",
        json={"application_id": masters["application_id"]},
        headers=auth,
    )

    rows = client.get(
        "/api/v1/parties",
        params={"party_type": "CUSTOMER", "application_id": masters["application_id"]},
        headers=auth,
    ).json()
    assert {row["id"] for row in rows["items"]} == {implied, declared}
