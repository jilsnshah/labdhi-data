"""Enquiries a party raises through their own link.

What these are really about. A party sends an enquiry and it is on the book -
no queue, no approval - which means the form has to turn what somebody typed on
a phone into rows: a material, a grade of it, a manufacturer, the product the
three make, and the town they named. Anything missing from our master data is
created as they go, matched case-insensitively first so "pvc" and "PVC" never
become two materials.

And the form still cannot be talked into lying about who is asking or what kind
of enquiry it is: both come from the code in the link.
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


def product_of(masters: dict) -> dict:
    """The three names that make the seeded Reliance PVC K-67."""
    return {
        "material_id": masters["material_id"],
        "grade_id": masters["grade_id"],
        "manufacturer_id": masters["manufacturer_id"],
    }


def send(client, code: str, **payload):
    return client.post(f"/api/v1/portal/{code}/enquiries", json=payload)


def inbox(client, auth, **params) -> list[dict]:
    response = client.get("/api/v1/portal-enquiries", params=params, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()["items"]


def inquiries(client, auth, **params) -> list[dict]:
    response = client.get("/api/v1/inquiries", params=params, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()["items"]


def detail_of(client, auth, row: dict, block: str) -> dict:
    return client.get(f"/api/v1/inquiries/{row['id']}", headers=auth).json()[block]


def masters_named(client, auth, kind: str, **params) -> list[str]:
    rows = client.get(f"/api/v1/{kind}", params={"page_size": 100, **params}, headers=auth).json()[
        "items"
    ]
    return [row["name"] for row in rows]


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
    assert send(client, "notarealcodeatall", quantity="20").status_code == 404
    assert client.get("/api/v1/portal/notarealcodeatall/enquiries").status_code == 404
    assert client.get("/api/v1/portal/notarealcodeatall/materials").status_code == 404


def test_the_desk_endpoints_need_signing_in(client, auth, parties, masters, code_of):
    send(client, code_of(parties["customer"]), **product_of(masters), quantity="20")
    assert client.get("/api/v1/portal-enquiries").status_code == 401


# --- an enquiry lands as an inquiry ------------------------------------------ #
def test_a_customer_enquiry_is_an_inquiry_the_moment_it_arrives(
    client, auth, parties, masters, code_of
):
    """No queue and nobody to approve it: the desk sees it in the book."""
    code = code_of(parties["customer"])
    response = send(
        client, code, **product_of(masters), quantity="20", to_place="Rajkot", rate="91.50"
    )
    assert response.status_code == 200, response.text

    rows = inquiries(client, auth)
    assert len(rows) == 1
    row = rows[0]
    assert row["inquiry_type"] == "CUSTOMER"
    assert row["status"] == "ACTIVE"
    assert row["source"] == "PORTAL", "told apart from the desk's own work"
    assert row["created_by"] is None, "there is no salesperson to name"

    detail = detail_of(client, auth, row, "customer_detail")
    assert detail["customer"]["name"] == "ABC Pipes"
    assert detail["product"]["display_name"] == "Reliance PVC K-67"
    assert detail["quantity"] == "20.000"
    assert detail["rate"] == "91.50"
    assert detail["location"]["city"] == "Rajkot"


def test_a_supplier_enquiry_asks_for_no_place(client, auth, parties, masters, code_of):
    """A supplier is not asked where it ships from, so the inquiry carries none."""
    code = code_of(parties["supplier"])
    assert send(client, code, **product_of(masters), quantity="25").status_code == 200

    row = inquiries(client, auth)[0]
    assert row["inquiry_type"] == "SUPPLIER"
    detail = detail_of(client, auth, row, "supplier_detail")
    assert detail["supplier"]["name"] == "Mahavir Polymers"
    assert detail["location"] is None


def test_a_transporter_raises_a_load_between_two_towns(client, auth, parties, code_of):
    code = code_of(parties["transporter"])
    sent = send(
        client, code, quantity="20", from_place="Gandhidham", to_place="Mumbai", rate="18000"
    )
    assert sent.status_code == 200, sent.text

    row = inquiries(client, auth)[0]
    assert row["inquiry_type"] == "TRANSPORT"
    detail = detail_of(client, auth, row, "transport_detail")
    assert detail["transporter"]["name"] == "Jay Transport"
    assert detail["pickup_location"]["city"] == "Gandhidham"
    assert detail["delivery_location"]["city"] == "Mumbai"
    assert detail["price"] == "18000.00"


def test_the_party_decides_nothing_about_which_book_it_goes_in(
    client, auth, parties, masters, code_of
):
    """Their own type settles it; the payload has no say."""
    send(client, code_of(parties["customer"]), **product_of(masters), quantity="5")
    send(client, code_of(parties["supplier"]), **product_of(masters), quantity="5")

    assert {row["inquiry_type"] for row in inquiries(client, auth)} == {"CUSTOMER", "SUPPLIER"}


def test_a_load_without_both_ends_is_refused(client, auth, parties, code_of):
    code = code_of(parties["transporter"])
    assert send(client, code, quantity="20", from_place="Gandhidham").status_code == 422
    assert inquiries(client, auth) == []


def test_a_load_that_goes_nowhere_is_refused(client, auth, parties, code_of):
    code = code_of(parties["transporter"])
    response = send(client, code, quantity="20", from_place="Rajkot", to_place="rajkot")

    assert response.status_code == 422
    assert "same place" in response.text


def test_nonsense_quantities_are_refused(client, auth, parties, masters, code_of):
    code = code_of(parties["customer"])
    for quantity in ("0", "-5"):
        assert send(client, code, **product_of(masters), quantity=quantity).status_code == 422


# --- master data a party creates as they go ---------------------------------- #
def test_a_material_we_do_not_carry_is_created(client, auth, parties, masters, code_of):
    code = code_of(parties["customer"])
    response = send(
        client,
        code,
        material_text="LLDPE",
        grade_text="Grade 1020",
        manufacturer_text="GAIL",
        quantity="15",
    )
    assert response.status_code == 200, response.text

    assert "LLDPE" in masters_named(client, auth, "materials")
    assert "Grade 1020" in masters_named(client, auth, "grades")
    assert "GAIL" in masters_named(client, auth, "manufacturers")

    row = inquiries(client, auth)[0]
    assert (
        detail_of(client, auth, row, "customer_detail")["product"]["display_name"]
        == "GAIL LLDPE Grade 1020"
    )


def test_a_name_we_already_have_is_not_created_twice(client, auth, parties, masters, code_of):
    """'pvc' and 'PVC' are the same material; a list holding both is useless."""
    code = code_of(parties["customer"])
    send(
        client,
        code,
        material_text="pvc",
        grade_text="k-67",
        manufacturer_text="reliance",
        quantity="12",
    )

    names = masters_named(client, auth, "materials")
    assert names.count("PVC") == 1
    assert "pvc" not in names
    row = inquiries(client, auth)[0]
    detail = detail_of(client, auth, row, "customer_detail")
    assert detail["product"]["id"] == masters["product_id"], "the product we already had"


def test_a_new_combination_of_known_names_becomes_a_new_product(
    client, auth, parties, masters, code_of
):
    """Someone else's PVC K-67 is a product we simply have not traded before."""
    code = code_of(parties["customer"])
    send(
        client,
        code,
        material_id=masters["material_id"],
        grade_id=masters["grade_id"],
        manufacturer_text="Finolex",
        quantity="8",
    )

    products = client.get("/api/v1/products", params={"page_size": 50}, headers=auth).json()
    names = [row["display_name"] for row in products["items"]]
    assert "Finolex PVC K-67" in names
    assert "Reliance PVC K-67" in names, "the one we had is untouched"


