"""Enquiries parties raise themselves, and what the desk does with them.

Two halves, with a deliberate gap between them. On the public side a party
types what they want into their own link and it is written down as they wrote
it - no master data is required of them and nothing they send can reach the
book. On the desk side those words are read, mapped onto a real product and
location, and accepted, which is the moment an inquiry exists.

What the form is never allowed to decide:

* **Who is asking.** The party comes from the code in the link.
* **What kind of enquiry it is.** A customer raises a customer enquiry, a
  supplier a supplier one, a transporter a load. The party's own type decides,
  so nobody can quote into the wrong book.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.pagination import PageParams, paginate
from app.models.enums import (
    AuditAction,
    InquiryType,
    PartyType,
    PortalEnquiryStatus,
    RecordStatus,
)
from app.models.masters import Product, product_applications
from app.models.party import Party
from app.models.portal_enquiry import PortalEnquiry
from app.schemas.inquiry import (
    CustomerInquiryCreate,
    InquiryCreate,
    SupplierInquiryCreate,
    TransportInquiryCreate,
)
from app.schemas.portal_enquiry import EnquiryAcceptRequest, PortalEnquiryRequest
from app.services import audit, inquiries
from app.services.common import get_or_404
from app.services.portal import party_by_code

#: What a party of each kind is raising when they fill the form in.
ENQUIRY_OF = {
    PartyType.CUSTOMER: InquiryType.CUSTOMER,
    PartyType.SUPPLIER: InquiryType.SUPPLIER,
    PartyType.TRANSPORTER: InquiryType.TRANSPORT,
}

#: How many grades the public picker will return at once.
PRODUCT_PICKER_LIMIT = 25


def _now() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------- #
# The party's side
# --------------------------------------------------------------------------- #
def search_products(session: Session, query: str | None, limit: int = PRODUCT_PICKER_LIMIT):
    """Grades a party can pick from, by name.

    Only active products, only the name and the id. The product master is
    material, grade and manufacturer - nothing in it belongs to another party,
    which is why it can be offered on a public form at all.
    """
    statement = (
        select(Product)
        .where(Product.status == RecordStatus.ACTIVE)
        .order_by(Product.display_name)
        .limit(min(limit, PRODUCT_PICKER_LIMIT))
    )
    text = (query or "").strip()
    if text:
        statement = statement.where(Product.display_name.ilike(f"%{text}%"))
    return list(session.scalars(statement).all())


def submit(session: Session, code: str, payload: PortalEnquiryRequest) -> PortalEnquiry:
    """Record an enquiry a party raised through their own link."""
    party = party_by_code(session, code)
    enquiry_type = ENQUIRY_OF[party.party_type]

    product_id = payload.product_id
    if product_id is not None:
        product = session.get(Product, product_id)
        if product is None or product.status != RecordStatus.ACTIVE:
            raise ValidationError("That product is not one we carry.")

    if enquiry_type is InquiryType.TRANSPORT:
        if not payload.from_place or not payload.to_place:
            raise ValidationError("Tell us where the load is picked up and where it goes.")
    elif product_id is None and not payload.product_text:
        raise ValidationError("Tell us which material or grade this is about.")

    enquiry = PortalEnquiry(
        party_id=party.id,
        inquiry_type=enquiry_type,
        product_id=product_id,
        # Their own words are kept only when they are not pointing at a grade
        # we have: two names for one thing would just be a question later.
        product_text=None if product_id is not None else payload.product_text,
        quantity=payload.quantity,
        unit=payload.unit,
        from_place=payload.from_place,
        to_place=payload.to_place,
        rate=payload.rate,
        notes=payload.notes,
        status=PortalEnquiryStatus.NEW,
    )
    session.add(enquiry)
    session.flush()
    return enquiry


def mine(session: Session, code: str, limit: int = 20) -> list[PortalEnquiry]:
    """What this party has sent in, newest first.

    Shown back to them because somebody who sends an enquiry into a form is
    owed the knowledge that it arrived and was read.
    """
    party = party_by_code(session, code)
    return list(
        session.scalars(
            select(PortalEnquiry)
            .where(PortalEnquiry.party_id == party.id)
            .order_by(PortalEnquiry.created_at.desc())
            .limit(limit)
        ).all()
    )


# --------------------------------------------------------------------------- #
# The desk's side
# --------------------------------------------------------------------------- #
def _filtered(
    *,
    status: PortalEnquiryStatus | None,
    enquiry_type: InquiryType | None,
    party_id: int | None,
    product_id: int | None,
    material_id: int | None,
    grade_id: int | None,
    manufacturer_id: int | None,
    application_id: int | None,
    search: str | None,
) -> Select:
    """The inbox, narrowed the same way the enquiry and party lists are."""
    statement = select(PortalEnquiry)
    if status is not None:
        statement = statement.where(PortalEnquiry.status == status)
    if enquiry_type is not None:
        statement = statement.where(PortalEnquiry.inquiry_type == enquiry_type)
    if party_id is not None:
        statement = statement.where(PortalEnquiry.party_id == party_id)
    if product_id is not None:
        statement = statement.where(PortalEnquiry.product_id == product_id)

    # The product filters only reach enquiries whose grade we recognised; one
    # typed as free text has no material or manufacturer to match on.
    product_filters = (material_id, grade_id, manufacturer_id, application_id)
    if any(value is not None for value in product_filters):
        products = select(Product.id)
        if material_id is not None:
            products = products.where(Product.material_id == material_id)
        if grade_id is not None:
            products = products.where(Product.grade_id == grade_id)
        if manufacturer_id is not None:
            products = products.where(Product.manufacturer_id == manufacturer_id)
        if application_id is not None:
            products = products.where(
                Product.id.in_(
                    select(product_applications.c.product_id).where(
                        product_applications.c.application_id == application_id
                    )
                )
            )
        statement = statement.where(PortalEnquiry.product_id.in_(products))

    text = (search or "").strip()
    if text:
        like = f"%{text}%"
        statement = statement.where(
            or_(
                PortalEnquiry.product_text.ilike(like),
                PortalEnquiry.from_place.ilike(like),
                PortalEnquiry.to_place.ilike(like),
                PortalEnquiry.notes.ilike(like),
                PortalEnquiry.party_id.in_(select(Party.id).where(Party.name.ilike(like))),
                PortalEnquiry.product_id.in_(
                    select(Product.id).where(Product.display_name.ilike(like))
                ),
            )
        )
    return statement


def list_for_desk(
    session: Session,
    params: PageParams,
    *,
    status: PortalEnquiryStatus | None = None,
    enquiry_type: InquiryType | None = None,
    party_id: int | None = None,
    product_id: int | None = None,
    material_id: int | None = None,
    grade_id: int | None = None,
    manufacturer_id: int | None = None,
    application_id: int | None = None,
    search: str | None = None,
):
    """The inbox, a page at a time. Waiting ones first, then newest."""
    statement = _filtered(
        status=status,
        enquiry_type=enquiry_type,
        party_id=party_id,
        product_id=product_id,
        material_id=material_id,
        grade_id=grade_id,
        manufacturer_id=manufacturer_id,
        application_id=application_id,
        search=search,
    ).order_by(
        # NEW sorts before the rest, so the desk reads what is waiting first.
        (PortalEnquiry.status != PortalEnquiryStatus.NEW),
        PortalEnquiry.created_at.desc(),
    )
    return paginate(session, statement, params)


def counts(session: Session) -> dict[str, int]:
    """How many are waiting, accepted and declined - for the nav badge."""
    rows = session.execute(
        select(PortalEnquiry.status, func.count()).group_by(PortalEnquiry.status)
    ).all()
    tally = {status.value.lower(): 0 for status in PortalEnquiryStatus}
    for status, total in rows:
        key = status.value.lower() if hasattr(status, "value") else str(status).lower()
        tally[key] = total
    return tally


def get_enquiry(session: Session, enquiry_id: int) -> PortalEnquiry:
    return get_or_404(session, PortalEnquiry, enquiry_id, "Enquiry")


def _must_be_new(enquiry: PortalEnquiry) -> None:
    if enquiry.status != PortalEnquiryStatus.NEW:
        raise ConflictError(f"This enquiry has already been {enquiry.status.value.lower()}.")


def _mark_handled(
    session: Session,
    enquiry: PortalEnquiry,
    status: PortalEnquiryStatus,
    user_id: int,
    *,
    inquiry_id: int | None = None,
) -> None:
    """Record the decision, and who made it.

    ``handler`` is eagerly joined, so it was loaded as nothing when the row
    was fetched; expiring it makes the next read fetch the user who decided.
    """
    enquiry.status = status
    enquiry.inquiry_id = inquiry_id
    enquiry.handled_by = user_id
    enquiry.handled_at = _now()
    session.flush()
    session.expire(enquiry, ["handler", "inquiry"])


def accept(
    session: Session, enquiry_id: int, payload: EnquiryAcceptRequest, user_id: int
) -> PortalEnquiry:
    """Turn a party's words into an inquiry on the desk's own terms.

    The desk names the product and the location, because the party could only
    type text. Quantity, unit and rate carry over from what they sent unless
    the desk corrects them - what arrived is a starting point, not a record.

    The inquiry is created through the ordinary create path, so it is validated,
    audited and owned by whoever accepted it, exactly like one keyed in by hand.
    """
    enquiry = get_enquiry(session, enquiry_id)
    _must_be_new(enquiry)

    quantity: Decimal = payload.quantity if payload.quantity is not None else enquiry.quantity
    unit = payload.unit or enquiry.unit
    rate = payload.rate if payload.rate is not None else enquiry.rate
    product_id = payload.product_id or enquiry.product_id

    if enquiry.inquiry_type is InquiryType.TRANSPORT:
        if payload.pickup_location_id is None or payload.delivery_location_id is None:
            raise ValidationError("A transport inquiry needs a pickup and a delivery location.")
        create = InquiryCreate(
            inquiry_type=InquiryType.TRANSPORT,
            transport=TransportInquiryCreate(
                transporter_id=enquiry.party_id,
                quantity=quantity,
                unit=unit,
                pickup_location_id=payload.pickup_location_id,
                delivery_location_id=payload.delivery_location_id,
                price=rate,
            ),
        )
    elif product_id is None:
        raise ValidationError("Pick the product this enquiry is for.")
    elif enquiry.inquiry_type is InquiryType.CUSTOMER:
        create = InquiryCreate(
            inquiry_type=InquiryType.CUSTOMER,
            customer=CustomerInquiryCreate(
                customer_id=enquiry.party_id,
                product_id=product_id,
                quantity=quantity,
                unit=unit,
                location_id=payload.location_id,
                rate=rate,
            ),
        )
    else:
        create = InquiryCreate(
            inquiry_type=InquiryType.SUPPLIER,
            supplier=SupplierInquiryCreate(
                supplier_id=enquiry.party_id,
                product_id=product_id,
                quantity=quantity,
                unit=unit,
                location_id=payload.location_id,
                rate=rate,
            ),
        )

    inquiry = inquiries.create_inquiry(session, create, user_id)

    _mark_handled(session, enquiry, PortalEnquiryStatus.ACCEPTED, user_id, inquiry_id=inquiry.id)
    audit.record(
        session,
        user_id=user_id,
        entity_type="portal_enquiry",
        entity_id=enquiry.id,
        action=AuditAction.UPDATE,
        new_value={"status": PortalEnquiryStatus.ACCEPTED.value, "inquiry_id": inquiry.id},
    )
    return enquiry


def decline(session: Session, enquiry_id: int, user_id: int) -> PortalEnquiry:
    """Read and not taken up. The party's words stay on the record."""
    enquiry = get_enquiry(session, enquiry_id)
    _must_be_new(enquiry)
    _mark_handled(session, enquiry, PortalEnquiryStatus.DECLINED, user_id)
    audit.record(
        session,
        user_id=user_id,
        entity_type="portal_enquiry",
        entity_id=enquiry.id,
        action=AuditAction.UPDATE,
        new_value={"status": PortalEnquiryStatus.DECLINED.value},
    )
    return enquiry


def link_for(session: Session, party_id: int, base_url: str) -> dict[str, str | int]:
    """The enquiry link for one party, for the desk to copy and send.

    Issuing a code is the whole act of giving a party a way in, so this is
    where it happens for enquiries - the same code their bid links use.
    """
    from app.services.portal import portal_code

    party = get_or_404(session, Party, party_id, "Party")
    if party.status != RecordStatus.ACTIVE or party.merged_into_id is not None:
        raise ValidationError("This party cannot be given a portal link.")
    code = portal_code(session, party)
    root = base_url.rstrip("/")
    return {
        "party_id": party.id,
        "enquiry_link": f"{root}/portal/{code}/enquire",
        "portal_link": f"{root}/portal/{code}",
    }


__all__ = [
    "ENQUIRY_OF",
    "NotFoundError",
    "accept",
    "counts",
    "decline",
    "get_enquiry",
    "link_for",
    "list_for_desk",
    "mine",
    "search_products",
    "submit",
]
