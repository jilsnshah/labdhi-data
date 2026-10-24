"""The Tally importer reads a ledger list, not a party list.

These tests pin the judgement calls: which rows are a party at all, when two
rows are the same company, and how a one-line Indian address becomes a city and
an area the desk can filter by.
"""

from __future__ import annotations

import pytest

from app.import_tally import (
    Address,
    Ledger,
    classify,
    disambiguate,
    merge,
    normalized_name,
    split_address,
)
from app.models.enums import PartyStage, PartyType


def ledger(name: str, gst: str | None = None, pan: str | None = None, address: str | None = None):
    return Ledger(
        name=name,
        gst=gst,
        pan=pan,
        addresses=[Address(None, address, "Gujarat", "India")] if address else [],
        sources={"book"},
    )


# --- what counts as a party ------------------------------------------------ #
@pytest.mark.parametrize(
    "name",
    [
        "BANK OF BARODA 16550200000267",
        "CCTV CAMERA A/C.",
        "ADVANCE TAX",
        "HIRAL P SHAH CAPITAL A/C.",
        "HDFC LIFE INSURANCE",
    ],
)
def test_bookkeeping_ledgers_are_not_parties(name):
    candidates, skipped = classify([ledger(name)])
    assert candidates == []
    assert [item.name for item in skipped] == [name]


def test_a_bookkeeping_name_with_a_gstin_is_still_imported():
    """'...TRANSPORT GST' style names exist; a GSTIN means a real counterparty."""
    candidates, skipped = classify([ledger("SHREE RENT A CAR", gst="24AAACZ5277H1Z4")])
    assert skipped == []
    assert len(candidates) == 1


@pytest.mark.parametrize(
    "name",
    ["AAKASH ROADWAYS", "AJANTA FREIGHT CARRIER", "CARGOCORP LOGISTICS", "AMEY TRANSPORT CO."],
)
def test_names_that_move_goods_are_transporters(name):
    candidates, _ = classify([ledger(name, address="GIDC, Odhav, Ahmedabad")])
    assert candidates[0].party_type == PartyType.TRANSPORTER


def test_everything_else_is_a_customer():
    candidates, _ = classify([ledger("AARVI POLYPLAST", address="Vatva, Ahmedabad")])
    assert candidates[0].party_type == PartyType.CUSTOMER


def test_a_row_with_nothing_to_verify_it_comes_in_as_a_prospect():
    thin, solid = classify([ledger("DARPAN PATEL"), ledger("A-ONE PIPE", pan="AHZPG5607M")])[0]
    assert thin.stage == PartyStage.PROSPECT
    assert solid.stage == PartyStage.ACTIVE


# --- the same company, typed differently ----------------------------------- #
def test_one_gstin_is_one_party_however_the_name_is_spelled():
    merged = merge(
        [
            ledger("HARIOM PLASTICS", gst="24AAPHS3296B1ZZ", address="Narol, Ahmedabad"),
            ledger("HARIOM PLASTICS - NEW", gst="24AAPHS3296B1ZZ", address="Odhav, Ahmedabad"),
        ]
    )
    assert len(merged) == 1
    assert len(merged[0].addresses) == 2, "both addresses are kept"


def test_the_same_name_in_two_books_is_one_party_and_remembers_both():
    first = ledger("AARVI POLYPLAST", address="Vatva, Ahmedabad")
    first.sources = {"ledger-a"}
    second = ledger("Aarvi Polyplast ", pan="BEZPG5365N")
    second.sources = {"ledger-b"}
    merged = merge([first, second])
    assert len(merged) == 1
    assert merged[0].sources == {"ledger-a", "ledger-b"}
    assert merged[0].pan == "BEZPG5365N", "detail from either book is kept"


def test_a_misspelt_name_only_merges_through_a_shared_gstin():
    """One letter apart is a different company until a GSTIN says otherwise."""
    spelled_differently = merge(
        [ledger("ARVI POLYPLAST"), ledger("AARVI POLYPLAST")],
    )
    assert len(spelled_differently) == 2
    same_gstin = merge(
        [
            ledger("ARVI POLYPLAST", gst="24BEZPG5365N1ZO"),
            ledger("AARVI POLYPLAST", gst="24BEZPG5365N1ZO"),
        ]
    )
    assert len(same_gstin) == 1


