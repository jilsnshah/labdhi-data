"""Inquiry services: create a recorded quotation, edit it, and set its status."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError, ValidationError
from app.models.enums import (
    AuditAction,
    InquirySource,
    InquiryStatus,
    InquiryType,
    PartyStage,
    PartyType,
)
from app.models.inquiry import (
    CustomerInquiry,
    Inquiry,
    SupplierInquiry,
    TransportInquiry,
)
from app.models.masters import Product
from app.models.party import Location, Party
from app.schemas.inquiry import (
    CustomerInquiryCreate,
    InquiryCreate,
    InquiryUpdate,
    SupplierInquiryCreate,
    TransportInquiryCreate,
)
from app.services import audit
from app.services.common import require_active

DETAIL_LOADERS = (
    selectinload(Inquiry.customer_detail),
    selectinload(Inquiry.supplier_detail),
    selectinload(Inquiry.transport_detail),
)

#: Which party type each inquiry type is recorded against.
PARTY_TYPE = {
    InquiryType.CUSTOMER: PartyType.CUSTOMER,
    InquiryType.SUPPLIER: PartyType.SUPPLIER,
    InquiryType.TRANSPORT: PartyType.TRANSPORTER,
}

#: Fields a PATCH may touch, per inquiry type. Anything else is refused so a
#: rate never lands on a transport inquiry or a route on a supplier quote.
EDITABLE = {
    InquiryType.CUSTOMER: {"party_id", "product_id", "quantity", "unit", "location_id", "rate"},
    InquiryType.SUPPLIER: {"party_id", "product_id", "quantity", "unit", "location_id", "rate"},
    InquiryType.TRANSPORT: {
        "party_id",
        "quantity",
        "unit",
        "pickup_location_id",
        "delivery_location_id",
        "price",
    },
}


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #
def _party(session: Session, party_id: int, expected: PartyType, field: str) -> Party:
    party = session.get(Party, party_id)
    if party is None:
        raise ValidationError(f"Party #{party_id} was not found.", field=field)
    if party.stage == PartyStage.MERGED:
        raise ValidationError(
            f"Party '{party.name}' was merged into #{party.merged_into_id}; "
            "use that party instead.",
            field=field,
        )
    if party.party_type != expected:
        raise ValidationError(
            f"Party '{party.name}' is a {party.party_type.value}; a {expected.value} "
            f"is required here.",
            field=field,
        )
    require_active(party, expected.value.capitalize())
    return party


def _product(session: Session, product_id: int) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise ValidationError(f"Product #{product_id} was not found.", field="product_id")
    require_active(product, "Product")
    return product


def _location(session: Session, location_id: int, field: str) -> Location:
    """Any active Master Data location - never filtered by the inquiry's party."""
    location = session.get(Location, location_id)
    if location is None:
        raise ValidationError(f"Location #{location_id} was not found.", field=field)
    require_active(location, "Location")
    return location


