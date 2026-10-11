"""Unknown parties: quick create, duplicate detection, merge, promotion."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

FUTURE = (date.today() + timedelta(days=9)).isoformat()


def _soon(hours: float = 3) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


def _customer_inquiry(client, auth, masters, **customer):
    return client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "CUSTOMER",
            "customer": {
                "product_id": masters["product_id"],
                "quantity": "20",
                "unit": "MT",
                **customer,
            },
        },
        headers=auth,
    )


def _prospect(client, auth, name, phone="+91 90000 00001", party_type="CUSTOMER"):
    """Create a prospect the way the inquiry forms do: name and phone only."""
    response = client.post(
        "/api/v1/parties/prospects",
        json={"party_type": party_type, "name": name, "phone": phone},
        headers=auth,
    )
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------- #
# Prospects from the inquiry forms: name and phone, saved straight to Master Data
# --------------------------------------------------------------------------- #
def test_a_prospect_needs_only_a_name_and_phone(client, auth):
    party = _prospect(client, auth, "Patel Traders", "+91 99250 77001")
    assert party["stage"] == "PROSPECT"
    assert party["party_type"] == "CUSTOMER"
    assert party["source"] == "QUICK_CREATE"
    assert party["phone"] == "+91 99250 77001"


@pytest.mark.parametrize(
    "body",
    [
        {"name": "No Phone Co"},
        {"phone": "+91 90000 00002"},
        {"name": "   ", "phone": "+91 90000 00002"},
        {"name": "Blank Phone Co", "phone": "  "},
    ],
)
def test_a_prospect_needs_both_name_and_phone(client, auth, body):
    response = client.post(
        "/api/v1/parties/prospects", json={"party_type": "SUPPLIER", **body}, headers=auth
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("party_type", ["CUSTOMER", "SUPPLIER", "TRANSPORTER"])
def test_a_prospect_of_each_type_is_saved_with_that_type(client, auth, party_type):
    party = _prospect(client, auth, f"New {party_type.title()}", party_type=party_type)
    assert party["party_type"] == party_type
    listed = client.get(
        "/api/v1/parties", params={"party_type": party_type, "stage": "PROSPECT"}, headers=auth
    ).json()
    assert party["id"] in [item["id"] for item in listed["items"]]


def test_a_new_prospect_can_be_used_by_every_later_inquiry(client, auth, masters):
    party = _prospect(client, auth, "Walk-in Co")
    first = _customer_inquiry(client, auth, masters, customer_id=party["id"])
    second = _customer_inquiry(client, auth, masters, customer_id=party["id"])
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["customer_detail"]["customer"]["stage"] == "PROSPECT"


def test_supplier_and_transporter_prospects_complete_their_inquiries(
    client, auth, masters, locations
):
    supplier = _prospect(client, auth, "Nova Polymers", party_type="SUPPLIER")
    response = client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "SUPPLIER",
            "supplier": {
                "supplier_id": supplier["id"],
                "product_id": masters["product_id"],
                "quantity": "20",
                "location_id": locations["pickup_id"],
                "rate": "90.50",
            },
        },
        headers=auth,
    )
    assert response.status_code == 201, response.text

    transporter = _prospect(client, auth, "Roadside Carriers", party_type="TRANSPORTER")
    response = client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "TRANSPORT",
            "transport": {
                "transporter_id": transporter["id"],
                "quantity": "20",
                "pickup_location_id": locations["pickup_id"],
                "delivery_location_id": locations["delivery_id"],
                "price": "18000",
            },
        },
        headers=auth,
    )
    assert response.status_code == 201, response.text
    assert response.json()["transport_detail"]["transporter"]["stage"] == "PROSPECT"


def test_a_prospect_of_the_wrong_type_is_refused(client, auth, masters):
    supplier = _prospect(client, auth, "Not A Customer", party_type="SUPPLIER")
    response = _customer_inquiry(client, auth, masters, customer_id=supplier["id"])
    assert response.status_code == 422
    assert "a CUSTOMER is required" in response.json()["error"]["message"]


# --------------------------------------------------------------------------- #
# Quick create from an activity
# --------------------------------------------------------------------------- #
def test_activity_can_create_an_unknown_party_inline(client, auth, salesperson):
    response = client.post(
        "/api/v1/activities",
        json={
            "new_party": {
                "name": "Unknown Moulder",
                "phone": "+91 90033 00033",
                "party_type": "CUSTOMER",
            },
            "activity_type": "CALL",
            "scheduled_at": _soon(),
            "note": "Cold call from a broker reference.",
            "assigned_salesperson_id": salesperson.id,
        },
        headers=auth,
    )
    assert response.status_code == 201, response.text
    assert response.json()["party"]["stage"] == "PROSPECT"


def test_activity_can_create_an_unknown_supplier_to_call(client, auth):
    response = client.post(
        "/api/v1/activities",
        json={
            "new_party": {
                "name": "Cold Supplier",
                "phone": "+91 90044 00044",
                "party_type": "SUPPLIER",
            },
            "activity_type": "CALL",
            "scheduled_at": _soon(),
        },
        headers=auth,
    )
    assert response.status_code == 201
    assert response.json()["party"]["party_type"] == "SUPPLIER"


def test_visit_accepts_an_inline_address(client, auth, parties):
    response = client.post(
        "/api/v1/activities",
        json={
            "party_id": parties["customer"],
            "activity_type": "VISIT",
            "scheduled_at": _soon(),
            "new_location": {"label": "New shed", "city": "Shapar", "state": "Gujarat"},
        },
        headers=auth,
    )
    assert response.status_code == 201, response.text
    assert response.json()["location"]["city"] == "Shapar"


def test_visit_accepts_a_text_only_address(client, auth, parties, salesperson, sales_auth):
    """'His shop on Gondal Road' is a valid answer - no location row needed."""
    response = client.post(
        "/api/v1/activities",
        json={
            "party_id": parties["customer"],
            "activity_type": "VISIT",
            "scheduled_at": _soon(),
            "location_text": "His shop, Gondal Road, opposite the bus stand",
            "assigned_salesperson_id": salesperson.id,
        },
        headers=auth,
    )
    assert response.status_code == 201, response.text
    assert response.json()["location_id"] is None

    # The field app still gets something to navigate with.
    field_view = client.get(
        f"/api/v1/salesperson/activities/{response.json()['id']}", headers=sales_auth
    ).json()
    assert "Gondal Road" in field_view["location"]["formatted"]
    assert "Gondal+Road" in field_view["location"]["maps_url"]


def test_visit_still_needs_somewhere_to_go(client, auth, parties):
    response = client.post(
        "/api/v1/activities",
        json={
            "party_id": parties["customer"],
            "activity_type": "VISIT",
            "scheduled_at": _soon(),
        },
        headers=auth,
    )
    assert response.status_code == 422
    assert "location" in response.json()["error"]["message"].lower()


def test_salesperson_can_pin_the_place_they_found(client, auth, sales_auth, parties, salesperson):
    activity = client.post(
        "/api/v1/activities",
        json={
            "party_id": parties["customer"],
            "activity_type": "VISIT",
            "scheduled_at": _soon(),
            "new_location": {"label": "Shed", "city": "Shapar"},
            "assigned_salesperson_id": salesperson.id,
        },
        headers=auth,
    ).json()

    fixed = client.post(
        f"/api/v1/salesperson/activities/{activity['id']}/location-fix",
        json={"latitude": "22.1736", "longitude": "70.8697"},
        headers=sales_auth,
    )
    assert fixed.status_code == 200, fixed.text
    assert "destination=22.1736,70.8697" in fixed.json()["location"]["maps_url"]

    # Coordinates that were missing are filled in on the location master.
    location = client.get(f"/api/v1/locations/{activity['location_id']}", headers=auth).json()
    assert location["latitude"] == "22.173600"

    # And not on somebody else's activity.
    other = client.post(
        "/api/v1/activities",
        json={
            "party_id": parties["other_customer"],
            "activity_type": "VISIT",
            "scheduled_at": _soon(),
            "location_text": "Somewhere",
        },
        headers=auth,
    ).json()
    assert (
        client.post(
            f"/api/v1/salesperson/activities/{other['id']}/location-fix",
            json={"latitude": "22.0", "longitude": "70.0"},
            headers=sales_auth,
        ).status_code
        == 404
    )


# --------------------------------------------------------------------------- #
# Duplicate detection
# --------------------------------------------------------------------------- #
def test_duplicates_match_on_phone_and_gst(client, auth):
    existing = client.post(
        "/api/v1/parties",
        json={
            "name": "ABC Pipes Pvt Ltd",
            "party_type": "CUSTOMER",
            "phone": "+91 98250 11001",
            "gst_number": "24AABCA9999A1Z5",
        },
        headers=auth,
    ).json()

    by_phone = client.get(
        "/api/v1/parties/duplicates",
        params={"party_type": "CUSTOMER", "phone": "098250-11001"},
        headers=auth,
    ).json()
    assert by_phone["has_exact_match"] is True
    assert by_phone["candidates"][0]["id"] == existing["id"]
    assert by_phone["candidates"][0]["match_reason"] == "exact_phone"

    by_gst = client.get(
        "/api/v1/parties/duplicates",
        params={"gst_number": "24aabca9999a1z5"},
        headers=auth,
    ).json()
    assert by_gst["candidates"][0]["match_reason"] == "exact_gst"


def test_duplicates_match_on_a_similar_name(client, auth, parties):
    result = client.get(
        "/api/v1/parties/duplicates",
        params={"party_type": "CUSTOMER", "name": "abc pipe"},
        headers=auth,
    ).json()
    names = [candidate["name"] for candidate in result["candidates"]]
    assert "ABC Pipes" in names
    assert result["has_exact_match"] is False  # a warning, not a block


def test_duplicate_check_ignores_the_party_being_edited(client, auth, parties):
    result = client.get(
        "/api/v1/parties/duplicates",
        params={"party_type": "CUSTOMER", "name": "ABC Pipes", "exclude_id": parties["customer"]},
        headers=auth,
    ).json()
    assert all(c["id"] != parties["customer"] for c in result["candidates"])


def test_quick_create_refuses_a_colliding_gst(client, auth, masters):
    client.post(
        "/api/v1/parties",
        json={"name": "Known Co", "party_type": "CUSTOMER", "gst_number": "24AABCZ1111A1Z5"},
        headers=auth,
    )
    response = client.post(
        "/api/v1/activities",
        json={
            "new_party": {
                "name": "Same GST Co",
                "gst_number": "24aabcz1111a1z5",
                "party_type": "CUSTOMER",
            },
            "activity_type": "CALL",
            "scheduled_at": _soon(),
        },
        headers=auth,
    )
    assert response.status_code == 409
    assert "already belongs to 'Known Co'" in response.json()["error"]["message"]


# --------------------------------------------------------------------------- #
# Name uniqueness: strict for verified parties, relaxed for prospects
# --------------------------------------------------------------------------- #
def test_two_prospects_may_share_a_name(client, auth):
    first = _prospect(client, auth, "Patel Traders")
    second = _prospect(client, auth, "Patel Traders")
    assert first["id"] != second["id"]


def test_verified_parties_still_need_a_unique_name(client, auth, parties):
    response = client.post(
        "/api/v1/parties", json={"name": "abc pipes", "party_type": "CUSTOMER"}, headers=auth
    )
    assert response.status_code == 409


def test_promoting_into_a_name_clash_is_refused(client, auth, masters, parties):
    prospect = _prospect(client, auth, "ABC Pipes")
    response = client.post(f"/api/v1/parties/{prospect['id']}/promote", headers=auth)
    assert response.status_code == 409
    assert "already exists" in response.json()["error"]["message"]


# --------------------------------------------------------------------------- #
# Promotion
# --------------------------------------------------------------------------- #
def test_closing_an_inquiry_leaves_the_prospect_as_it_is(client, auth, masters):
    """Promotion is a deliberate act on the party page, not a side effect."""
    party = _prospect(client, auth, "Still Cold Co")
    inquiry = _customer_inquiry(client, auth, masters, customer_id=party["id"]).json()
    client.patch(f"/api/v1/inquiries/{inquiry['id']}", json={"status": "CLOSED"}, headers=auth)
    assert client.get(f"/api/v1/parties/{party['id']}", headers=auth).json()["stage"] == "PROSPECT"


def test_promote_is_idempotent(client, auth, masters):
    prospect = _prospect(client, auth, "Promote Me")
    assert client.post(f"/api/v1/parties/{prospect['id']}/promote", headers=auth).status_code == 200
    again = client.post(f"/api/v1/parties/{prospect['id']}/promote", headers=auth)
    assert again.status_code == 200
    assert again.json()["stage"] == "ACTIVE"


# --------------------------------------------------------------------------- #
# Listing
# --------------------------------------------------------------------------- #
def test_prospects_can_be_listed_separately(client, auth, masters, parties):
    _prospect(client, auth, "Lead One")
    prospects = client.get(
        "/api/v1/parties", params={"party_type": "CUSTOMER", "stage": "PROSPECT"}, headers=auth
    ).json()
    assert [item["name"] for item in prospects["items"]] == ["Lead One"]

    verified = client.get(
        "/api/v1/parties", params={"party_type": "CUSTOMER", "stage": "ACTIVE"}, headers=auth
    ).json()
    assert "Lead One" not in [item["name"] for item in verified["items"]]


def test_stale_prospects_list_only_untouched_leads(client, auth, masters, db_session):
    from datetime import timedelta as delta

    from app.models import Party

    touched = _prospect(client, auth, "Touched Lead")["id"]
    _customer_inquiry(client, auth, masters, customer_id=touched)
    untouched = client.post(
        "/api/v1/parties",
        json={"name": "Forgotten Lead", "party_type": "CUSTOMER", "stage": "PROSPECT"},
        headers=auth,
    ).json()["id"]

    # Age both of them.
    old = datetime.now(UTC) - delta(days=90)
    for party_id in (touched, untouched):
        db_session.get(Party, party_id).created_at = old
    db_session.flush()

    stale = client.get("/api/v1/parties", params={"stale_days": 60}, headers=auth).json()
    ids = [item["id"] for item in stale["items"]]
    assert untouched in ids
    assert touched not in ids  # it has an inquiry, so it is not stale


# --------------------------------------------------------------------------- #
# Merge
# --------------------------------------------------------------------------- #
@pytest.fixture
def merge_pair(client, auth, masters, parties, salesperson):
    """A verified party and a duplicate prospect carrying real history."""
    survivor = parties["customer"]
    loser = _prospect(client, auth, "ABC Pipes (walk-in)", "+91 98250 11001")["id"]
    inquiry = _customer_inquiry(client, auth, masters, customer_id=loser).json()

    client.post(
        "/api/v1/activities",
        json={
            "party_id": loser,
            "activity_type": "CALL",
            "scheduled_at": _soon(),
            "assigned_salesperson_id": salesperson.id,
        },
        headers=auth,
    )
    client.post(
        "/api/v1/notes", json={"party_id": loser, "note": "Met at the market."}, headers=auth
    )
    client.post(
        f"/api/v1/parties/{loser}/products",
        json={"product_id": masters["product_id"]},
        headers=auth,
    )
    return {"survivor": survivor, "loser": loser, "inquiry_id": inquiry["id"]}


def test_merge_moves_all_history(client, auth, merge_pair, masters):
    response = client.post(
        f"/api/v1/parties/{merge_pair['survivor']}/merge",
        json={"loser_id": merge_pair["loser"], "note": "Same shop, entered twice."},
        headers=auth,
    )
    assert response.status_code == 200, response.text
    moved = response.json()["moved"]
    assert moved["customer_inquiries"] == 1
    assert moved["activities"] == 1
    assert moved["notes"] == 1

    overview = client.get(f"/api/v1/parties/{merge_pair['survivor']}/overview", headers=auth).json()
    assert any(
        item["id"] == merge_pair["inquiry_id"]
        for item in overview["open_inquiries"] + overview["inquiry_history"]
    )
    assert overview["stats"]["activities"] == 1
    assert overview["stats"]["notes"] == 1
    assert "Same shop, entered twice." in (overview["party"]["notes"] or "")


def test_merge_retires_the_duplicate_without_deleting_it(client, auth, merge_pair):
    client.post(
        f"/api/v1/parties/{merge_pair['survivor']}/merge",
        json={"loser_id": merge_pair["loser"]},
        headers=auth,
    )
    loser = client.get(f"/api/v1/parties/{merge_pair['loser']}", headers=auth)
    assert loser.status_code == 200  # old links still resolve
    assert loser.json()["stage"] == "MERGED"
    assert loser.json()["status"] == "INACTIVE"
    assert loser.json()["merged_into_id"] == merge_pair["survivor"]

    listed = client.get("/api/v1/parties", params={"party_type": "CUSTOMER"}, headers=auth).json()
    assert merge_pair["loser"] not in [item["id"] for item in listed["items"]]
    with_merged = client.get(
        "/api/v1/parties", params={"party_type": "CUSTOMER", "include_merged": True}, headers=auth
    ).json()
    assert merge_pair["loser"] in [item["id"] for item in with_merged["items"]]


def test_merge_dedupes_colliding_product_links(client, auth, merge_pair, masters):
    # Both parties claim the same product with the same relationship.
    client.post(
        f"/api/v1/parties/{merge_pair['survivor']}/products",
        json={"product_id": masters["product_id"]},
        headers=auth,
    )
    response = client.post(
        f"/api/v1/parties/{merge_pair['survivor']}/merge",
        json={"loser_id": merge_pair["loser"]},
        headers=auth,
    )
    assert response.status_code == 200, response.text
    assert response.json()["moved"].get("party_products_deduped") == 1
    links = client.get(f"/api/v1/parties/{merge_pair['survivor']}/products", headers=auth).json()
    assert len(links) == 1


def test_merged_party_cannot_be_used_for_new_business(client, auth, masters, merge_pair):
    client.post(
        f"/api/v1/parties/{merge_pair['survivor']}/merge",
        json={"loser_id": merge_pair["loser"]},
        headers=auth,
    )
    inquiry = _customer_inquiry(client, auth, masters, customer_id=merge_pair["loser"])
    assert inquiry.status_code == 422
    assert "merged into" in inquiry.json()["error"]["message"]

    activity = client.post(
        "/api/v1/activities",
        json={
            "party_id": merge_pair["loser"],
            "activity_type": "CALL",
            "scheduled_at": _soon(),
        },
        headers=auth,
    )
    assert activity.status_code == 422


def test_merge_is_admin_only_and_type_safe(client, auth, desk_auth, parties, merge_pair):
    assert (
        client.post(
            f"/api/v1/parties/{merge_pair['survivor']}/merge",
            json={"loser_id": merge_pair["loser"]},
            headers=desk_auth,
        ).status_code
        == 403
    )
    cross_type = client.post(
        f"/api/v1/parties/{parties['supplier']}/merge",
        json={"loser_id": merge_pair["loser"]},
        headers=auth,
    )
    assert cross_type.status_code == 422
    assert "Cannot merge" in cross_type.json()["error"]["message"]
    assert (
        client.post(
            f"/api/v1/parties/{merge_pair['survivor']}/merge",
            json={"loser_id": merge_pair["survivor"]},
            headers=auth,
        ).status_code
        == 422
    )


def test_merge_is_audited(client, auth, merge_pair):
    client.post(
        f"/api/v1/parties/{merge_pair['survivor']}/merge",
        json={"loser_id": merge_pair["loser"]},
        headers=auth,
    )
    rows = client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "party", "entity_id": merge_pair["survivor"]},
        headers=auth,
    ).json()["items"]
    merge_row = next(row for row in rows if row["action"] == "MERGE")
    assert merge_row["old_value"]["merged_party_id"] == merge_pair["loser"]


def test_salesperson_cannot_create_or_merge_parties(client, sales_auth, parties, masters):
    assert (
        client.get(
            "/api/v1/parties/duplicates", params={"name": "abc"}, headers=sales_auth
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/parties/{parties['customer']}/merge",
            json={"loser_id": parties["other_customer"]},
            headers=sales_auth,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/parties/{parties['customer']}/promote", headers=sales_auth
        ).status_code
        == 403
    )
    # And no backdoor through the activity form's inline party creation.
    assert (
        client.post(
            "/api/v1/activities",
            json={
                "new_party": {"name": "Field Lead", "party_type": "CUSTOMER"},
                "activity_type": "CALL",
                "scheduled_at": _soon(),
            },
            headers=sales_auth,
        ).status_code
        == 403
    )


def test_merged_duplicate_does_not_block_promoting_the_survivor(client, auth, masters, merge_pair):
    """A merged row keeps its name for history, but must not reserve it."""
    client.post(
        f"/api/v1/parties/{merge_pair['survivor']}/merge",
        json={"loser_id": merge_pair["loser"]},
        headers=auth,
    )
    prospect = _prospect(client, auth, "Namesake Co", "+91 90066 00066")
    # Retire a namesake, then promote: the merged row must not stand in the way.
    other = client.post(
        "/api/v1/parties",
        json={"name": "Namesake Co", "party_type": "CUSTOMER"},
        headers=auth,
    ).json()
    client.post(
        f"/api/v1/parties/{other['id']}/merge", json={"loser_id": prospect["id"]}, headers=auth
    )
    revived = _prospect(client, auth, "Namesake Co", "+91 90077 00077")
    # The live namesake still blocks it...
    assert client.post(f"/api/v1/parties/{revived['id']}/promote", headers=auth).status_code == 409
    # ...but once that one is merged away, promotion works.
    client.patch(f"/api/v1/parties/{other['id']}", json={"name": "Namesake Co Ltd"}, headers=auth)
    assert client.post(f"/api/v1/parties/{revived['id']}/promote", headers=auth).status_code == 200


def test_phone_dedupe_key_is_maintained_by_the_mapper(client, auth, db_session, parties):
    """Any write path - service, seed or importer - must keep the key in step."""
    from app.models import Party

    # Written straight through the ORM, the way the seed script does it.
    party = db_session.get(Party, parties["customer"])
    party.phone = "+91 98250 11001"
    db_session.flush()
    assert party.phone_normalized == "9825011001"

    found = client.get(
        "/api/v1/parties/duplicates",
        params={"party_type": "CUSTOMER", "phone": "098250-11001"},
        headers=auth,
    ).json()
    assert found["has_exact_match"] is True
    assert found["candidates"][0]["id"] == parties["customer"]

    # Clearing the phone clears the key.
    party.phone = None
    db_session.flush()
    assert party.phone_normalized is None


def test_exact_identifier_outranks_a_perfect_name_match(client, auth):
    """A matching phone must not be masked by an identical name elsewhere."""
    same_phone = client.post(
        "/api/v1/parties",
        json={"name": "Different Name Co", "party_type": "CUSTOMER", "phone": "+91 98777 66001"},
        headers=auth,
    ).json()
    client.post(
        "/api/v1/parties",
        json={"name": "Shared Name Co", "party_type": "CUSTOMER", "phone": "+91 91111 22222"},
        headers=auth,
    )

    result = client.get(
        "/api/v1/parties/duplicates",
        params={"party_type": "CUSTOMER", "name": "Shared Name Co", "phone": "+91 98777 66001"},
        headers=auth,
    ).json()
    assert result["has_exact_match"] is True
    # The phone match leads, even though the other name matches perfectly.
    assert result["candidates"][0]["id"] == same_phone["id"]
    assert result["candidates"][0]["match_reason"] == "exact_phone"
    assert [c["match_reason"] for c in result["candidates"]][1] == "similar_name"
