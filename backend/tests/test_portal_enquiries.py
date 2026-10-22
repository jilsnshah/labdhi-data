"""Enquiries a party raises through their own link.

Two things these tests are really about. First, that a public form cannot put
anything in the book: what arrives is a request in the party's own words, and
only the desk, by accepting it, turns one into an inquiry. Second, that the
form cannot be talked into lying about who is asking or what kind of enquiry it
is - both come from the code in the link, never from the payload.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def code_of(client, auth):
    """The portal code for a party, as the desk would copy it."""

    def get(party_id: int) -> str:
        response = client.get(f"/api/v1/portal-enquiries/link/{party_id}", headers=auth)
        assert response.status_code == 200, response.text
        return response.json()["enquiry_link"].split("/portal/")[1].split("/")[0]

    return get


def send(client, code: str, **payload):
    return client.post(f"/api/v1/portal/{code}/enquiries", json=payload)


def inbox(client, auth, **params) -> list[dict]:
    response = client.get("/api/v1/portal-enquiries", params=params, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()["items"]


# --- the link ---------------------------------------------------------------- #
def test_every_party_has_an_enquiry_link_issued_on_demand(client, auth, parties):
    """One code per party, the same one their bid links use."""
    first = client.get(f"/api/v1/portal-enquiries/link/{parties['customer']}", headers=auth).json()
    again = client.get(f"/api/v1/portal-enquiries/link/{parties['customer']}", headers=auth).json()

    assert first["enquiry_link"].endswith("/enquire")
    assert first["enquiry_link"] == again["enquiry_link"], "the code is permanent"
    assert first["portal_link"] in first["enquiry_link"]


def test_the_link_is_the_only_way_in(client, parties):
    """No code, no enquiry - and a wrong code tells a stranger nothing."""
    assert send(client, "notarealcodeatall", quantity="20", product_text="PVC").status_code == 404
    assert client.get("/api/v1/portal/notarealcodeatall/enquiries").status_code == 404


def test_the_desk_endpoints_need_signing_in(client, auth, parties, code_of):
    code = code_of(parties["customer"])
    send(client, code, quantity="20", product_text="PVC K-67")

    assert client.get("/api/v1/portal-enquiries").status_code == 401
    assert client.get("/api/v1/portal-enquiries/counts").status_code == 401


# --- what the party sends --------------------------------------------------- #
def test_a_customer_raises_a_customer_enquiry(client, auth, parties, masters, code_of):
    """The party's own type decides the book it goes in. The form cannot."""
    code = code_of(parties["customer"])
    response = send(
        client,
        code,
        product_id=masters["product_id"],
        quantity="20",
        unit="MT",
        to_place="Rajkot",
        rate="91.50",
        notes="Need it by Friday.",
    )

    assert response.status_code == 200, response.text
    sent = response.json()
    assert sent["inquiry_type"] == "CUSTOMER"
    assert sent["status"] == "NEW"
    assert sent["product_name"] == "Reliance PVC K-67"
    assert sent["rate"] == "91.50"


def test_a_supplier_raises_a_supplier_enquiry(client, auth, parties, masters, code_of):
    code = code_of(parties["supplier"])
    sent = send(
        client, code, product_id=masters["product_id"], quantity="25", from_place="Ahmedabad"
    ).json()

    assert sent["inquiry_type"] == "SUPPLIER"
    assert sent["from_place"] == "Ahmedabad"


def test_a_transporter_raises_a_load(client, auth, parties, code_of):
    code = code_of(parties["transporter"])
    sent = send(
        client, code, quantity="20", from_place="Gandhidham", to_place="Mumbai", rate="18000"
    ).json()

    assert sent["inquiry_type"] == "TRANSPORT"
    assert sent["product_name"] is None, "a load carries no product"


def test_a_load_without_both_ends_is_refused(client, auth, parties, code_of):
    code = code_of(parties["transporter"])
    response = send(client, code, quantity="20", from_place="Gandhidham")

    assert response.status_code == 422
    assert "picked up" in response.text


def test_a_party_may_type_a_grade_we_do_not_carry(client, auth, parties, code_of):
    """They cannot be expected to know our master data, only what they want."""
    code = code_of(parties["customer"])
    sent = send(client, code, product_text="Finolex K-70 or similar", quantity="15").json()

    assert sent["product_name"] == "Finolex K-70 or similar"
    row = inbox(client, auth)[0]
    assert row["product"] is None
    assert row["product_text"] == "Finolex K-70 or similar"


def test_an_enquiry_for_nothing_in_particular_is_refused(client, auth, parties, code_of):
    code = code_of(parties["customer"])
    response = send(client, code, quantity="15")

    assert response.status_code == 422
    assert "material or grade" in response.text


def test_a_product_we_do_not_carry_is_refused(client, auth, parties, code_of):
    code = code_of(parties["customer"])
    assert send(client, code, product_id=99999, quantity="15").status_code == 422


