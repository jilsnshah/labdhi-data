"""Import parties from a Tally "Updation of Party GSTIN/UIN" export.

The export is one row per ledger, with extra unnumbered rows carrying a second
address for the ledger above (GODOWN, DELIVERY, FACTORY...). Several firms can
be exported separately; pass every file and the same company is merged once, on
its GSTIN first and its name second.

A ledger list is not a party list: it also holds bank accounts, tax ledgers and
fixed assets. Those are left out, and the ones that look like a party but carry
no address, GSTIN or PAN come in as prospects, so the office can see what is
verified and what is not.

Usage::

    python -m app.import_tally --dry-run  "labdhi exim ledger address.xlsx" ...
    python -m app.import_tally            "labdhi exim ledger address.xlsx" ...

Re-running is safe: a party is matched on its GSTIN, or on its type and name,
and an existing row is only filled in where the CRM has nothing yet.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Location, Party, PartyLocation, User
from app.models.enums import (
    AuditAction,
    LocationType,
    PartySource,
    PartyStage,
    PartyType,
    UserRole,
)
from app.models.party import normalize_phone  # noqa: F401  (kept: documents the event hook)
from app.services import audit

# --------------------------------------------------------------------------- #
# Reading the sheet
# --------------------------------------------------------------------------- #
#: Tally writes a stray control character in front of its placeholder values.
_JUNK = re.compile(r"[\x00-\x08\x0b-\x1f]|_x00[0-9a-fA-F]{2}_")
#: Values that mean "nothing recorded".
_EMPTY = {"", "not applicable", "unknown", "n/a", "na", "-"}

HEADER_FIRST_CELL = "sl no"


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = _JUNK.sub("", str(value))
    text = re.sub(r"\s+", " ", text).strip(" \t ")
    if text.lower() in _EMPTY:
        return None
    return text or None


@dataclass
class Address:
    label: str | None
    raw: str
    state: str | None
    country: str | None


@dataclass
class Ledger:
    name: str
    gst: str | None = None
    pan: str | None = None
    addresses: list[Address] = field(default_factory=list)
    sources: set[str] = field(default_factory=set)

    @property
    def primary(self) -> Address | None:
        return self.addresses[0] if self.addresses else None


def read_ledgers(path: Path) -> list[Ledger]:
    """Every numbered row in the sheet, with its unnumbered address rows."""
    import openpyxl

    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    workbook.close()

    start = next(
        (
            index + 1
            for index, row in enumerate(rows)
            if row and str(row[0] or "").strip().lower().startswith(HEADER_FIRST_CELL)
        ),
        None,
    )
    if start is None:
        raise SystemExit(f"{path.name}: no 'Sl No.' header row - is this a Tally party export?")

    ledgers: list[Ledger] = []
    current: Ledger | None = None
    for row in rows[start:]:
        cells = [_clean(cell) for cell in (list(row) + [None] * 8)[:8]]
        serial, name, address, state, country, _registration, gst, pan = cells
        if not name:
            continue
        if serial:
            current = Ledger(name=name, gst=gst, pan=pan, sources={path.stem})
            ledgers.append(current)
            if address:
                current.addresses.append(Address(None, address, state, country))
        elif current is not None and address:
            # An extra address for the ledger above: GODOWN, DELIVERY, FACTORY.
            current.addresses.append(Address(name, address, state, country))
    return ledgers


# --------------------------------------------------------------------------- #
# Deciding what each ledger is
# --------------------------------------------------------------------------- #
#: Bank, tax, capital and fixed-asset ledgers: real rows in the books, not parties.
NON_TRADE = re.compile(
    r"(\bA/C\.?\b|\bBANK\b|\bTDS\b|\bTCS\b|\bGST\b|\bITC\b|ADVANCE TAX|INCOME TAX"
    r"|DUTY (RECEIVABLE|PAYABLE)|\bRECEIVABLE\b|\bPAYABLE\b|CAPITAL\b|\bLOAN\b|DEPOSIT"
    r"|INSURANCE|INTEREST|ROUND ?OFF|\bCASH\b|SALARY|\bRENT\b|ELECTRIC|STATIONERY"
    r"|\bAUDIT\b|SERVICE TAX|LC MARGIN|PRINTER|COMPUTER|CCTV|AIR ?CONDITIONER"
    r"|FURNITURE|MOBILE PHONE|\bSCOOTER\b|\bCAR\b|SUSPENSE|PROFIT ?& ?LOSS)",
    re.IGNORECASE,
)

#: Names that say the party moves goods rather than buys or sells them.
TRANSPORTER = re.compile(
    r"\b(LOGISTICS?|LOGISTIC|ROADWAYS?|ROAD ?LINES?|ROAD ?CARRIERS?|TRANSPORTS?"
    r"|TRANSPORT ?CO|TRANSPORTATION|CARGO|FREIGHT|CARRIERS?|CARRYING|COURIER"
    r"|SHIPPING|CONTAINER|PARCEL ?SERVICE|TRANS ?CARRIER)\b",
    re.IGNORECASE,
)

GSTIN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z][Z][0-9A-Z]$")
PAN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def normalized_name(name: str) -> str:
    """Key for "the same company, typed differently"."""
    text = name.upper()
    text = re.sub(r"\s*-\s*(OLD|NEW|\d+)$", "", text)  # "HARIOM PLASTICS - NEW"
    text = re.sub(
        r"\b(PVT|PRIVATE|LTD|LIMITED|LLP|CO|COMPANY|INC|THE)\b", "", text
    )  # legal forms vary
    return re.sub(r"[^A-Z0-9]", "", text)


# --------------------------------------------------------------------------- #
# Addresses
# --------------------------------------------------------------------------- #
#: Tally writes the district the way the clerk typed it; these are the same place.
CITY_ALIASES = {
    "MORABI": "Morbi",
    "MORBI": "Morbi",
    "KACHCHH": "Kutch",
    "KUTCHH": "Kutch",
    "KUCHH": "Kutch",
    "AHEMDABAD": "Ahmedabad",
    "AHMEDABAD": "Ahmedabad",
    "AHMADABAD": "Ahmedabad",
    "AMDAVAD": "Ahmedabad",
    "BOMBAY": "Mumbai",
    "NAVO MUMBAI": "Navi Mumbai",
    "NEW MUMBAI": "Navi Mumbai",
    "BARODA": "Vadodara",
    "GANDHINAGR": "Gandhinagar",
    "HIMATNAGAR": "Himmatnagar",
    "SIDDHAPUR": "Siddhpur",
    "THANE-W": "Thane",
    "THANE W": "Thane",
    "KHOPAT THANE": "Thane",
    "AHEDABAD": "Ahmedabad",
    "AHHMEDABAD": "Ahmedabad",
    "EDABAD": "Ahmedabad",
    "GANDHI NAGAR": "Gandhinagar",
    "GHANDHINAGAR": "Gandhinagar",
    "GANDHINAGER": "Gandhinagar",
    "BANASKANATHA": "Banaskantha",
    "BANGLORE": "Bengaluru",
    "BANGALORE": "Bengaluru",
    "BARODARA": "Vadodara",
    "SURENDRA NAGAR": "Surendranagar",
    "SURENDRANAGR": "Surendranagar",
}

#: Localities that are not towns of their own: the address says the suburb, the
#: city is implied. Mapping them keeps the city filter honest and still records
#: the locality as the area.
LOCALITY_CITY = {
    "ASLALI": "Ahmedabad",
    "NARODA": "Ahmedabad",
    "ODHAV": "Ahmedabad",
    "VATVA": "Ahmedabad",
    "NAROL": "Ahmedabad",
    "PIPLAJ": "Ahmedabad",
    "RAMOL": "Ahmedabad",
    "VINZOL": "Ahmedabad",
    "VASTRAL": "Ahmedabad",
    "NIKOL": "Ahmedabad",
    "KATHWADA": "Ahmedabad",
    "ASARAWA": "Ahmedabad",
    "ASARWA": "Ahmedabad",
    "AMBAWDI": "Ahmedabad",
    "AMBAWADI": "Ahmedabad",
    "ASHRAM ROAD": "Ahmedabad",
    "MANINAGAR": "Ahmedabad",
    "SARKHEJ": "Ahmedabad",
    "MAKARBA": "Ahmedabad",
    "BOPAL": "Ahmedabad",
    "THALTEJ": "Ahmedabad",
    "SATELLITE": "Ahmedabad",
    "PRAHLADNAGAR": "Ahmedabad",
    "JETALPUR": "Ahmedabad",
    "CHANGODAR": "Ahmedabad",
    "DASKROI": "Ahmedabad",
    "MORAIYA": "Ahmedabad",
    "BAVLA": "Ahmedabad",
    "SANAND": "Ahmedabad",
    "DEHGAM": "Gandhinagar",
    "KALOL": "Gandhinagar",
    "SANTEJ": "Gandhinagar",
    "RAKANPUR": "Gandhinagar",
    "CHHATRAL": "Gandhinagar",
    "SHAPAR": "Rajkot",
    "VERAVAL (SHAPAR)": "Rajkot",
    "METODA": "Rajkot",
    "ANJAR": "Kutch",
    "MUNDRA": "Kutch",
    "GANDHIDHAM": "Kutch",
    "NAKHTRANA": "Kutch",
    "BHACHAU": "Kutch",
}
#: "Mundra-Kutch", "Ahmedabad-4", "Bakrol (Bujarang) Ahmedabad" - the town is
#: the last part that is actually a word.
CITY_SPLIT = re.compile(r"\s*[-/()]\s*")
#: Leading district / taluka markers Tally users type into the last line.
CITY_PREFIX = re.compile(
    r"^(DIST(RICT)?|DISTT|DIS|DI|TAL(UKA)?|TA|VILLAGE|VIL|AT|NR|NEAR|POST|PO)\b[\.\-: ]*",
    re.IGNORECASE,
)
#: "Halvad District. Morbi" - what follows the marker is the district town.
CITY_AFTER_DISTRICT = re.compile(r"\b(?:DIST(?:RICT)?|DISTT)\b[\.\-: ]*(.+)$", re.IGNORECASE)
#: An area is a locality a trader would filter by - "Odhav", "GIDC Vatva" -
#: never a plot or an estate number, so anything with a digit is not one.
AREA_WORDS = re.compile(
    r"\b(GIDC|G\.?I\.?D\.?C|INDUSTRIAL (ESTATE|AREA|PARK|ZONE)|ESTATE|VISTAR|CHOKDI|SEZ)\b",
    re.IGNORECASE,
)
AREA_REJECT = re.compile(
    r"[0-9/\\]|\b(NR|NEAR|OPP|B/H|BEHIND|ROAD|HIGHWAY|CROSS|CHAR RASTA)\b",
    re.IGNORECASE,
)
PINCODE = re.compile(r"\b(\d{6})\b")


#: Towns we trust when a line runs them together with their locality, as in
#: "Kathwada Ahmedabad" or "Mundra Kutch".
KNOWN_CITIES = (
    set(CITY_ALIASES.values())
    | set(LOCALITY_CITY.values())
    | {
        "Ahmedabad",
        "Gandhinagar",
        "Rajkot",
        "Morbi",
        "Kutch",
        "Gandhidham",
        "Surat",
        "Vadodara",
        "Mehsana",
        "Bhavnagar",
        "Jamnagar",
        "Changodar",
        "Himmatnagar",
        "Palanpur",
        "Mumbai",
        "Thane",
        "Delhi",
    }
)
KNOWN_CITIES_UPPER = {city.upper() for city in KNOWN_CITIES}


def _normalize_area(text: str) -> str | None:
    """ "GIDC Vatva", "Vatva GIDC", "GIDC-Vatva" are one place; bare "GIDC" is none."""
    cleaned = re.sub(r"\bG\.?I\.?D\.?C\.?\b", " ", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"[\s\-]+", " ", cleaned).strip(" .,:;-")
    if cleaned.upper() in LOCALITY_CITY:
        return cleaned.title()
    if not cleaned:
        return None  # "GIDC" on its own says nothing
    return text.strip(" .,:;-").title()


def _city_token(token: str) -> str | None:
    """The place name inside one comma-separated piece of a Tally address."""
    text = PINCODE.sub("", token).strip(" .,:;-")
    after_district = CITY_AFTER_DISTRICT.search(text)
    if after_district:
        text = after_district.group(1).strip(" .,:;-")
    text = CITY_PREFIX.sub("", text).strip(" .,:;-")
    if not text:
        return None
    # "Ahmedabad-4" -> Ahmedabad; "Mundra-Kutch" -> Kutch.
    words = [part for part in CITY_SPLIT.split(text) if re.search(r"[A-Za-z]{3}", part)]
    if not words:
        return None
    text = words[-1].strip(" .,:;-\\")
    # A long tail is a street, not a town: "Naroda Dehgam Road Naroda Ahmedabad".
    if len(text.split()) > 3:
        text = text.split()[-1]
    if len(text) < 3 or len(text) > 120:
        return None
    return text


def _city_from(token: str) -> str | None:
    """The town a piece of address points at, suburbs resolved to their city."""
    text = _city_token(token)
    if text is None:
        return None
    key = text.upper()
    mapped = CITY_ALIASES.get(key) or LOCALITY_CITY.get(key)
    if mapped:
        return mapped
    # "Kathwada Ahmedabad": the locality was typed without a comma.
    words = text.replace(".", " ").split()
    if len(words) > 1 and words[-1].upper() in KNOWN_CITIES_UPPER:
        last = words[-1].upper()
        return CITY_ALIASES.get(last) or LOCALITY_CITY.get(last) or words[-1].title()
    return text.title()


def split_address(raw: str) -> tuple[str, str | None, str | None, str | None]:
    """``raw`` -> (street, area, city, pincode).

    Tally stores the address as one line with the town last, so the tail of the
    string is the city and what precedes it is usually the locality.
    """
    pincode_match = PINCODE.search(raw)
    pincode = pincode_match.group(1) if pincode_match else None

    parts = [part.strip(" .,:;-") for part in raw.split(",")]
    parts = [part for part in parts if part]
    if not parts:
        return raw[:200], None, None, pincode

    # Walk back from the end: the last piece that reads like a town wins.
    city = None
    city_index = len(parts)
    for index in range(len(parts) - 1, max(len(parts) - 3, -1), -1):
        city = _city_from(parts[index])
        if city:
            city_index = index
            break

    body = parts[:city_index]
    area = None
    # A suburb used as the city is the area; the real city came from the map.
    if city_index < len(parts):
        tail = (_city_token(parts[city_index]) or "").upper()
        if tail in LOCALITY_CITY:
            area = tail.title()
    if area is None:
        for part in reversed(body):
            candidate = CITY_PREFIX.sub("", part).strip(" .,:;-")
            if candidate.upper() in LOCALITY_CITY:
                area = candidate.title()
                break
            if (
                AREA_WORDS.search(candidate)
                and not AREA_REJECT.search(candidate)
                and len(candidate.split()) <= 3
            ):
                area = _normalize_area(candidate)
                if area:
                    break

    street = ", ".join(body) or raw
    return street[:200], area, city, pincode


LOCATION_TYPES = [
    (re.compile(r"GODOWN|WAREHOUSE|STOCK", re.IGNORECASE), LocationType.WAREHOUSE),
    (re.compile(r"FACTORY|PLANT|WORKS|UNIT", re.IGNORECASE), LocationType.FACTORY),
    (re.compile(r"DELIV|DISPATCH|SHIP", re.IGNORECASE), LocationType.DELIVERY_LOCATION),
    (re.compile(r"OFFICE|HEAD|REGD|CORPORATE", re.IGNORECASE), LocationType.HEAD_OFFICE),
]


def location_type_of(label: str | None, is_first: bool) -> LocationType:
    if label:
        for pattern, kind in LOCATION_TYPES:
            if pattern.search(label):
                return kind
        return LocationType.OTHER
    return LocationType.HEAD_OFFICE if is_first else LocationType.OTHER


# --------------------------------------------------------------------------- #
# Merging the files into one party list
# --------------------------------------------------------------------------- #
@dataclass
class Candidate:
    ledger: Ledger
    party_type: PartyType
    stage: PartyStage


def merge(ledgers: list[Ledger]) -> list[Ledger]:
    """One entry per company: the same GSTIN, or the same name, is one party."""
    by_gst: dict[str, Ledger] = {}
    by_name: dict[str, Ledger] = {}
    merged: list[Ledger] = []

    def absorb(into: Ledger, other: Ledger) -> None:
        into.gst = into.gst or other.gst
        into.pan = into.pan or other.pan
        into.sources |= other.sources
        known = {(address.label, address.raw) for address in into.addresses}
        for address in other.addresses:
            if (address.label, address.raw) not in known:
                into.addresses.append(address)

    for ledger in ledgers:
        gst = ledger.gst if ledger.gst and GSTIN.match(ledger.gst) else None
        key = normalized_name(ledger.name)
        existing = by_gst.get(gst) if gst else None
        if existing is None:
            existing = by_name.get(key)
            # Two different companies can share a name only if both have a GSTIN
            # of their own; then they stay apart and are disambiguated later.
            if existing is not None and gst and existing.gst and existing.gst != gst:
                existing = None
        if existing is not None:
            absorb(existing, ledger)
            if gst:
                by_gst.setdefault(gst, existing)
            by_name.setdefault(key, existing)
            continue
        merged.append(ledger)
        if gst:
            by_gst[gst] = ledger
        by_name.setdefault(key, ledger)
    return merged


def classify(ledgers: list[Ledger]) -> tuple[list[Candidate], list[Ledger]]:
    """Split the merged list into parties to import and ledgers to leave out."""
    candidates: list[Candidate] = []
    skipped: list[Ledger] = []
    for ledger in ledgers:
        has_identity = bool(ledger.gst or ledger.pan)
        if NON_TRADE.search(ledger.name) and not has_identity:
            skipped.append(ledger)
            continue
        party_type = (
            PartyType.TRANSPORTER if TRANSPORTER.search(ledger.name) else PartyType.CUSTOMER
        )
        thin = not ledger.addresses and not has_identity
        candidates.append(
            Candidate(ledger, party_type, PartyStage.PROSPECT if thin else PartyStage.ACTIVE)
        )
    return candidates, skipped


# --------------------------------------------------------------------------- #
# Writing to the database
# --------------------------------------------------------------------------- #
def _existing_party(session: Session, candidate: Candidate) -> Party | None:
    ledger = candidate.ledger
    if ledger.gst:
        found = session.scalar(select(Party).where(Party.gst_number == ledger.gst))
        if found is not None:
            return found
    return session.scalar(
        select(Party).where(
            Party.party_type == candidate.party_type,
            Party.name == ledger.name,
            Party.merged_into_id.is_(None),
        )
    )


def _import_user(session: Session) -> int | None:
    user = session.scalar(select(User).where(User.role == UserRole.ADMIN).order_by(User.id))
    return user.id if user else None


def apply(session: Session, candidates: list[Candidate], *, user_id: int | None) -> Counter:
    stats: Counter = Counter()
    taken_names: set[tuple[str, str]] = set()

    for candidate in candidates:
        ledger = candidate.ledger
        party = _existing_party(session, candidate)

        if party is None:
            name = ledger.name
            key = (candidate.party_type.value, name.lower())
            if key in taken_names and candidate.stage == PartyStage.ACTIVE:
                # Same name, different GSTIN: keep both, tell them apart.
                name = f"{name} ({ledger.gst[:2]}{ledger.gst[-4:]})" if ledger.gst else name
            taken_names.add((candidate.party_type.value, name.lower()))
            party = Party(
                name=name[:200],
                party_type=candidate.party_type,
                gst_number=ledger.gst,
                stage=candidate.stage,
                source=PartySource.IMPORT,
                notes=_notes(ledger),
            )
            session.add(party)
            session.flush()
            audit.record(
                session,
                user_id=user_id,
                entity_type="party",
                entity_id=party.id,
                action=AuditAction.CREATE,
                new_value={
                    "name": party.name,
                    "party_type": party.party_type.value,
                    "source": PartySource.IMPORT.value,
                    "import": sorted(ledger.sources),
                },
            )
            stats["created"] += 1
        else:
            # Never overwrite what the office has already corrected.
            filled = []
            if not party.gst_number and ledger.gst:
                party.gst_number = ledger.gst
                filled.append("gst_number")
            if not party.notes:
                party.notes = _notes(ledger)
                filled.append("notes")
            stats["updated" if filled else "unchanged"] += 1

        stats["locations"] += _sync_locations(session, party, ledger)

    return stats


def _notes(ledger: Ledger) -> str:
    bits = [f"Imported from Tally ({', '.join(sorted(ledger.sources))})."]
    if ledger.pan and PAN.match(ledger.pan):
        bits.append(f"PAN {ledger.pan}.")
    return " ".join(bits)


def _sync_locations(session: Session, party: Party, ledger: Ledger) -> int:
    """Add the addresses this party does not have yet."""
    existing = {
        (link.location.address_line_1 or "").strip().lower(): link for link in party.locations
    }
    has_primary = any(link.is_primary for link in party.locations)
    added = 0

    for index, address in enumerate(ledger.addresses):
        street, area, city, pincode = split_address(address.raw)
        if not city:
            # The city is required; without it the row would be worse than none.
            city = address.state or "Unknown"
        if street.strip().lower() in existing:
            continue
        location = Location(
            label=(address.label or None),
            address_line_1=street,
            area=area,
            city=city[:120],
            state=address.state,
            country=address.country or "India",
            pincode=pincode,
        )
        session.add(location)
        session.flush()
        session.add(
            PartyLocation(
                party_id=party.id,
                location_id=location.id,
                location_type=location_type_of(address.label, index == 0),
                is_primary=(index == 0 and not has_primary),
            )
        )
        if index == 0 and not has_primary:
            has_primary = True
        existing[street.strip().lower()] = None  # type: ignore[assignment]
        added += 1
    return added


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def summarise(candidates: list[Candidate], skipped: list[Ledger]) -> str:
    types = Counter(candidate.party_type.value for candidate in candidates)
    stages = Counter(candidate.stage.value for candidate in candidates)
    cities: Counter = Counter()
    addresses = 0
    for candidate in candidates:
        for address in candidate.ledger.addresses:
            addresses += 1
            _, _, city, _ = split_address(address.raw)
            cities[city or "(none)"] += 1
    lines = [
        f"parties to import : {len(candidates)}",
        f"  by type         : {dict(types)}",
        f"  by stage        : {dict(stages)}",
        f"  with GSTIN      : {sum(1 for c in candidates if c.ledger.gst)}",
        f"addresses         : {addresses}",
        f"  top cities      : {', '.join(f'{c} {n}' for c, n in cities.most_common(8))}",
        f"ledgers left out  : {len(skipped)}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="Tally .xlsx exports")
    parser.add_argument("--dry-run", action="store_true", help="Report, write nothing")
    parser.add_argument("--list-skipped", action="store_true", help="Print the excluded ledgers")
    args = parser.parse_args(argv)

    ledgers: list[Ledger] = []
    for path in args.files:
        if not path.exists():
            raise SystemExit(f"{path}: not found")
        found = read_ledgers(path)
        print(f"{path.name}: {len(found)} ledgers")
        ledgers += found

    candidates, skipped = classify(merge(ledgers))
    print(f"\n{summarise(candidates, skipped)}\n")
    if args.list_skipped:
        for ledger in skipped:
            print(f"  skipped: {ledger.name}")
        print()

    if args.dry_run:
        print("dry run - nothing written")
        return 0

    with SessionLocal() as session:
        stats = apply(session, candidates, user_id=_import_user(session))
        session.commit()
    print(f"written: {dict(stats)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