def test_a_grade_belongs_to_the_material_it_was_named_under(
    client, auth, parties, masters, code_of
):
    """The same grade name under two materials is two different grades."""
    code = code_of(parties["customer"])
    send(
        client,
        code,
        material_id=masters["other_material_id"],
        grade_text="K-67",
        manufacturer_id=masters["manufacturer_id"],
        quantity="9",
    )

    under_hdpe = masters_named(client, auth, "grades", material_id=masters["other_material_id"])
    assert "K-67" in under_hdpe, "a second K-67, belonging to HDPE"
    assert "MFI 0.3" in under_hdpe, "the one HDPE already had"
    row = inquiries(client, auth)[0]
    detail = detail_of(client, auth, row, "customer_detail")
    assert detail["product"]["display_name"] == "Reliance HDPE K-67"


def test_a_grade_cannot_be_borrowed_from_another_material(client, auth, parties, masters, code_of):
    code = code_of(parties["customer"])
    response = send(
        client,
        code,
        material_id=masters["other_material_id"],
        grade_id=masters["grade_id"],
        manufacturer_id=masters["manufacturer_id"],
        quantity="9",
    )
    assert response.status_code == 422
    assert "different material" in response.text


def test_an_enquiry_naming_no_grade_at_all_is_refused(client, auth, parties, code_of):
    code = code_of(parties["customer"])
    assert send(client, code, quantity="15").status_code == 422
    assert inquiries(client, auth) == []


def test_a_town_becomes_a_location_once_not_every_time(client, auth, parties, masters, code_of):
    code = code_of(parties["customer"])
    send(client, code, **product_of(masters), quantity="10", to_place="Surat")
    send(client, code, **product_of(masters), quantity="11", to_place="surat")

    found = client.get("/api/v1/locations", params={"q": "Surat"}, headers=auth).json()
    assert found["total"] == 1


def test_what_a_party_created_carries_no_name_in_the_audit_log(client, auth, parties, code_of):
    """How the desk tells a party's additions from its own: nobody signed them."""
    code = code_of(parties["customer"])
    send(
        client,
        code,
        material_text="EVA",
        grade_text="VA 18",
        manufacturer_text="Hanwha",
        quantity="4",
    )

    logs = client.get(
        "/api/v1/audit-logs", params={"entity_type": "material", "page_size": 50}, headers=auth
    ).json()["items"]
    made = next(row for row in logs if (row["new_value"] or {}).get("name") == "EVA")
    assert made["user_id"] is None
    assert made["new_value"]["created_from"] == "portal"