def test_nonsense_quantities_are_refused(client, auth, parties, masters, code_of):
    code = code_of(parties["customer"])
    for quantity in ("0", "-5"):
        response = send(client, code, product_id=masters["product_id"], quantity=quantity)
        assert response.status_code == 422, quantity


def test_whitespace_a_phone_keyboard_leaves_behind_is_trimmed(client, auth, parties, code_of):
    code = code_of(parties["customer"])
    sent = send(
        client, code, product_text="  PVC K-67  ", quantity="10", notes="   ", to_place=" Rajkot "
    ).json()

    assert sent["product_name"] == "PVC K-67"
    assert sent["notes"] is None, "all whitespace is nothing at all"
    assert sent["to_place"] == "Rajkot"


def test_a_party_sees_their_own_enquiries_and_nobody_elses(client, auth, parties, masters, code_of):
    mine = code_of(parties["customer"])
    theirs = code_of(parties["other_customer"])
    send(client, mine, product_id=masters["product_id"], quantity="20")
    send(client, theirs, product_id=masters["product_id"], quantity="30")

    rows = client.get(f"/api/v1/portal/{mine}/enquiries").json()
    assert [row["quantity"] for row in rows] == ["20.000"]
    assert "XYZ Polymers" not in str(rows)


def test_the_picker_offers_grades_by_name(client, auth, parties, masters, code_of):
    code = code_of(parties["customer"])

    everything = client.get(f"/api/v1/portal/{code}/products").json()
    assert any(row["display_name"] == "Reliance PVC K-67" for row in everything)

    found = client.get(f"/api/v1/portal/{code}/products", params={"q": "k-67"}).json()
    assert [row["display_name"] for row in found] == ["Reliance PVC K-67"]
    assert client.get(f"/api/v1/portal/{code}/products", params={"q": "zzz"}).json() == []


def test_the_picker_shows_nothing_but_products(client, auth, parties, masters, code_of):
    """It is the one piece of our data a public caller may read, so: just names."""
    code = code_of(parties["customer"])
    rows = client.get(f"/api/v1/portal/{code}/products").json()

    assert all(set(row) == {"id", "display_name"} for row in rows)


# --- the desk's inbox -------------------------------------------------------- #
def test_an_enquiry_appears_in_the_desk_inbox_at_once(client, auth, parties, masters, code_of):
    code = code_of(parties["customer"])
    send(client, code, product_id=masters["product_id"], quantity="20", to_place="Rajkot")

    row = inbox(client, auth)[0]
    assert row["party"]["name"] == "ABC Pipes"
    assert row["status"] == "NEW"
    assert row["inquiry_id"] is None
    assert row["handled_at"] is None

    counts = client.get("/api/v1/portal-enquiries/counts", headers=auth).json()
    assert counts == {"new": 1, "accepted": 0, "declined": 0}


def test_what_is_waiting_is_read_first(client, auth, parties, masters, code_of):
    code = code_of(parties["customer"])
    send(client, code, product_id=masters["product_id"], quantity="10")
    second = send(client, code, product_id=masters["product_id"], quantity="20").json()
    client.post(f"/api/v1/portal-enquiries/{second['id']}/decline", headers=auth)

    rows = inbox(client, auth)
    assert [row["status"] for row in rows] == ["NEW", "DECLINED"]


def test_the_inbox_filters_the_way_the_other_lists_do(client, auth, parties, masters, code_of):
    send(client, code_of(parties["customer"]), product_id=masters["product_id"], quantity="20")
    send(client, code_of(parties["transporter"]), quantity="9", from_place="Surat", to_place="Pune")

    assert len(inbox(client, auth)) == 2
    assert len(inbox(client, auth, inquiry_type="TRANSPORT")) == 1
    assert len(inbox(client, auth, party_id=parties["customer"])) == 1
    assert len(inbox(client, auth, material_id=masters["material_id"])) == 1
    assert len(inbox(client, auth, grade_id=masters["other_grade_id"])) == 0
    assert len(inbox(client, auth, q="Surat")) == 1
    assert len(inbox(client, auth, q="ABC")) == 1


def test_the_inbox_pages(client, auth, parties, masters, code_of):
    """A hundred parties could write in overnight."""
    code = code_of(parties["customer"])
    for n in range(1, 8):
        send(client, code, product_id=masters["product_id"], quantity=str(n))

    page = client.get(
        "/api/v1/portal-enquiries", params={"page": 2, "page_size": 3}, headers=auth
    ).json()
    assert page["total"] == 7
    assert len(page["items"]) == 3