def test_two_companies_with_one_name_but_their_own_gstins_stay_apart():
    merged = merge(
        [
            ledger("SHREE TRADERS", gst="24AAACZ5277H1Z4"),
            ledger("SHREE TRADERS", gst="27AAACZ5277H1ZB"),
        ]
    )
    assert len(merged) == 2


def test_legal_form_and_old_new_markers_do_not_make_a_new_company():
    assert normalized_name("ANAND TRADELINK PRIVATE LIMITED") == normalized_name(
        "ANAND TRADELINK PVT LTD"
    )
    assert normalized_name("HARIOM PLASTICS - OLD") == normalized_name("Hariom Plastics")


# --- addresses ------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("raw", "city"),
    [
        ("509, PHASE-IV, GIDC, VATVA, AHMEDABAD-382445", "Ahmedabad"),
        ("45, NR. SHYAM DAIRY, KUKAVAV ROAD, AMRELI", "Amreli"),
        ("Baroi Road, Plot No.8, GIDC, Mundra-Kutch", "Kutch"),
        ("715, JUNA MADHUPURA, AHMEDABAD-4", "Ahmedabad"),  # not "4"
        ("PLOT 12, HALVAD DISTRICT. MORABI", "Morbi"),  # district marker, typo
        ("S.NO.95, KATHWADA AHMEDABAD", "Ahmedabad"),  # run together, no comma
        ("22, Shed No.4, Aslali", "Ahmedabad"),  # a suburb is not a city
    ],
)
def test_the_town_is_read_off_the_end_of_the_line(raw, city):
    assert split_address(raw)[2] == city


def test_the_locality_becomes_the_area_the_desk_filters_by():
    _, area, city, _ = split_address("Godown 2, Ocean Estate, Nr. Aashapuri, Aslali, Ahmedabad")
    assert (area, city) == ("Aslali", "Ahmedabad")


def test_a_plot_number_is_never_an_area():
    assert split_address("106 GIDC, Odhav, Ahmedabad")[1] == "Odhav"
    assert split_address("A/12 Swagat Industrial Park 1, Rajkot")[1] is None


def test_gidc_variants_are_one_area():
    first = split_address("Shed 4, GIDC-Vatva, Ahmedabad")[1]
    second = split_address("Shed 9, Vatva GIDC, Ahmedabad")[1]
    assert first == second == "Vatva"
    assert split_address("Shed 2, GIDC, Rajkot")[1] is None, "'GIDC' alone says nothing"


def test_the_pincode_is_lifted_out_of_the_line():
    street, _, city, pincode = split_address("509, PHASE-IV, GIDC, VATVA, AHMEDABAD-382445")
    assert pincode == "382445"
    assert city == "Ahmedabad"
    assert "382445" not in city
    assert street.startswith("509")


def test_an_address_the_parser_cannot_read_still_keeps_its_text():
    street, _, _, _ = split_address("SOME UNPARSEABLE LINE")
    assert street == "SOME UNPARSEABLE LINE"


# --- two firms, one trade name --------------------------------------------- #
def _candidates(*ledgers):
    candidates, _ = classify(merge(list(ledgers)))
    disambiguate(candidates)
    return candidates


def test_one_company_registered_in_two_states_is_told_apart_by_state():
    gujarat = ledger("R P SHAH AND SONS", gst="24AGNPS9348A1Z5", address="Odhav, Ahmedabad")
    maharashtra = ledger("R P SHAH AND SONS", gst="27AGNPS9348A1ZZ")
    maharashtra.addresses = [Address(None, "Nariman Point, Mumbai", "Maharashtra", "India")]
    names = [candidate.ledger.name for candidate in _candidates(gujarat, maharashtra)]
    assert names == ["R P SHAH AND SONS", "R P SHAH AND SONS (Maharashtra)"]


def test_two_firms_in_one_state_are_told_apart_by_gstin():
    names = [
        candidate.ledger.name
        for candidate in _candidates(
            ledger("HARIOM PLASTICS", gst="24AAPHS3296B1ZZ", address="Narol, Ahmedabad"),
            ledger("HARIOM PLASTICS", gst="24ADZPS9590H1ZH", address="Odhav, Ahmedabad"),
        )
    ]
    assert names == ["HARIOM PLASTICS", "HARIOM PLASTICS (GST H1ZH)"]