def test_whitespace_a_phone_keyboard_leaves_behind_is_trimmed(client, auth, parties, code_of):
    code = code_of(parties["customer"])
    send(
        client,
        code,
        material_text="  PP  ",
        grade_text=" H110MA ",
        manufacturer_text=" IOCL ",
        quantity="10",
        notes="   ",
        to_place=" Rajkot ",
    )

    assert "PP" in masters_named(client, auth, "materials")
    row = inbox(client, auth)[0]
    assert row["notes"] is None, "all whitespace is nothing at all"
    assert row["to_place"] == "Rajkot"


# --- the pickers -------------------------------------------------------------- #
def test_the_pickers_offer_our_names_and_nothing_else(client, auth, parties, masters, code_of):
    code = code_of(parties["customer"])

    materials = client.get(f"/api/v1/portal/{code}/materials").json()
    assert {"PVC", "HDPE"} <= {row["name"] for row in materials}
    assert all(set(row) == {"id", "name"} for row in materials)

    narrowed = client.get(f"/api/v1/portal/{code}/materials", params={"q": "pv"}).json()
    assert [row["name"] for row in narrowed] == ["PVC"]
    assert client.get(f"/api/v1/portal/{code}/materials", params={"q": "zzz"}).json() == []


def test_the_grade_picker_only_shows_grades_of_that_material(
    client, auth, parties, masters, code_of
):
    code = code_of(parties["customer"])
    grades = client.get(
        f"/api/v1/portal/{code}/grades", params={"material_id": masters["material_id"]}
    ).json()

    assert [row["name"] for row in grades] == ["K-67"]


def test_the_manufacturer_picker_works_the_same_way(client, auth, parties, masters, code_of):
    code = code_of(parties["customer"])
    rows = client.get(f"/api/v1/portal/{code}/manufacturers", params={"q": "rel"}).json()
    assert [row["name"] for row in rows] == ["Reliance"]


# --- what each side sees afterwards ------------------------------------------- #
def test_a_party_sees_their_own_enquiries_and_nobody_elses(client, auth, parties, masters, code_of):
    mine = code_of(parties["customer"])
    theirs = code_of(parties["other_customer"])
    send(client, mine, **product_of(masters), quantity="20")
    send(client, theirs, **product_of(masters), quantity="30")

    rows = client.get(f"/api/v1/portal/{mine}/enquiries").json()
    assert [row["quantity"] for row in rows] == ["20.000"]
    assert "XYZ Polymers" not in str(rows)
    assert "inquiry_id" not in rows[0], "what we did with it is the desk's record"


def test_the_desk_sees_what_was_typed_beside_the_inquiry_it_became(
    client, auth, parties, masters, code_of
):
    """The log earns its keep: an inquiry holds neither their note nor their words."""
    code = code_of(parties["customer"])
    send(
        client,
        code,
        **product_of(masters),
        quantity="20",
        to_place="Rajkot",
        notes="Need it before Diwali.",
    )

    row = inbox(client, auth)[0]
    assert row["party"]["name"] == "ABC Pipes"
    assert row["notes"] == "Need it before Diwali."
    assert row["to_place"] == "Rajkot"
    assert row["inquiry_id"] == inquiries(client, auth)[0]["id"]


def test_the_log_filters_the_way_the_other_lists_do(client, auth, parties, masters, code_of):
    send(client, code_of(parties["customer"]), **product_of(masters), quantity="20")
    send(client, code_of(parties["transporter"]), quantity="9", from_place="Surat", to_place="Pune")

    assert len(inbox(client, auth)) == 2
    assert len(inbox(client, auth, inquiry_type="TRANSPORT")) == 1
    assert len(inbox(client, auth, party_id=parties["customer"])) == 1
    assert len(inbox(client, auth, material_id=masters["material_id"])) == 1
    assert len(inbox(client, auth, grade_id=masters["other_grade_id"])) == 0
    assert len(inbox(client, auth, q="Surat")) == 1
    assert len(inbox(client, auth, q="ABC")) == 1


def test_the_log_pages(client, auth, parties, masters, code_of):
    """A hundred parties could write in overnight."""
    code = code_of(parties["customer"])
    for n in range(1, 8):
        send(client, code, **product_of(masters), quantity=str(n))

    page = client.get(
        "/api/v1/portal-enquiries", params={"page": 2, "page_size": 3}, headers=auth
    ).json()
    assert page["total"] == 7
    assert len(page["items"]) == 3


def test_an_inquiry_the_desk_keyed_in_is_still_its_own(client, auth, parties, masters, locations):
    """The new column must not quietly relabel everything already on the book."""
    created = client.post(
        "/api/v1/inquiries",
        json={
            "inquiry_type": "CUSTOMER",
            "customer": {
                "customer_id": parties["customer"],
                "product_id": masters["product_id"],
                "quantity": "20",
                "location_id": locations["delivery_id"],
            },
        },
        headers=auth,
    ).json()

    assert created["source"] == "DESK"
    assert created["created_by"] is not None