# --- accepting and declining ------------------------------------------------- #
def test_accepting_creates_the_inquiry_the_party_asked_for(
    client, auth, parties, masters, locations, code_of
):
    code = code_of(parties["customer"])
    sent = send(
        client,
        code,
        product_id=masters["product_id"],
        quantity="20",
        to_place="Rajkot",
        rate="91.5",
    ).json()

    accepted = client.post(
        f"/api/v1/portal-enquiries/{sent['id']}/accept",
        json={"location_id": locations["delivery_id"]},
        headers=auth,
    )
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["status"] == "ACCEPTED"
    assert body["inquiry_id"] is not None
    assert body["handler"]["name"] == "Test Admin", "who accepted it is on the record"

    inquiry = client.get(f"/api/v1/inquiries/{body['inquiry_id']}", headers=auth).json()
    detail = inquiry["customer_detail"]
    assert inquiry["inquiry_type"] == "CUSTOMER"
    assert detail["customer"]["name"] == "ABC Pipes"
    assert detail["product"]["id"] == masters["product_id"]
    assert detail["quantity"] == "20.000"
    assert detail["rate"] == "91.50", "their own rate, unless the desk changes it"


def test_the_desk_can_correct_what_the_party_sent(
    client, auth, parties, masters, locations, code_of
):
    """What arrives is a starting point, not a record."""
    code = code_of(parties["customer"])
    sent = send(client, code, product_text="something like K-67", quantity="20", rate="91.5").json()

    accepted = client.post(
        f"/api/v1/portal-enquiries/{sent['id']}/accept",
        json={
            "product_id": masters["product_id"],
            "location_id": locations["delivery_id"],
            "quantity": "18",
            "rate": "90.25",
        },
        headers=auth,
    ).json()

    inquiry = client.get(f"/api/v1/inquiries/{accepted['inquiry_id']}", headers=auth).json()
    assert inquiry["customer_detail"]["quantity"] == "18.000"
    assert inquiry["customer_detail"]["rate"] == "90.25"
    row = client.get(f"/api/v1/portal-enquiries/{sent['id']}", headers=auth).json()
    assert row["product_text"] == "something like K-67", "their words are kept as written"
    assert row["quantity"] == "20.000"


def test_a_typed_grade_cannot_be_accepted_without_naming_the_product(
    client, auth, parties, locations, code_of
):
    code = code_of(parties["customer"])
    sent = send(client, code, product_text="Finolex K-70", quantity="20").json()

    response = client.post(
        f"/api/v1/portal-enquiries/{sent['id']}/accept",
        json={"location_id": locations["delivery_id"]},
        headers=auth,
    )
    assert response.status_code == 422
    assert "product" in response.text.lower()


def test_accepting_a_load_needs_both_locations(client, auth, parties, locations, code_of):
    code = code_of(parties["transporter"])
    sent = send(client, code, quantity="20", from_place="Ahmedabad", to_place="Rajkot").json()

    half = client.post(
        f"/api/v1/portal-enquiries/{sent['id']}/accept",
        json={"pickup_location_id": locations["pickup_id"]},
        headers=auth,
    )
    assert half.status_code == 422

    whole = client.post(
        f"/api/v1/portal-enquiries/{sent['id']}/accept",
        json={
            "pickup_location_id": locations["pickup_id"],
            "delivery_location_id": locations["delivery_id"],
        },
        headers=auth,
    ).json()
    inquiry = client.get(f"/api/v1/inquiries/{whole['inquiry_id']}", headers=auth).json()
    assert inquiry["inquiry_type"] == "TRANSPORT"
    assert inquiry["transport_detail"]["transporter"]["name"] == "Jay Transport"


def test_declining_keeps_the_words_and_makes_no_inquiry(client, auth, parties, masters, code_of):
    code = code_of(parties["customer"])
    sent = send(client, code, product_id=masters["product_id"], quantity="20").json()

    declined = client.post(f"/api/v1/portal-enquiries/{sent['id']}/decline", headers=auth).json()
    assert declined["status"] == "DECLINED"
    assert declined["inquiry_id"] is None
    assert declined["handled_at"] is not None
    assert client.get("/api/v1/inquiries", headers=auth).json()["total"] == 0


def test_an_enquiry_is_decided_once(client, auth, parties, masters, locations, code_of):
    code = code_of(parties["customer"])
    sent = send(client, code, product_id=masters["product_id"], quantity="20").json()
    body = {"location_id": locations["delivery_id"]}

    first = client.post(f"/api/v1/portal-enquiries/{sent['id']}/accept", json=body, headers=auth)
    assert first.status_code == 200, first.text
    again = client.post(f"/api/v1/portal-enquiries/{sent['id']}/accept", json=body, headers=auth)
    assert again.status_code == 409
    assert (
        client.post(f"/api/v1/portal-enquiries/{sent['id']}/decline", headers=auth).status_code
        == 409
    )


def test_the_party_sees_that_it_was_read(client, auth, parties, masters, locations, code_of):
    """Somebody who sends something into a form is owed that much."""
    code = code_of(parties["customer"])
    sent = send(client, code, product_id=masters["product_id"], quantity="20").json()
    client.post(
        f"/api/v1/portal-enquiries/{sent['id']}/accept",
        json={"location_id": locations["delivery_id"]},
        headers=auth,
    )

    mine = client.get(f"/api/v1/portal/{code}/enquiries").json()
    assert mine[0]["status"] == "ACCEPTED"
    assert "inquiry_id" not in mine[0], "where it went is the desk's record, not theirs"
