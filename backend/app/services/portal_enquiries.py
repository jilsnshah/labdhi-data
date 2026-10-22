"""Enquiries parties raise themselves, straight onto the book.

A party opens their link, says what they want, and an inquiry exists. There is
no queue and nobody to approve it: the desk sees it in the inquiries list the
moment it arrives, marked as having come from the party rather than the desk.

The price of that is this module's real work - turning what somebody typed on a
phone into rows. They are asked for a material, then a grade of it, then a
manufacturer, each from a list of ours; anything they cannot find there they
type, and it is created. The three together make a product, created too if that
combination is new. A town they name becomes a location the same way.

Everything is matched case-insensitively against what we already have before
anything is created, because "pvc" and "PVC" are the same material and a master
list that holds both is worse than useless. What is created this way carries no
user in the audit log, which is how the desk tells it apart from its own work.

What the form is never allowed to decide:

* **Who is asking.** The party comes from the code in the link.
* **What kind of enquiry it is.** A customer raises a customer inquiry, a
  supplier a supplier one, a transporter a load. Their own type decides, so
  nobody can quote into the wrong book.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.core.pagination import PageParams, paginate
from app.models.enums import (
    AuditAction,
    InquirySource,
    InquiryType,
    PartyType,
    RecordStatus,
)
from app.models.inquiry import Inquiry
from app.models.masters import Grade, Manufacturer, Material, Product, product_applications
from app.models.party import Location, Party
from app.models.portal_enquiry import PortalEnquiry
from app.schemas.inquiry import (
    CustomerInquiryCreate,
    InquiryCreate,
    SupplierInquiryCreate,
    TransportInquiryCreate,
)
from app.schemas.portal_enquiry import PortalEnquiryRequest
from app.services import audit, inquiries
from app.services.common import get_or_404
from app.services.masters import build_display_name
from app.services.portal import party_by_code

#: What a party of each kind is raising when they fill the form in.
ENQUIRY_OF = {
    PartyType.CUSTOMER: InquiryType.CUSTOMER,
    PartyType.SUPPLIER: InquiryType.SUPPLIER,
    PartyType.TRANSPORTER: InquiryType.TRANSPORT,
}

#: How many rows a picker on the public form will return at once.
PICKER_LIMIT = 25


# --------------------------------------------------------------------------- #
# The pickers
# --------------------------------------------------------------------------- #
def _search(session: Session, model, query: str | None, extra=None, limit: int = PICKER_LIMIT):
    """Active rows whose name contains what they have typed so far."""
    statement = (
        select(model)
        .where(model.status == RecordStatus.ACTIVE)
        .order_by(model.name)
        .limit(min(limit, PICKER_LIMIT))
    )
    if extra is not None:
        statement = statement.where(extra)
    text = (query or "").strip()
    if text:
        statement = statement.where(model.name.ilike(f"%{text}%"))
    return list(session.scalars(statement).all())


def search_materials(session: Session, query: str | None = None):
    return _search(session, Material, query)


def search_grades(session: Session, material_id: int | None, query: str | None = None):
    """Grades of one material. A grade means nothing without its material."""
    extra = Grade.material_id == material_id if material_id is not None else None
    return _search(session, Grade, query, extra)


def search_manufacturers(session: Session, query: str | None = None):
    return _search(session, Manufacturer, query)


# --------------------------------------------------------------------------- #
# Turning words into rows
# --------------------------------------------------------------------------- #
def _existing(session: Session, model, name: str, extra=None):
    """A row of this name, whatever case it was typed in."""
    statement = select(model).where(func.lower(model.name) == name.lower())
    if extra is not None:
        statement = statement.where(extra)
    return session.scalars(statement.limit(1)).first()


def _made(session: Session, entity_type: str, row) -> None:
    """Record master data a party created. No user, because there was none."""
    audit.record(
        session,
        user_id=None,
        entity_type=entity_type,
        entity_id=row.id,
        action=AuditAction.CREATE,
        new_value={"name": row.name, "created_from": "portal"},
    )


def _resolve_material(session: Session, chosen: int | None, typed: str | None) -> Material:
    if chosen is not None:
        return get_or_404(session, Material, chosen, "Material")
    if not typed:
        raise ValidationError("Tell us which material this is about.")
    found = _existing(session, Material, typed)
    if found is not None:
        return found
    material = Material(name=typed)
    session.add(material)
    session.flush()
    _made(session, "material", material)
    return material


def _resolve_grade(
    session: Session, material: Material, chosen: int | None, typed: str | None
) -> Grade:
    if chosen is not None:
        grade = get_or_404(session, Grade, chosen, "Grade")
        if grade.material_id != material.id:
            raise ValidationError("That grade belongs to a different material.")
        return grade
    if not typed:
        raise ValidationError("Tell us which grade of it you mean.")
    found = _existing(session, Grade, typed, Grade.material_id == material.id)
    if found is not None:
        return found
    grade = Grade(material_id=material.id, name=typed)
    session.add(grade)
    session.flush()
    _made(session, "grade", grade)
    return grade


def _resolve_manufacturer(session: Session, chosen: int | None, typed: str | None) -> Manufacturer:
    if chosen is not None:
        return get_or_404(session, Manufacturer, chosen, "Manufacturer")
    if not typed:
        raise ValidationError("Tell us whose material it is.")
    found = _existing(session, Manufacturer, typed)
    if found is not None:
        return found
    manufacturer = Manufacturer(name=typed)
    session.add(manufacturer)
    session.flush()
    _made(session, "manufacturer", manufacturer)
    return manufacturer


def _resolve_product(session: Session, payload: PortalEnquiryRequest) -> Product:
    """Material, then grade, then manufacturer - and the product they make.

    Each step may create what it did not find, so a party is never turned away
    because our master list is short of a grade. The product itself is the same
    story one level up: a combination nobody has traded before is simply new.
    """
    material = _resolve_material(session, payload.material_id, payload.material_text)
    grade = _resolve_grade(session, material, payload.grade_id, payload.grade_text)
    manufacturer = _resolve_manufacturer(
        session, payload.manufacturer_id, payload.manufacturer_text
    )

    product = session.scalars(
        select(Product)
        .where(
            Product.material_id == material.id,
            Product.grade_id == grade.id,
            Product.manufacturer_id == manufacturer.id,
        )
        .limit(1)
    ).first()
    if product is not None:
        return product

    product = Product(
        material_id=material.id,
        grade_id=grade.id,
        manufacturer_id=manufacturer.id,
        display_name=build_display_name(manufacturer, material, grade),
    )
    session.add(product)
    session.flush()
    audit.record(
        session,
        user_id=None,
        entity_type="product",
        entity_id=product.id,
        action=AuditAction.CREATE,
        new_value={"display_name": product.display_name, "created_from": "portal"},
    )
    return product


def _resolve_place(session: Session, typed: str | None) -> Location | None:
    """The town they named, as a location.

    They give us a place, not an address, so this matches and creates the
    plainest kind of row there is: a city on its own. A proper address for the
    same town is a different thing and is left alone.
    """
    name = (typed or "").strip()
    if not name:
        return None
    found = session.scalars(
        select(Location)
        .where(
            func.lower(Location.city) == name.lower(),
            Location.label.is_(None),
            Location.area.is_(None),
        )
        .limit(1)
    ).first()
    if found is not None:
        return found
    location = Location(city=name)
    session.add(location)
    session.flush()
    audit.record(
        session,
        user_id=None,
        entity_type="location",
        entity_id=location.id,
        action=AuditAction.CREATE,
        new_value={"city": location.city, "created_from": "portal"},
    )
    return location


# --------------------------------------------------------------------------- #
# The party's side
# --------------------------------------------------------------------------- #
def submit(session: Session, code: str, payload: PortalEnquiryRequest) -> PortalEnquiry:
    """Record what a party asked for, as an inquiry on the book."""
    party = party_by_code(session, code)
    enquiry_type = ENQUIRY_OF[party.party_type]
    quantity: Decimal = payload.quantity

    if enquiry_type is InquiryType.TRANSPORT:
        if not payload.from_place or not payload.to_place:
            raise ValidationError("Tell us where the load is picked up and where it goes.")
        pickup = _resolve_place(session, payload.from_place)
        delivery = _resolve_place(session, payload.to_place)
        assert pickup is not None and delivery is not None
        if pickup.id == delivery.id:
            raise ValidationError("The pickup and the delivery cannot be the same place.")
        product = None
        create = InquiryCreate(
            inquiry_type=InquiryType.TRANSPORT,
            transport=TransportInquiryCreate(
                transporter_id=party.id,
                quantity=quantity,
                unit=payload.unit,
                pickup_location_id=pickup.id,
                delivery_location_id=delivery.id,
                price=payload.rate,
            ),
        )
    else:
        product = _resolve_product(session, payload)
        place = _resolve_place(session, payload.to_place)
        block = {
            "product_id": product.id,
            "quantity": quantity,
            "unit": payload.unit,
            "location_id": place.id if place else None,
            "rate": payload.rate,
        }
        create = (
            InquiryCreate(
                inquiry_type=InquiryType.CUSTOMER,
                customer=CustomerInquiryCreate(customer_id=party.id, **block),
            )
            if enquiry_type is InquiryType.CUSTOMER
            else InquiryCreate(
                inquiry_type=InquiryType.SUPPLIER,
                supplier=SupplierInquiryCreate(supplier_id=party.id, **block),
            )
        )

    inquiry = inquiries.create_inquiry(session, create, None, InquirySource.PORTAL)

    enquiry = PortalEnquiry(
        party_id=party.id,
        inquiry_type=enquiry_type,
        product_id=product.id if product else None,
        quantity=quantity,
        unit=payload.unit,
        from_place=payload.from_place,
        to_place=payload.to_place,
        rate=payload.rate,
        notes=payload.notes,
        inquiry_id=inquiry.id,
    )
    session.add(enquiry)
    session.flush()
    return enquiry


def mine(session: Session, code: str, limit: int = 20) -> list[PortalEnquiry]:
    """What this party has sent in, newest first.

    Shown back to them because somebody who sends something into a form is owed
    the knowledge that it arrived.
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
    enquiry_type: InquiryType | None,
    party_id: int | None,
    product_id: int | None,
    material_id: int | None,
    grade_id: int | None,
    manufacturer_id: int | None,
    application_id: int | None,
    search: str | None,
) -> Select:
    """The log, narrowed the same way the enquiry and party lists are."""
    statement = select(PortalEnquiry)
    if enquiry_type is not None:
        statement = statement.where(PortalEnquiry.inquiry_type == enquiry_type)
    if party_id is not None:
        statement = statement.where(PortalEnquiry.party_id == party_id)
    if product_id is not None:
        statement = statement.where(PortalEnquiry.product_id == product_id)

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
    enquiry_type: InquiryType | None = None,
    party_id: int | None = None,
    product_id: int | None = None,
    material_id: int | None = None,
    grade_id: int | None = None,
    manufacturer_id: int | None = None,
    application_id: int | None = None,
    search: str | None = None,
):
    """What has come in, newest first, a page at a time."""
    statement = _filtered(
        enquiry_type=enquiry_type,
        party_id=party_id,
        product_id=product_id,
        material_id=material_id,
        grade_id=grade_id,
        manufacturer_id=manufacturer_id,
        application_id=application_id,
        search=search,
    ).order_by(PortalEnquiry.created_at.desc())
    return paginate(session, statement, params)


def get_enquiry(session: Session, enquiry_id: int) -> PortalEnquiry:
    return get_or_404(session, PortalEnquiry, enquiry_id, "Enquiry")


def for_inquiry(session: Session, inquiry_id: int) -> PortalEnquiry | None:
    """What the party actually typed, for an inquiry that came from one."""
    return session.scalars(
        select(PortalEnquiry).where(PortalEnquiry.inquiry_id == inquiry_id).limit(1)
    ).first()


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
    "Inquiry",
    "for_inquiry",
    "get_enquiry",
    "link_for",
    "list_for_desk",
    "mine",
    "search_grades",
    "search_manufacturers",
    "search_materials",
    "submit",
]