def _money(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


# --------------------------------------------------------------------------- #
# Create
# --------------------------------------------------------------------------- #
def _new_header(
    session: Session,
    inquiry_type: InquiryType,
    status: InquiryStatus,
    user_id: int | None,
    source: InquirySource = InquirySource.DESK,
) -> Inquiry:
    now = datetime.now(UTC)
    closed = status == InquiryStatus.CLOSED
    inquiry = Inquiry(
        inquiry_type=inquiry_type,
        status=status,
        source=source,
        created_by=user_id,
        closed_at=now if closed else None,
        closed_by=user_id if closed else None,
    )
    session.add(inquiry)
    session.flush()
    return inquiry


def _create_customer(
    session: Session,
    payload: CustomerInquiryCreate,
    status: InquiryStatus,
    user_id: int | None,
    source: InquirySource = InquirySource.DESK,
) -> Inquiry:
    customer = _party(session, payload.customer_id, PartyType.CUSTOMER, "customer_id")
    product = _product(session, payload.product_id)
    if payload.location_id is not None:
        _location(session, payload.location_id, "location_id")

    inquiry = _new_header(session, InquiryType.CUSTOMER, status, user_id, source)
    session.add(
        CustomerInquiry(
            inquiry_id=inquiry.id,
            customer_id=customer.id,
            product_id=product.id,
            quantity=payload.quantity,
            unit=payload.unit,
            location_id=payload.location_id,
            rate=payload.rate,
        )
    )
    session.flush()
    _audit_create(
        session,
        inquiry,
        user_id,
        party_id=customer.id,
        product_id=product.id,
        quantity=payload.quantity,
        unit=payload.unit.value,
        location_id=payload.location_id,
        rate=_money(payload.rate),
    )
    return inquiry


def _create_supplier(
    session: Session,
    payload: SupplierInquiryCreate,
    status: InquiryStatus,
    user_id: int | None,
    source: InquirySource = InquirySource.DESK,
) -> Inquiry:
    supplier = _party(session, payload.supplier_id, PartyType.SUPPLIER, "supplier_id")
    product = _product(session, payload.product_id)
    if payload.location_id is not None:
        _location(session, payload.location_id, "location_id")

    inquiry = _new_header(session, InquiryType.SUPPLIER, status, user_id, source)
    session.add(
        SupplierInquiry(
            inquiry_id=inquiry.id,
            supplier_id=supplier.id,
            product_id=product.id,
            quantity=payload.quantity,
            unit=payload.unit,
            location_id=payload.location_id,
            rate=payload.rate,
        )
    )
    session.flush()
    _audit_create(
        session,
        inquiry,
        user_id,
        party_id=supplier.id,
        product_id=product.id,
        quantity=payload.quantity,
        unit=payload.unit.value,
        location_id=payload.location_id,
        rate=_money(payload.rate),
    )
    return inquiry


def _create_transport(
    session: Session,
    payload: TransportInquiryCreate,
    status: InquiryStatus,
    user_id: int | None,
    source: InquirySource = InquirySource.DESK,
) -> Inquiry:
    transporter = _party(session, payload.transporter_id, PartyType.TRANSPORTER, "transporter_id")
    _location(session, payload.pickup_location_id, "pickup_location_id")
    _location(session, payload.delivery_location_id, "delivery_location_id")

    inquiry = _new_header(session, InquiryType.TRANSPORT, status, user_id, source)
    session.add(
        TransportInquiry(
            inquiry_id=inquiry.id,
            transporter_id=transporter.id,
            quantity=payload.quantity,
            unit=payload.unit,
            pickup_location_id=payload.pickup_location_id,
            delivery_location_id=payload.delivery_location_id,
            price=payload.price,
        )
    )
    session.flush()
    _audit_create(
        session,
        inquiry,
        user_id,
        party_id=transporter.id,
        quantity=payload.quantity,
        unit=payload.unit.value,
        pickup_location_id=payload.pickup_location_id,
        delivery_location_id=payload.delivery_location_id,
        price=_money(payload.price),
    )
    return inquiry


def _audit_create(session: Session, inquiry: Inquiry, user_id: int | None, **fields) -> None:
    audit.record(
        session,
        user_id=user_id,
        entity_type="inquiry",
        entity_id=inquiry.id,
        action=AuditAction.CREATE,
        new_value={
            "inquiry_type": inquiry.inquiry_type.value,
            "status": inquiry.status.value,
            **{
                key: str(value) if isinstance(value, Decimal) else value
                for key, value in fields.items()
            },
        },
    )


def create_inquiry(
    session: Session,
    payload: InquiryCreate,
    user_id: int | None,
    source: InquirySource = InquirySource.DESK,
) -> Inquiry:
    """Record an inquiry.

    ``user_id`` is None, and ``source`` PORTAL, when a party raised this
    themselves through their own link: there is no salesperson behind it, and
    the row says so rather than borrowing somebody's name.
    """
    if payload.inquiry_type == InquiryType.CUSTOMER:
        assert payload.customer is not None
        inquiry = _create_customer(session, payload.customer, payload.status, user_id, source)
    elif payload.inquiry_type == InquiryType.SUPPLIER:
        assert payload.supplier is not None
        inquiry = _create_supplier(session, payload.supplier, payload.status, user_id, source)
    else:
        assert payload.transport is not None
        inquiry = _create_transport(session, payload.transport, payload.status, user_id, source)
    session.flush()
    return get_inquiry(session, inquiry.id)


# --------------------------------------------------------------------------- #
# Read / update / status
# --------------------------------------------------------------------------- #
def get_inquiry(session: Session, inquiry_id: int) -> Inquiry:
    inquiry = session.get(Inquiry, inquiry_id, options=list(DETAIL_LOADERS))
    if inquiry is None:
        raise NotFoundError(f"Inquiry #{inquiry_id} was not found.")
    return inquiry


def _detail(inquiry: Inquiry) -> CustomerInquiry | SupplierInquiry | TransportInquiry:
    detail = inquiry.customer_detail or inquiry.supplier_detail or inquiry.transport_detail
    if detail is None:  # pragma: no cover - every inquiry is created with its detail row
        raise NotFoundError(f"Inquiry #{inquiry.id} has no detail record.")
    return detail


#: The detail-row column that holds the party, per inquiry type.
PARTY_COLUMN = {
    InquiryType.CUSTOMER: "customer_id",
    InquiryType.SUPPLIER: "supplier_id",
    InquiryType.TRANSPORT: "transporter_id",
}


def set_status(session: Session, inquiry: Inquiry, new_status: InquiryStatus, user_id: int) -> None:
    """ACTIVE <-> CLOSED, in either direction. Closing stamps who and when."""
    if new_status == inquiry.status:
        return
    old = inquiry.status
    inquiry.status = new_status
    if new_status == InquiryStatus.CLOSED:
        inquiry.closed_at = datetime.now(UTC)
        inquiry.closed_by = user_id
    else:
        inquiry.closed_at = None
        inquiry.closed_by = None
    audit.record(
        session,
        user_id=user_id,
        entity_type="inquiry",
        entity_id=inquiry.id,
        action=AuditAction.STATUS_CHANGE,
        old_value={"status": old.value},
        new_value={"status": new_status.value},
    )


def update_inquiry(
    session: Session, inquiry_id: int, payload: InquiryUpdate, user_id: int
) -> Inquiry:
    inquiry = get_inquiry(session, inquiry_id)
    data = payload.model_dump(exclude_unset=True)
    status = data.pop("status", None)

    not_allowed = sorted(set(data) - EDITABLE[inquiry.inquiry_type])
    if not_allowed:
        raise ValidationError(
            f"{', '.join(not_allowed)} cannot be set on a "
            f"{inquiry.inquiry_type.value.lower()} inquiry.",
            field=not_allowed[0],
        )

    # Required fields may be changed but not emptied.
    for field in (
        "party_id",
        "product_id",
        "quantity",
        "unit",
        "pickup_location_id",
        "delivery_location_id",
    ):
        if field in data and data[field] is None:
            raise ValidationError(f"{field} cannot be empty.", field=field)

    detail = _detail(inquiry)
    if "party_id" in data:
        _party(session, data["party_id"], PARTY_TYPE[inquiry.inquiry_type], "party_id")
        data[PARTY_COLUMN[inquiry.inquiry_type]] = data.pop("party_id")
    if "product_id" in data:
        _product(session, data["product_id"])
    for field in ("location_id", "pickup_location_id", "delivery_location_id"):
        if data.get(field) is not None:
            _location(session, data[field], field)

    if inquiry.inquiry_type == InquiryType.TRANSPORT:
        pickup = data.get("pickup_location_id", detail.pickup_location_id)
        drop = data.get("delivery_location_id", detail.delivery_location_id)
        if pickup == drop:
            raise ValidationError(
                "Pickup and drop locations must be different.", field="delivery_location_id"
            )

    changes: dict[str, list] = {}
    for field, new in data.items():
        old = getattr(detail, field)
        if old != new:
            setattr(detail, field, new)
            changes[field] = [_plain(old), _plain(new)]
    if changes:
        audit.record_changes(
            session,
            user_id=user_id,
            entity_type="inquiry",
            entity_id=inquiry.id,
            changes=changes,
        )

    if status is not None:
        set_status(session, inquiry, status, user_id)

    session.flush()
    # Changing a party or location id leaves the joined relationship pointing at
    # the old row until it is reloaded.
    session.expire(detail)
    session.expire(inquiry)
    return get_inquiry(session, inquiry.id)


def _plain(value):
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)
