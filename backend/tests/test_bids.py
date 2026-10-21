"""Bids: running a blind auction, and the wall around each participant.

The desk sees every quotation with a name on it. A participant sees the price
to beat and nothing else - not who else was asked, not what they wrote, not
even that the other bids exist. These tests are that wall.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def bid(client, auth, masters, parties):
    """An open customer bid with two customers invited."""
    created = client.post(
        "/api/v1/bids",
        json={
            "bid_type": "CUSTOMER",
            "product_id": masters["product_id"],
            "quantity": "30",
            "unit": "MT",
            "specifications": "Loose bags, ex-Ahmedabad.",
            "party_ids": [parties["customer"], parties["other_customer"]],
        },
        headers=auth,
    )
    assert created.status_code == 201, created.text
    bid_id = created.json()["id"]
    client.post(f"/api/v1/bids/{bid_id}/publish", headers=auth)
    detail = client.get(f"/api/v1/bids/{bid_id}", headers=auth).json()
    detail["participants"] = participants_of(client, auth, bid_id)
    return detail


def quotes_of(client, auth, bid_id: int, **params) -> list[dict]:
    """The offers on a bid, from the paginated endpoint the desk uses."""
    return client.get(f"/api/v1/bids/{bid_id}/quotes", params=params, headers=auth).json()["items"]


def participants_of(client, auth, bid_id: int, **params) -> list[dict]:
    return client.get(f"/api/v1/bids/{bid_id}/participants", params=params, headers=auth).json()[
        "items"
    ]


def code_of(bid: dict, party_id: int) -> str:
    """The portal code the desk would copy for one participant."""
    link = next(p["bid_link"] for p in bid["participants"] if p["party"]["id"] == party_id)
    return link.split("/portal/")[1].split("/")[0]


def quote(client, code: str, bid_id: int, price: str, **extra):
    return client.post(f"/api/v1/portal/{code}/bids/{bid_id}/quote", json={"price": price, **extra})


# --- raising a bid --------------------------------------------------------- #
def test_a_bid_starts_as_a_draft_and_is_invisible_until_opened(client, auth, masters, parties):
    created = client.post(
        "/api/v1/bids",
        json={
            "bid_type": "CUSTOMER",
            "product_id": masters["product_id"],
            "quantity": "10",
            "party_ids": [parties["customer"]],
        },
        headers=auth,
    ).json()
    assert created["status"] == "DRAFT"

    created["participants"] = participants_of(client, auth, created["id"])
    code = code_of(created, parties["customer"])
    assert client.get(f"/api/v1/portal/{code}/bids/{created['id']}").status_code == 404
    assert client.get(f"/api/v1/portal/{code}").json()["open_bids"] == []

    opened = client.post(f"/api/v1/bids/{created['id']}/publish", headers=auth).json()
    assert opened["status"] == "OPEN"
    assert client.get(f"/api/v1/portal/{code}/bids/{created['id']}").status_code == 200


def test_a_bid_goes_only_to_the_book_it_is_addressed_to(client, auth, masters, parties):
    response = client.post(
        "/api/v1/bids",
        json={
            "bid_type": "CUSTOMER",
            "product_id": masters["product_id"],
            "quantity": "10",
            "party_ids": [parties["supplier"]],
        },
        headers=auth,
    )
    assert response.status_code == 422
    assert "supplier" in response.json()["error"]["message"]


def test_a_transport_bid_needs_two_different_places(client, auth, parties, locations):
    missing = client.post(
        "/api/v1/bids", json={"bid_type": "TRANSPORT", "quantity": "20"}, headers=auth
    )
    same = client.post(
        "/api/v1/bids",
        json={
            "bid_type": "TRANSPORT",
            "quantity": "20",
            "pickup_location_id": locations["pickup_id"],
            "delivery_location_id": locations["pickup_id"],
        },
        headers=auth,
    )
    good = client.post(
        "/api/v1/bids",
        json={
            "bid_type": "TRANSPORT",
            "quantity": "20",
            "pickup_location_id": locations["pickup_id"],
            "delivery_location_id": locations["delivery_id"],
            "party_ids": [parties["transporter"]],
        },
        headers=auth,
    )
    assert missing.status_code == 422
    assert same.status_code == 422
    assert good.status_code == 201


def test_an_empty_bid_cannot_be_opened(client, auth, masters):
    created = client.post(
        "/api/v1/bids",
        json={"bid_type": "CUSTOMER", "product_id": masters["product_id"], "quantity": "5"},
        headers=auth,
    ).json()
    response = client.post(f"/api/v1/bids/{created['id']}/publish", headers=auth)
    assert response.status_code == 422
    assert "at least one participant" in response.json()["error"]["message"]


# --- the wall between participants ----------------------------------------- #
def test_a_participant_sees_the_price_to_beat_but_never_who_set_it(client, bid, parties):
    mine = code_of(bid, parties["customer"])
    theirs = code_of(bid, parties["other_customer"])

    quote(client, theirs, bid["id"], "95.50")
    seen = client.get(f"/api/v1/portal/{mine}/bids/{bid['id']}").json()

    assert seen["best_price"] == "95.50"
    assert seen["bidders"] == 1
    assert seen["my_quote"] is None
    assert seen["leading"] is False
    # Nothing in the payload names the other bidder or lists their offer.
    body = str(seen)
    assert "XYZ Polymers" not in body
    assert "participants" not in seen
    assert "quotes" not in seen


def test_selling_rewards_the_highest_and_buying_the_lowest(client, auth, masters, parties, bid):
    first = code_of(bid, parties["customer"])
    second = code_of(bid, parties["other_customer"])
    quote(client, first, bid["id"], "90")
    quote(client, second, bid["id"], "97")
    selling = client.get(f"/api/v1/portal/{first}/bids/{bid['id']}").json()
    assert selling["best_is_highest"] is True
    assert selling["best_price"] == "97.00", "we are selling: the high offer leads"
    assert selling["leading"] is False

    buying = client.post(
        "/api/v1/bids",
        json={
            "bid_type": "SUPPLIER",
            "product_id": masters["product_id"],
            "quantity": "30",
            "party_ids": [parties["supplier"]],
        },
        headers=auth,
    ).json()
    client.post(f"/api/v1/bids/{buying['id']}/publish", headers=auth)
    supplier_code = code_of(
        {"participants": participants_of(client, auth, buying["id"])}, parties["supplier"]
    )
    quote(client, supplier_code, buying["id"], "88")
    seen = client.get(f"/api/v1/portal/{supplier_code}/bids/{buying['id']}").json()
    assert seen["best_is_highest"] is False
    assert seen["leading"] is True


def test_a_code_cannot_reach_a_bid_it_was_not_invited_to(client, auth, masters, parties, bid):
    other = client.post(
        "/api/v1/bids",
        json={
            "bid_type": "CUSTOMER",
            "product_id": masters["product_id"],
            "quantity": "5",
            "party_ids": [parties["other_customer"]],
        },
        headers=auth,
    ).json()
    client.post(f"/api/v1/bids/{other['id']}/publish", headers=auth)

    outsider = code_of(bid, parties["customer"])
    assert client.get(f"/api/v1/portal/{outsider}/bids/{other['id']}").status_code == 404
    assert quote(client, outsider, other["id"], "99").status_code == 404
    # The portal lists only their own bids.
    listed = client.get(f"/api/v1/portal/{outsider}").json()
    assert [row["id"] for row in listed["open_bids"]] == [bid["id"]]


@pytest.mark.parametrize("code", ["notarealcodeatall", "0000000000000000", "../../etc"])
def test_an_unknown_code_tells_a_stranger_nothing(client, code):
    response = client.get(f"/api/v1/portal/{code}")
    assert response.status_code in (404, 422)
    assert "name" not in response.text.lower() or response.status_code == 422


def test_the_portal_needs_no_sign_in_but_the_desk_endpoints_do(client, bid, parties):
    code = code_of(bid, parties["customer"])
    assert client.get(f"/api/v1/portal/{code}").status_code == 200
    assert client.get("/api/v1/bids").status_code == 401
    assert client.get(f"/api/v1/bids/{bid['id']}").status_code == 401


def test_a_salesperson_cannot_reach_the_desk_side_of_bids(client, sales_auth, bid):
    assert client.get("/api/v1/bids", headers=sales_auth).status_code == 403
    assert client.get(f"/api/v1/bids/{bid['id']}", headers=sales_auth).status_code == 403


# --- quoting --------------------------------------------------------------- #
def test_a_quote_can_be_replaced_while_the_bid_is_open(client, auth, bid, parties):
    code = code_of(bid, parties["customer"])
    first = quote(client, code, bid["id"], "92", notes="Ex-works").json()
    assert first["my_quote"]["revision"] == 1

    second = quote(client, code, bid["id"], "94.25").json()
    assert second["my_quote"]["price"] == "94.25"
    assert second["my_quote"]["revision"] == 2

    # The desk sees one standing offer, not two.
    desk = quotes_of(client, auth, bid["id"])
    assert len(desk) == 1
    assert desk[0]["price"] == "94.25"
    # ...and the history keeps both.
    events = client.get(f"/api/v1/bids/{bid['id']}/history", headers=auth).json()["items"]
    quoted = [event for event in events if event["action"] == "QUOTE"]
    assert len(quoted) == 2


def test_nobody_can_bid_for_more_than_the_lot(client, bid, parties):
    code = code_of(bid, parties["customer"])
    response = quote(client, code, bid["id"], "92", quantity="100")
    assert response.status_code == 422
    assert "cannot bid for more" in response.json()["error"]["message"]


def test_the_terms_of_an_open_bid_cannot_be_changed_under_the_bidders(client, auth, bid):
    response = client.patch(f"/api/v1/bids/{bid['id']}", json={"quantity": "5"}, headers=auth)
    assert response.status_code == 409
    allowed = client.patch(f"/api/v1/bids/{bid['id']}", json={"title": "Renamed"}, headers=auth)
    assert allowed.status_code == 200


def test_a_participant_who_has_quoted_cannot_be_dropped(client, auth, bid, parties):
    code = code_of(bid, parties["customer"])
    quote(client, code, bid["id"], "91")
    participant_id = next(
        p["id"] for p in bid["participants"] if p["party"]["id"] == parties["customer"]
    )
    response = client.delete(
        f"/api/v1/bids/{bid['id']}/participants/{participant_id}", headers=auth
    )
    assert response.status_code == 409


# --- closing and awarding --------------------------------------------------- #
def test_closing_freezes_the_quotations(client, auth, bid, parties):
    code = code_of(bid, parties["customer"])
    quote(client, code, bid["id"], "93")

    closed = client.post(f"/api/v1/bids/{bid['id']}/close", headers=auth).json()
    assert closed["status"] == "CLOSED"
    assert len(quotes_of(client, auth, bid["id"])) == 1, "quotations are kept"

    refused = quote(client, code, bid["id"], "99")
    assert refused.status_code == 409
    seen = client.get(f"/api/v1/portal/{code}/bids/{bid['id']}").json()
    assert seen["can_quote"] is False
    assert seen["my_quote"]["price"] == "93.00"


def test_closing_without_a_winner_is_recorded_as_such(client, auth, bid, parties):
    quote(client, code_of(bid, parties["customer"]), bid["id"], "93")
    closed = client.post(
        f"/api/v1/bids/{bid['id']}/close", params={"without_winner": True}, headers=auth
    ).json()
    assert closed["status"] == "CLOSED"
    assert closed["no_winner"] is True
    assert closed["winner"] is None
    assert len(quotes_of(client, auth, bid["id"])) == 1


def test_the_desk_picks_the_winner_by_judgement_not_by_price(client, auth, bid, parties):
    first = code_of(bid, parties["customer"])
    second = code_of(bid, parties["other_customer"])
    quote(client, first, bid["id"], "90")
    quote(client, second, bid["id"], "97")
    client.post(f"/api/v1/bids/{bid['id']}/close", headers=auth)

    rows = quotes_of(client, auth, bid["id"])
    assert [q["price"] for q in rows] == ["97.00", "90.00"], "best first"

    # Award the lower offer: the desk's call, not the arithmetic.
    lower = next(q for q in rows if q["price"] == "90.00")
    awarded = client.post(
        f"/api/v1/bids/{bid['id']}/award", json={"quote_id": lower["id"]}, headers=auth
    ).json()
    assert awarded["winner"]["party"]["id"] == parties["customer"]
    assert awarded["winner"]["is_winner"] is True
    assert awarded["status"] == "CLOSED", "awarding does not change the status"
    assert awarded["no_winner"] is False


def test_a_winner_cannot_be_chosen_before_closing(client, auth, bid, parties):
    code = code_of(bid, parties["customer"])
    quoted = quote(client, code, bid["id"], "93")
    assert quoted.status_code == 200
    response = client.post(
        f"/api/v1/bids/{bid['id']}/award",
        json={"quote_id": quotes_of(client, auth, bid["id"])[0]["id"]},
        headers=auth,
    )
    assert response.status_code == 409


def test_the_winner_is_not_announced_to_the_participants(client, auth, bid, parties):
    first = code_of(bid, parties["customer"])
    second = code_of(bid, parties["other_customer"])
    quote(client, first, bid["id"], "90")
    quote(client, second, bid["id"], "97")
    client.post(f"/api/v1/bids/{bid['id']}/close", headers=auth)
    client.post(
        f"/api/v1/bids/{bid['id']}/award",
        json={"quote_id": quotes_of(client, auth, bid["id"])[0]["id"]},
        headers=auth,
    )

    loser = client.get(f"/api/v1/portal/{first}/bids/{bid['id']}").json()
    assert "winner" not in loser
    assert str(loser).count("XYZ Polymers") == 0


# --- history ---------------------------------------------------------------- #
def test_the_bid_keeps_its_own_history(client, auth, bid, parties):
    quote(client, code_of(bid, parties["customer"]), bid["id"], "93")
    client.post(f"/api/v1/bids/{bid['id']}/close", headers=auth)
    actions = [
        event["action"]
        for event in client.get(f"/api/v1/bids/{bid['id']}/history", headers=auth).json()["items"]
    ]
    assert actions[-1] == "CREATE", "newest first, so the raising is last"
    assert "PUBLISH" in actions
    assert "QUOTE" in actions
    assert "CLOSE" in actions


def test_bids_do_not_touch_the_inquiry_book(client, auth, bid):
    """The two systems are separate; running a bid creates no inquiry."""
    assert client.get("/api/v1/inquiries", headers=auth).json()["total"] == 0


# --- finding a bid again ---------------------------------------------------- #
def test_bids_narrow_by_what_the_product_is_made_of(client, auth, masters, parties):
    """The inquiry book's product filters, over bids."""
    client.post(
        "/api/v1/bids",
        json={
            "bid_type": "CUSTOMER",
            "product_id": masters["product_id"],
            "quantity": "10",
            "party_ids": [parties["customer"]],
        },
        headers=auth,
    )

    def found(**params) -> int:
        return client.get("/api/v1/bids", params=params, headers=auth).json()["total"]

    assert found(material_id=masters["material_id"]) == 1
    assert found(grade_id=masters["grade_id"]) == 1
    assert found(manufacturer_id=masters["manufacturer_id"]) == 1
    assert found(application_id=masters["application_id"]) == 1
    assert found(product_id=masters["product_id"]) == 1
    # A different material is a different product.
    assert found(material_id=masters["other_material_id"]) == 0


