"""Party services: parties, their locations and their product relationships."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, and_, func, or_, select, text, update
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.pagination import PageParams, apply_sort, paginate
from app.models.activity import Activity
from app.models.enums import (
    AuditAction,
    InquiryStatus,
    LocationType,
    PartyProductRelationship,
    PartySource,
    PartyStage,
    PartyType,
    RecordStatus,
)
from app.models.inquiry import (
    CustomerInquiry,
    Inquiry,
    SupplierInquiry,
    TransportInquiry,
)
from app.models.masters import Application, Product
from app.models.note import Note
from app.models.party import (
    Location,
    Party,
    PartyApplication,
    PartyLocation,
    PartyProduct,
    normalize_phone,
)
from app.schemas.party import (
    DuplicateCandidate,
    DuplicateCheckResult,
    LocationCreate,
    LocationUpdate,
    PartyApplicationCreate,
    PartyApplicationUpdate,
    PartyCreate,
    PartyLocationCreate,
    PartyLocationUpdate,
    PartyProductCreate,
    PartyProductUpdate,
    PartyProspectCreate,
    PartyQuickCreate,
    PartyUpdate,
)
from app.services import audit
from app.services.common import apply_patch, ensure_unique, get_or_404, require_active

#: Which product relationships make sense for which party type.
ALLOWED_RELATIONSHIPS: dict[PartyType, set[PartyProductRelationship]] = {
    PartyType.CUSTOMER: {
        PartyProductRelationship.PURCHASES,
        PartyProductRelationship.INTERESTED_IN,
    },
    PartyType.SUPPLIER: {PartyProductRelationship.SUPPLIES},
    PartyType.TRANSPORTER: set(),
}

DEFAULT_RELATIONSHIP: dict[PartyType, PartyProductRelationship | None] = {
    PartyType.CUSTOMER: PartyProductRelationship.PURCHASES,
    PartyType.SUPPLIER: PartyProductRelationship.SUPPLIES,
    PartyType.TRANSPORTER: None,
}


# --------------------------------------------------------------------------- #
# Locations (independent master)
# --------------------------------------------------------------------------- #
def list_locations(
    session: Session,
    params: PageParams,
    *,
    q: str | None = None,
    city: str | None = None,
    area: str | None = None,
    state: str | None = None,
    party_id: int | None = None,
    status: RecordStatus | None = None,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> tuple[Sequence[Location], int]:
    stmt = select(Location)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Location.label.ilike(like),
                Location.area.ilike(like),
                Location.city.ilike(like),
                Location.state.ilike(like),
                Location.address_line_1.ilike(like),
                Location.pincode.ilike(like),
            )
        )
    if city:
        stmt = stmt.where(Location.city.ilike(f"%{city}%"))
    if area:
        stmt = stmt.where(func.lower(Location.area) == area.strip().lower())
    if state:
        stmt = stmt.where(Location.state.ilike(f"%{state}%"))
    if party_id is not None:
        stmt = stmt.where(
            Location.id.in_(
                select(PartyLocation.location_id).where(PartyLocation.party_id == party_id)
            )
        )
    if status:
        stmt = stmt.where(Location.status == status)
    stmt = apply_sort(
        stmt,
        sort_by,
        sort_dir,
        {
            "city": Location.city,
            "area": Location.area,
            "label": Location.label,
            "created_at": Location.created_at,
            "id": Location.id,
        },
        "city",
    )
    return paginate(session, stmt, params)


def list_areas(session: Session) -> list[str]:
    """Every distinct area on an active location, alphabetically.

    Areas are free text on the location, so this is what the pickers offer: the
    spellings already in use, which keeps "Shapar" from turning into "shapar".
    """
    rows = session.execute(
        select(Location.area)
        .where(Location.area.is_not(None), Location.status == RecordStatus.ACTIVE)
        .distinct()
    ).scalars()
    return sorted(rows, key=str.lower)


def create_location(session: Session, payload: LocationCreate, user_id: int) -> Location:
    location = Location(**payload.model_dump())
    session.add(location)
    session.flush()
    audit.record(
        session,
        user_id=user_id,
        entity_type="location",
        entity_id=location.id,
        action=AuditAction.CREATE,
        new_value={"city": location.city, "area": location.area, "label": location.label},
    )
    return location


def update_location(
    session: Session, location_id: int, payload: LocationUpdate, user_id: int
) -> Location:
    location = get_or_404(session, Location, location_id, "Location")
    data = payload.model_dump(exclude_unset=True)
    changes = apply_patch(location, data, set(data.keys()))
    audit.record_changes(
        session,
        user_id=user_id,
        entity_type="location",
        entity_id=location.id,
        changes=changes,
    )
    return location


# --------------------------------------------------------------------------- #
# Parties
# --------------------------------------------------------------------------- #
def _open_inquiry_counts(session: Session, party_ids: Sequence[int]) -> dict[int, int]:
    if not party_ids:
        return {}
    open_filter = Inquiry.status == InquiryStatus.ACTIVE
    counts: dict[int, int] = {}
    for detail, column in (
        (CustomerInquiry, CustomerInquiry.customer_id),
        (SupplierInquiry, SupplierInquiry.supplier_id),
        (TransportInquiry, TransportInquiry.transporter_id),
    ):
        rows = session.execute(
            select(column, func.count())
            .join(Inquiry, Inquiry.id == detail.inquiry_id)
            .where(column.in_(party_ids), open_filter)
            .group_by(column)
        ).all()
        for party_id, count in rows:
            counts[party_id] = counts.get(party_id, 0) + count
    return counts


def _product_counts(session: Session, party_ids: Sequence[int]) -> dict[int, int]:
    if not party_ids:
        return {}
    rows = session.execute(
        select(PartyProduct.party_id, func.count())
        .where(PartyProduct.party_id.in_(party_ids), PartyProduct.active.is_(True))
        .group_by(PartyProduct.party_id)
    ).all()
    return dict(rows)


def _primary_cities(session: Session, party_ids: Sequence[int]) -> dict[int, str]:
    if not party_ids:
        return {}
    rows = session.execute(
        select(PartyLocation.party_id, Location.city, PartyLocation.is_primary)
        .join(Location, Location.id == PartyLocation.location_id)
        .where(PartyLocation.party_id.in_(party_ids))
        .order_by(PartyLocation.party_id, PartyLocation.is_primary.desc(), PartyLocation.id)
    ).all()
    cities: dict[int, str] = {}
    for party_id, city, _is_primary in rows:
        cities.setdefault(party_id, city)
    return cities


def list_parties(
    session: Session,
    params: PageParams,
    *,
    q: str | None = None,
    party_type: PartyType | None = None,
    status: RecordStatus | None = None,
    stage: PartyStage | None = None,
    include_merged: bool = False,
    stale_days: int | None = None,
    city: str | None = None,
    location_id: int | None = None,
    product_id: int | None = None,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> tuple[Sequence[Party], int, dict[str, dict[int, object]]]:
    stmt: Select = select(Party)
    if stage is not None:
        stmt = stmt.where(Party.stage == stage)
    elif not include_merged:
        # Merged rows stay reachable by id, but never pollute a list.
        stmt = stmt.where(Party.stage != PartyStage.MERGED)
    if stale_days is not None:
        # Prospects nobody has touched: no inquiry, no activity, old enough.
        cutoff = stale_prospect_cutoff(stale_days)
        stmt = stmt.where(
            Party.stage == PartyStage.PROSPECT,
            Party.created_at < cutoff,
            ~Party.id.in_(select(CustomerInquiry.customer_id)),
            ~Party.id.in_(select(SupplierInquiry.supplier_id)),
            ~Party.id.in_(select(TransportInquiry.transporter_id)),
            ~Party.id.in_(select(Activity.party_id)),
        )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Party.name.ilike(like),
                Party.phone.ilike(like),
                Party.email.ilike(like),
                Party.gst_number.ilike(like),
                Party.contact_person.ilike(like),
            )
        )
    if party_type:
        stmt = stmt.where(Party.party_type == party_type)
    if status:
        stmt = stmt.where(Party.status == status)
    if city:
        stmt = stmt.where(
            Party.id.in_(
                select(PartyLocation.party_id)
                .join(Location, Location.id == PartyLocation.location_id)
                .where(Location.city.ilike(f"%{city}%"))
            )
        )
    if location_id is not None:
        stmt = stmt.where(
            Party.id.in_(
                select(PartyLocation.party_id).where(PartyLocation.location_id == location_id)
            )
        )
    if product_id is not None:
        stmt = stmt.where(
            Party.id.in_(
                select(PartyProduct.party_id).where(
                    and_(PartyProduct.product_id == product_id, PartyProduct.active.is_(True))
                )
            )
        )
    stmt = apply_sort(
        stmt,
        sort_by,
        sort_dir,
        {
            "name": Party.name,
            "created_at": Party.created_at,
            "updated_at": Party.updated_at,
            "id": Party.id,
        },
        "name",
    )
    rows, total = paginate(session, stmt, params)
    ids = [party.id for party in rows]
    extras = {
        "open_inquiry_count": _open_inquiry_counts(session, ids),
        "product_count": _product_counts(session, ids),
        "primary_city": _primary_cities(session, ids),
    }
    return rows, total, extras


def get_party(session: Session, party_id: int, *, expected_type: PartyType | None = None) -> Party:
    party = session.get(
        Party,
        party_id,
        options=[
            selectinload(Party.locations).selectinload(PartyLocation.location),
            selectinload(Party.products).selectinload(PartyProduct.product),
        ],
    )
    if party is None:
        raise NotFoundError(f"Party #{party_id} was not found.")
    if expected_type and party.party_type != expected_type:
        raise ValidationError(
            f"Party #{party_id} is a {party.party_type.value}, not a {expected_type.value}."
        )
    return party


def _ensure_name_free(
    session: Session, name: str, party_type: PartyType, *, exclude_id: int | None = None
) -> None:
    """Only verified (ACTIVE) parties own the unique-name namespace.

    Prospects are exempt because two different walk-ins may share a name, and
    merged rows are exempt so a duplicate cannot block its own survivor.
    """
    stmt = select(Party.id).where(
        Party.party_type == party_type,
        func.lower(Party.name) == name.lower(),
        Party.stage == PartyStage.ACTIVE,
    )
    if exclude_id is not None:
        stmt = stmt.where(Party.id != exclude_id)
    if session.scalar(stmt.limit(1)) is not None:
        raise ConflictError(f"A {party_type.value.lower()} named '{name}' already exists.")


def create_party(session: Session, payload: PartyCreate, user_id: int) -> Party:
    if payload.stage != PartyStage.PROSPECT:
        _ensure_name_free(session, payload.name, payload.party_type)
    if payload.gst_number:
        ensure_unique(
            session,
            Party,
            gst_number=payload.gst_number,
            message=f"GST number '{payload.gst_number}' is already registered.",
        )
    party = Party(
        name=payload.name,
        party_type=payload.party_type,
        contact_person=payload.contact_person,
        phone=payload.phone,
        email=str(payload.email) if payload.email else None,
        gst_number=payload.gst_number,
        notes=payload.notes,
        stage=payload.stage,
        source=PartySource.DESK,
    )
    session.add(party)
    session.flush()

    for location_payload in payload.locations:
        add_party_location(session, party.id, location_payload, user_id, _audit=False)
    for product_payload in payload.products:
        add_party_product(session, party.id, product_payload, user_id, _audit=False)

    audit.record(
        session,
        user_id=user_id,
        entity_type="party",
        entity_id=party.id,
        action=AuditAction.CREATE,
        new_value={"name": party.name, "party_type": party.party_type.value},
    )
    session.flush()
    return get_party(session, party.id)


def update_party(session: Session, party_id: int, payload: PartyUpdate, user_id: int) -> Party:
    party = get_party(session, party_id)
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"])
    if "name" in data and party.stage != PartyStage.PROSPECT:
        _ensure_name_free(session, data["name"], party.party_type, exclude_id=party.id)
    if data.get("gst_number"):
        ensure_unique(
            session,
            Party,
            gst_number=data["gst_number"],
            exclude_id=party.id,
            message=f"GST number '{data['gst_number']}' is already registered.",
        )
    changes = apply_patch(
        party,
        data,
        {
            "name",
            "contact_person",
            "phone",
            "email",
            "gst_number",
            "notes",
            "status",
        },
    )
    audit.record_changes(
        session,
        user_id=user_id,
        entity_type="party",
        entity_id=party.id,
        changes=changes,
        action=AuditAction.STATUS_CHANGE if "status" in changes else AuditAction.UPDATE,
    )
    return party


# --------------------------------------------------------------------------- #
# Party <-> location links
# --------------------------------------------------------------------------- #
def _clear_other_primaries(session: Session, party_id: int, keep_id: int | None = None) -> None:
    stmt = select(PartyLocation).where(
        PartyLocation.party_id == party_id, PartyLocation.is_primary.is_(True)
    )
    for link in session.execute(stmt).scalars().all():
        if keep_id is None or link.id != keep_id:
            link.is_primary = False
    session.flush()


def add_party_location(
    session: Session,
    party_id: int,
    payload: PartyLocationCreate,
    user_id: int,
    *,
    _audit: bool = True,
) -> PartyLocation:
    party = get_or_404(session, Party, party_id, "Party")
    if payload.location_id is not None:
        location = get_or_404(session, Location, payload.location_id, "Location")
    else:
        assert payload.location is not None  # guaranteed by schema validation
        location = create_location(session, payload.location, user_id)

    existing = session.scalar(
        select(PartyLocation).where(
            PartyLocation.party_id == party.id, PartyLocation.location_id == location.id
        )
    )
    if existing is not None:
        raise ConflictError(f"Location #{location.id} is already linked to {party.name}.")

    has_any = session.scalar(
        select(func.count(PartyLocation.id)).where(PartyLocation.party_id == party.id)
    )
    is_primary = payload.is_primary or not has_any
    if is_primary:
        _clear_other_primaries(session, party.id)

    link = PartyLocation(
        party_id=party.id,
        location_id=location.id,
        location_type=payload.location_type,
        is_primary=is_primary,
    )
    session.add(link)
    session.flush()
    if _audit:
        audit.record(
            session,
            user_id=user_id,
            entity_type="party_location",
            entity_id=link.id,
            action=AuditAction.CREATE,
            new_value={
                "party_id": party.id,
                "location_id": location.id,
                "location_type": link.location_type.value,
            },
        )
    return link


def update_party_location(
    session: Session, party_id: int, link_id: int, payload: PartyLocationUpdate, user_id: int
) -> PartyLocation:
    link = get_or_404(session, PartyLocation, link_id, "Party location")
    if link.party_id != party_id:
        raise ValidationError("This location link belongs to another party.")
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_primary"):
        _clear_other_primaries(session, party_id, keep_id=link.id)
    changes = apply_patch(link, data, {"location_type", "is_primary"})
    audit.record_changes(
        session,
        user_id=user_id,
        entity_type="party_location",
        entity_id=link.id,
        changes=changes,
    )
    return link


def remove_party_location(session: Session, party_id: int, link_id: int, user_id: int) -> None:
    link = get_or_404(session, PartyLocation, link_id, "Party location")
    if link.party_id != party_id:
        raise ValidationError("This location link belongs to another party.")
    audit.record(
        session,
        user_id=user_id,
        entity_type="party_location",
        entity_id=link.id,
        action=AuditAction.UPDATE,
        old_value={"party_id": party_id, "location_id": link.location_id},
        new_value={"removed": True},
    )
    session.delete(link)
    session.flush()


# --------------------------------------------------------------------------- #
# Party <-> product links
# --------------------------------------------------------------------------- #
def _resolve_relationship(
    party: Party, requested: PartyProductRelationship | None
) -> PartyProductRelationship:
    allowed = ALLOWED_RELATIONSHIPS[party.party_type]
    if not allowed:
        raise ValidationError(
            f"{party.party_type.value} parties cannot be linked to products.",
            field="product_id",
        )
    relationship = requested or DEFAULT_RELATIONSHIP[party.party_type]
    if relationship not in allowed:
        allowed_names = ", ".join(sorted(r.value for r in allowed))
        raise ValidationError(
            f"Relationship '{relationship.value}' is not valid for a "
            f"{party.party_type.value}. Allowed: {allowed_names}.",
            field="relationship_type",
        )
    return relationship


def add_party_product(
    session: Session,
    party_id: int,
    payload: PartyProductCreate,
    user_id: int,
    *,
    _audit: bool = True,
) -> PartyProduct:
    party = get_or_404(session, Party, party_id, "Party")
    product = get_or_404(session, Product, payload.product_id, "Product")
    relationship = _resolve_relationship(party, payload.relationship_type)
    require_active(product, "Product")
    ensure_unique(
        session,
        PartyProduct,
        party_id=party.id,
        product_id=product.id,
        relationship_type=relationship,
        message=(
            f"{party.name} is already linked to '{product.display_name}' as {relationship.value}."
        ),
    )
    link = PartyProduct(
        party_id=party.id,
        product_id=product.id,
        relationship_type=relationship,
        notes=payload.notes,
        active=payload.active,
    )
    session.add(link)
    session.flush()
    if _audit:
        audit.record(
            session,
            user_id=user_id,
            entity_type="party_product",
            entity_id=link.id,
            action=AuditAction.CREATE,
            new_value={
                "party_id": party.id,
                "product_id": product.id,
                "relationship_type": relationship.value,
            },
        )
    return link


def update_party_product(
    session: Session, party_id: int, link_id: int, payload: PartyProductUpdate, user_id: int
) -> PartyProduct:
    link = get_or_404(session, PartyProduct, link_id, "Party product")
    if link.party_id != party_id:
        raise ValidationError("This product link belongs to another party.")
    party = get_or_404(session, Party, party_id, "Party")
    data = payload.model_dump(exclude_unset=True)
    if data.get("relationship_type") is not None:
        data["relationship_type"] = _resolve_relationship(party, data["relationship_type"])
        ensure_unique(
            session,
            PartyProduct,
            party_id=party_id,
            product_id=link.product_id,
            relationship_type=data["relationship_type"],
            exclude_id=link.id,
            message="This product is already linked to the party with that relationship.",
        )
    changes = apply_patch(link, data, {"relationship_type", "notes", "active"})
    audit.record_changes(
        session,
        user_id=user_id,
        entity_type="party_product",
        entity_id=link.id,
        changes=changes,
    )
    return link


def remove_party_product(session: Session, party_id: int, link_id: int, user_id: int) -> None:
    link = get_or_404(session, PartyProduct, link_id, "Party product")
    if link.party_id != party_id:
        raise ValidationError("This product link belongs to another party.")
    audit.record(
        session,
        user_id=user_id,
        entity_type="party_product",
        entity_id=link.id,
        action=AuditAction.UPDATE,
        old_value={"party_id": party_id, "product_id": link.product_id},
        new_value={"removed": True},
    )
    session.delete(link)
    session.flush()


# --------------------------------------------------------------------------- #
# Unknown parties: quick create, duplicate detection, merge, promotion
# --------------------------------------------------------------------------- #
def _has_trgm(session: Session) -> bool:
    """pg_trgm powers fuzzy name matching; it is optional, not required."""
    return bool(session.scalar(text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")))


def find_duplicates(
    session: Session,
    *,
    party_type: PartyType | None = None,
    name: str | None = None,
    phone: str | None = None,
    gst_number: str | None = None,
    exclude_id: int | None = None,
    limit: int = 8,
) -> DuplicateCheckResult:
    """Candidates that look like the party somebody is about to create.

    Ranked by how strong the evidence is - GST beats phone beats a similar name -
    and only then by score, so a perfect name match never masks the fact that an
    identifier matched exactly. Deliberately a warning: the trader may genuinely
    have two parties called "Patel Traders".
    """
    #: Stronger evidence wins regardless of similarity score.
    priority = {"exact_gst": 2, "exact_phone": 1, "similar_name": 0}

    found: dict[int, Party] = {}
    #: party id -> (reason, score)
    matches: dict[int, tuple[str, float]] = {}

    def record(party: Party, reason: str, score: float) -> None:
        if party.id == exclude_id or party.stage == PartyStage.MERGED:
            return
        found[party.id] = party
        current = matches.get(party.id)
        if current is None or (priority[reason], score) > (priority[current[0]], current[1]):
            matches[party.id] = (reason, score)

    base = select(Party)
    if party_type is not None:
        base = base.where(Party.party_type == party_type)

    if gst_number:
        rows = (
            session.execute(base.where(func.upper(Party.gst_number) == gst_number.strip().upper()))
            .scalars()
            .all()
        )
        for party in rows:
            record(party, "exact_gst", 1.0)

    normalized = normalize_phone(phone)
    if normalized:
        rows = session.execute(base.where(Party.phone_normalized == normalized)).scalars().all()
        for party in rows:
            record(party, "exact_phone", 0.95)

    cleaned = " ".join((name or "").split())
    if len(cleaned) >= 3:
        if _has_trgm(session):
            # similarity() comes from pg_trgm, enabled in migration 0003.
            similarity = func.similarity(Party.name, cleaned)
            rows = session.execute(
                base.where(similarity > 0.3)
                .order_by(similarity.desc(), Party.name)
                .limit(limit)
                .add_columns(similarity)
            ).all()
        else:
            # Without the extension, fall back to a containment match so the
            # warning still works (just less cleverly).
            rows = [
                (party, 0.5)
                for party in session.execute(
                    base.where(Party.name.ilike(f"%{cleaned}%")).order_by(Party.name).limit(limit)
                )
                .scalars()
                .all()
            ]
        for party, score in rows:
            record(party, "similar_name", float(score))

    cities = _primary_cities(session, list(found))
    ordered = sorted(
        matches.items(),
        key=lambda item: (
            -priority[item[1][0]],
            -item[1][1],
            found[item[0]].name.lower(),
            item[0],
        ),
    )[:limit]

    return DuplicateCheckResult(
        candidates=[
            DuplicateCandidate(
                id=party_id,
                name=found[party_id].name,
                party_type=found[party_id].party_type,
                stage=found[party_id].stage,
                status=found[party_id].status,
                phone=found[party_id].phone,
                gst_number=found[party_id].gst_number,
                city=cities.get(party_id),
                match_reason=reason,
                score=round(score, 3),
            )
            for party_id, (reason, score) in ordered
        ],
        # An identifier matching anywhere is worth surfacing, even if a closer
        # name match pushed it down the list.
        has_exact_match=any(priority[reason] > 0 for reason, _score in matches.values()),
    )


def create_prospect(session: Session, payload: PartyProspectCreate, user_id: int) -> Party:
    """Save an unknown party as a PROSPECT from just a name and a phone number.

    Used by the inquiry forms: the prospect is persisted straight away so it can
    be picked in the form and reused by later inquiries, rather than living only
    inside the inquiry that introduced it.
    """
    return quick_create_party(
        session,
        PartyQuickCreate(name=payload.name, phone=payload.phone),
        party_type=payload.party_type,
        user_id=user_id,
    )


def quick_create_party(
    session: Session,
    payload: PartyQuickCreate,
    *,
    party_type: PartyType,
    user_id: int,
    source: PartySource = PartySource.QUICK_CREATE,
) -> Party:
    """Create a PROSPECT in one step from an inquiry or activity form.

    Only an identifier is required (name or phone). GST stays globally unique, so
    a colliding GST is reported as a conflict pointing at the existing party.
    """
    if payload.gst_number:
        existing = session.scalar(
            select(Party).where(
                func.upper(Party.gst_number) == payload.gst_number,
                Party.stage != PartyStage.MERGED,
            )
        )
        if existing is not None:
            raise ConflictError(
                f"GST {payload.gst_number} already belongs to '{existing.name}' "
                f"(party #{existing.id}). Use that party instead."
            )

    party = Party(
        name=payload.display_name,
        party_type=party_type,
        contact_person=payload.contact_person,
        phone=payload.phone,
        email=str(payload.email) if payload.email else None,
        gst_number=payload.gst_number,
        notes=payload.notes,
        stage=PartyStage.PROSPECT,
        source=source,
    )
    session.add(party)
    session.flush()

    if payload.city:
        add_party_location(
            session,
            party.id,
            PartyLocationCreate(
                location=LocationCreate(city=payload.city),
                location_type=LocationType.OTHER,
                is_primary=True,
            ),
            user_id,
            _audit=False,
        )

    audit.record(
        session,
        user_id=user_id,
        entity_type="party",
        entity_id=party.id,
        action=AuditAction.CREATE,
        new_value={
            "name": party.name,
            "party_type": party_type.value,
            "stage": PartyStage.PROSPECT.value,
            "source": source.value,
        },
    )
    session.flush()
    return party


def promote_party(session: Session, party_id: int, user_id: int) -> Party:
    """PROSPECT -> ACTIVE once the relationship is real."""
    party = get_or_404(session, Party, party_id, "Party")
    if party.stage == PartyStage.MERGED:
        raise ConflictError(
            f"Party #{party.id} was merged into #{party.merged_into_id} and cannot be promoted."
        )
    if party.stage == PartyStage.ACTIVE:
        return party

    _ensure_name_free(session, party.name, party.party_type, exclude_id=party.id)
    party.stage = PartyStage.ACTIVE
    audit.record(
        session,
        user_id=user_id,
        entity_type="party",
        entity_id=party.id,
        action=AuditAction.PROMOTE,
        old_value={"stage": PartyStage.PROSPECT.value},
        new_value={"stage": PartyStage.ACTIVE.value},
    )
    return party


def merge_parties(
    session: Session, survivor_id: int, loser_id: int, user_id: int, note: str | None = None
) -> dict:
    """Fold ``loser`` into ``survivor``, keeping every historical reference.

    Link tables are de-duplicated while repointing, because they carry unique
    constraints. Nothing is deleted: the loser is kept as MERGED so old links and
    audit history still resolve.
    """
    if survivor_id == loser_id:
        raise ValidationError("A party cannot be merged into itself.", field="loser_id")

    survivor = get_or_404(session, Party, survivor_id, "Party")
    loser = get_or_404(session, Party, loser_id, "Party")

    if survivor.party_type != loser.party_type:
        raise ValidationError(
            f"Cannot merge a {loser.party_type.value} into a {survivor.party_type.value}.",
            field="loser_id",
        )
    for party in (survivor, loser):
        if party.stage == PartyStage.MERGED:
            raise ConflictError(f"Party #{party.id} has already been merged.")

    moved: dict[str, int] = {}

    def repoint(table, column: str) -> None:
        result = session.execute(
            update(table).where(getattr(table, column) == loser.id).values(**{column: survivor.id})
        )
        if result.rowcount:
            moved[table.__tablename__] = moved.get(table.__tablename__, 0) + result.rowcount

    # Business records: straight repoint, no unique constraints in the way.
    repoint(CustomerInquiry, "customer_id")
    repoint(SupplierInquiry, "supplier_id")
    repoint(TransportInquiry, "transporter_id")
    repoint(Activity, "party_id")
    repoint(Note, "party_id")

    # Product links: unique (party_id, product_id, relationship_type).
    survivor_products = {
        (link.product_id, link.relationship_type)
        for link in session.execute(
            select(PartyProduct).where(PartyProduct.party_id == survivor.id)
        )
        .scalars()
        .all()
    }
    for link in (
        session.execute(select(PartyProduct).where(PartyProduct.party_id == loser.id))
        .scalars()
        .all()
    ):
        key = (link.product_id, link.relationship_type)
        if key in survivor_products:
            session.delete(link)
            moved["party_products_deduped"] = moved.get("party_products_deduped", 0) + 1
        else:
            link.party_id = survivor.id
            survivor_products.add(key)
            moved["party_products"] = moved.get("party_products", 0) + 1

    # Location links: unique (party_id, location_id) + one primary per party.
    survivor_locations = {
        link.location_id
        for link in session.execute(
            select(PartyLocation).where(PartyLocation.party_id == survivor.id)
        )
        .scalars()
        .all()
    }
    survivor_has_primary = session.scalar(
        select(func.count(PartyLocation.id)).where(
            PartyLocation.party_id == survivor.id, PartyLocation.is_primary.is_(True)
        )
    )
    for link in (
        session.execute(select(PartyLocation).where(PartyLocation.party_id == loser.id))
        .scalars()
        .all()
    ):
        if link.location_id in survivor_locations:
            session.delete(link)
            moved["party_locations_deduped"] = moved.get("party_locations_deduped", 0) + 1
            continue
        link.party_id = survivor.id
        if link.is_primary and survivor_has_primary:
            link.is_primary = False
        elif link.is_primary:
            survivor_has_primary = 1
        survivor_locations.add(link.location_id)
        moved["party_locations"] = moved.get("party_locations", 0) + 1
    session.flush()

    # Fill in details the survivor is missing, then retire the loser.
    for field in ("phone", "email", "gst_number", "contact_person"):
        if getattr(survivor, field) is None and getattr(loser, field) is not None:
            setattr(survivor, field, getattr(loser, field))
    if note:
        survivor.notes = f"{survivor.notes}\n{note}" if survivor.notes else note

    loser.gst_number = None  # free the globally unique key for the survivor
    loser.stage = PartyStage.MERGED
    loser.status = RecordStatus.INACTIVE
    loser.merged_into_id = survivor.id
    session.flush()

    audit.record(
        session,
        user_id=user_id,
        entity_type="party",
        entity_id=survivor.id,
        action=AuditAction.MERGE,
        old_value={"merged_party_id": loser.id, "merged_party_name": loser.name},
        new_value={"survivor_id": survivor.id, "moved": moved, "note": note},
    )
    return moved


def stale_prospect_cutoff(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


# --- applications -----------------------------------------------------------
def add_party_application(
    session: Session,
    party_id: int,
    payload: PartyApplicationCreate,
    user_id: int,
    *,
    _audit: bool = True,
) -> PartyApplication:
    """Record that a party works in an end-use (pipes, windows, raffia).

    Unlike a product link this carries no buy/sell direction: an application
    describes the party's line of business, which is the same fact whichever
    side of a trade they happen to be on today.
    """
    party = get_or_404(session, Party, party_id, "Party")
    application = get_or_404(session, Application, payload.application_id, "Application")
    require_active(application, "Application")
    ensure_unique(
        session,
        PartyApplication,
        party_id=party.id,
        application_id=application.id,
        message=f"{party.name} is already linked to '{application.name}'.",
    )
    link = PartyApplication(
        party_id=party.id,
        application_id=application.id,
        notes=payload.notes,
        active=payload.active,
    )
    session.add(link)
    session.flush()
    if _audit:
        audit.record(
            session,
            user_id=user_id,
            entity_type="party_application",
            entity_id=link.id,
            action=AuditAction.CREATE,
            new_value={"party_id": party.id, "application_id": application.id},
        )
    return link


def update_party_application(
    session: Session,
    party_id: int,
    link_id: int,
    payload: PartyApplicationUpdate,
    user_id: int,
) -> PartyApplication:
    link = get_or_404(session, PartyApplication, link_id, "Party application")
    if link.party_id != party_id:
        raise ValidationError("This application link belongs to another party.")
    changes = apply_patch(link, payload.model_dump(exclude_unset=True), {"notes", "active"})
    audit.record_changes(
        session,
        user_id=user_id,
        entity_type="party_application",
        entity_id=link.id,
        changes=changes,
    )
    return link


def remove_party_application(session: Session, party_id: int, link_id: int, user_id: int) -> None:
    link = get_or_404(session, PartyApplication, link_id, "Party application")
    if link.party_id != party_id:
        raise ValidationError("This application link belongs to another party.")
    audit.record(
        session,
        user_id=user_id,
        entity_type="party_application",
        entity_id=link.id,
        action=AuditAction.UPDATE,
        old_value={"party_id": party_id, "application_id": link.application_id},
        new_value={"removed": True},
    )
    session.delete(link)
    session.flush()