def test_a_transport_bid_is_found_by_either_end_of_its_route(client, auth, parties, locations):
    client.post(
        "/api/v1/bids",
        json={
            "bid_type": "TRANSPORT",
            "quantity": "20",
            "pickup_location_id": locations["pickup_id"],
            "delivery_location_id": locations["delivery_id"],
            "party_ids": [parties["transporter"]],
        },
        headers=auth,
    )
    pickup = client.get(f"/api/v1/locations/{locations['pickup_id']}", headers=auth).json()
    client.patch(
        f"/api/v1/locations/{locations['pickup_id']}",
        json={"area": "Odhav", "city": pickup["city"]},
        headers=auth,
    )

    listed = client.get("/api/v1/bids", params={"area": "Odhav"}, headers=auth).json()
    assert listed["total"] == 1
    assert client.get("/api/v1/bids", params={"area": "Nowhere"}, headers=auth).json()["total"] == 0
    # Asking what the material is excludes transport, which carries none.
    assert client.get("/api/v1/bids", params={"material_id": 1}, headers=auth).json()["total"] == 0


# --- a room of a hundred ----------------------------------------------------- #
@pytest.fixture
def crowded(client, auth, masters):
    """One bid, sixty customers invited, forty of them quoting."""
    ids = []
    for index in range(60):
        party = client.post(
            "/api/v1/parties",
            json={"name": f"Bidder {index:03d}", "party_type": "CUSTOMER"},
            headers=auth,
        ).json()
        ids.append(party["id"])

    created = client.post(
        "/api/v1/bids",
        json={
            "bid_type": "CUSTOMER",
            "product_id": masters["product_id"],
            "quantity": "500",
            "party_ids": ids,
        },
        headers=auth,
    ).json()
    client.post(f"/api/v1/bids/{created['id']}/publish", headers=auth)

    rows = participants_of(client, auth, created["id"], page_size=100)
    for index, participant in enumerate(rows[:40]):
        code = participant["bid_link"].split("/portal/")[1].split("/")[0]
        quote(client, code, created["id"], str(90 + index))
    return created["id"]


def test_a_crowded_bid_is_served_a_page_at_a_time(client, auth, crowded):
    """Sixty participants must not arrive in one payload."""
    detail = client.get(f"/api/v1/bids/{crowded}", headers=auth).json()
    assert detail["participant_count"] == 60
    assert detail["quote_count"] == 40
    assert "participants" not in detail, "the room is fetched separately"
    assert "quotes" not in detail

    first = client.get(
        f"/api/v1/bids/{crowded}/quotes", params={"page_size": 10}, headers=auth
    ).json()
    assert first["total"] == 40
    assert len(first["items"]) == 10
    second = client.get(
        f"/api/v1/bids/{crowded}/quotes", params={"page_size": 10, "page": 2}, headers=auth
    ).json()
    assert {row["id"] for row in first["items"]}.isdisjoint({row["id"] for row in second["items"]})


def test_the_best_offer_is_on_the_first_page(client, auth, crowded):
    """Best first, across the whole bid - not merely the page."""
    page = client.get(
        f"/api/v1/bids/{crowded}/quotes", params={"page_size": 5}, headers=auth
    ).json()
    prices = [float(row["price"]) for row in page["items"]]
    assert prices == sorted(prices, reverse=True), "selling: highest leads"
    detail = client.get(f"/api/v1/bids/{crowded}", headers=auth).json()
    assert float(detail["best_price"]) == prices[0]


def test_the_desk_can_sort_the_offers_the_other_way(client, auth, crowded):
    cheapest = client.get(
        f"/api/v1/bids/{crowded}/quotes",
        params={"sort_by": "price", "sort_dir": "asc", "page_size": 3},
        headers=auth,
    ).json()["items"]
    prices = [float(row["price"]) for row in cheapest]
    assert prices == sorted(prices)


def test_a_participant_can_be_found_by_name(client, auth, crowded):
    found = client.get(
        f"/api/v1/bids/{crowded}/participants", params={"q": "Bidder 042"}, headers=auth
    ).json()
    assert found["total"] == 1
    assert found["items"][0]["party"]["name"] == "Bidder 042"

    quotes = client.get(
        f"/api/v1/bids/{crowded}/quotes", params={"q": "Bidder 00"}, headers=auth
    ).json()
    assert 0 < quotes["total"] < 40, "narrowed to the matching names"


def test_the_desk_can_see_who_has_not_answered(client, auth, crowded):
    silent = client.get(
        f"/api/v1/bids/{crowded}/participants",
        params={"quoted": False, "page_size": 100},
        headers=auth,
    ).json()
    assert silent["total"] == 20
    assert all(row["quote"] is None for row in silent["items"])

    answered = client.get(
        f"/api/v1/bids/{crowded}/participants", params={"quoted": True}, headers=auth
    ).json()
    assert answered["total"] == 40


def test_listing_bids_does_not_drag_in_the_rooms(client, auth, crowded):
    """The counts on a list row are counted in the database, not in Python."""
    row = next(
        item
        for item in client.get("/api/v1/bids", headers=auth).json()["items"]
        if item["id"] == crowded
    )
    assert row["participant_count"] == 60
    assert row["quote_count"] == 40
    assert row["best_price"] is not None


def test_a_busy_auction_does_not_return_its_whole_history(client, auth, crowded):
    """Forty quotations write forty lines; the rail asks for the latest few."""
    page = client.get(
        f"/api/v1/bids/{crowded}/history", params={"page_size": 10}, headers=auth
    ).json()
    assert page["total"] > 40
    assert len(page["items"]) == 10
    stamps = [event["at"] for event in page["items"]]
    assert stamps == sorted(stamps, reverse=True), "newest first"
