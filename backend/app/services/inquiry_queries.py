"""Read-side queries for inquiries: list rows and per-party lists."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.pagination import PageParams, paginate
from app.models.enums import InquiryStatus, InquiryType
from app.models.inquiry import (
    CustomerInquiry,
    Inquiry,
    SupplierInquiry,
    TransportInquiry,
)
from app.models.masters import Product, product_applications
from app.models.party import Location, Party
from app.schemas.inquiry import InquiryListItem
from app.services.inquiries import DETAIL_LOADERS

SORTABLE = {"id", "created_at", "updated_at", "status", "closed_at"}


def _place(location: Location | None) -> str | None:
    if location is None:
        return None
    parts = [location.label, location.area, location.city]
    # A label that just repeats the city adds nothing.
    if location.label == location.city:
        parts[0] = None
    seen: list[str] = []
    for part in parts:
        if part and part not in seen:
            seen.append(part)
    return ", ".join(seen)


def to_list_item(inquiry: Inquiry) -> InquiryListItem:
    item = {
        "id": inquiry.id,
        "inquiry_type": inquiry.inquiry_type,
        "status": inquiry.status,
        "title": inquiry.title,
        "created_by": inquiry.created_by,
        "created_by_name": inquiry.creator.name if inquiry.creator else None,
        "created_at": inquiry.created_at,
        "updated_at": inquiry.updated_at,
        "closed_at": inquiry.closed_at,
    }
    if inquiry.customer_detail is not None or inquiry.supplier_detail is not None:
        detail = inquiry.customer_detail or inquiry.supplier_detail
        party = detail.customer if inquiry.customer_detail is not None else detail.supplier
        item.update(
            party_id=party.id,
            party_name=party.name,
            party_stage=party.stage.value,
            product_id=detail.product_id,
            product_name=detail.product.display_name,
            quantity=detail.quantity,
            unit=detail.unit,
            location_name=_place(detail.location),
            location_area=detail.location.area if detail.location else None,
            location_city=detail.location.city if detail.location else None,
            rate=detail.rate,
        )
    elif inquiry.transport_detail is not None:
        detail = inquiry.transport_detail
        item.update(
            party_id=detail.transporter_id,
            party_name=detail.transporter.name,
            party_stage=detail.transporter.stage.value,
            quantity=detail.quantity,
            unit=detail.unit,
            pickup_name=_place(detail.pickup_location),
            delivery_name=_place(detail.delivery_location),
            price=detail.price,
        )
    return InquiryListItem(**item)


def build_list_items(session: Session, inquiries: Sequence[Inquiry]) -> list[InquiryListItem]:
    return [to_list_item(inquiry) for inquiry in inquiries]


def _apply_filters(
    stmt: Select,
    *,
    inquiry_type: InquiryType | None,
    status: InquiryStatus | None,
    party_id: int | None,
    product_id: int | None,
    location_id: int | None,
    area: str | None,
    created_from: date | None,
    created_to: date | None,
    q: str | None,
    material_id: int | None = None,
    grade_id: int | None = None,
    manufacturer_id: int | None = None,
    application_id: int | None = None,
) -> Select:
    customer = aliased(CustomerInquiry)
    supplier = aliased(SupplierInquiry)
    transport = aliased(TransportInquiry)
    stmt = (
        stmt.outerjoin(customer, customer.inquiry_id == Inquiry.id)
        .outerjoin(supplier, supplier.inquiry_id == Inquiry.id)
        .outerjoin(transport, transport.inquiry_id == Inquiry.id)
    )

    if inquiry_type:
        stmt = stmt.where(Inquiry.inquiry_type == inquiry_type)
    if status:
        stmt = stmt.where(Inquiry.status == status)
    if party_id is not None:
        stmt = stmt.where(
            or_(
                customer.customer_id == party_id,
                supplier.supplier_id == party_id,
                transport.transporter_id == party_id,
            )
        )
    if product_id is not None:
        stmt = stmt.where(or_(customer.product_id == product_id, supplier.product_id == product_id))
    if any(v is not None for v in (material_id, grade_id, manufacturer_id, application_id)):
        # Narrow through the product: transport inquiries carry none, so they drop out.
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
        stmt = stmt.where(or_(customer.product_id.in_(products), supplier.product_id.in_(products)))
    if location_id is not None:
        stmt = stmt.where(
            or_(
                customer.location_id == location_id,
                supplier.location_id == location_id,
                transport.pickup_location_id == location_id,
                transport.delivery_location_id == location_id,
            )
        )
    if area:
        # Any location on the inquiry in that area: its own location, or either
        # end of a transport route.
        in_area = select(Location.id).where(func.lower(Location.area) == area.strip().lower())
        stmt = stmt.where(
            or_(
                customer.location_id.in_(in_area),
                supplier.location_id.in_(in_area),
                transport.pickup_location_id.in_(in_area),
                transport.delivery_location_id.in_(in_area),
            )
        )
    if created_from:
        stmt = stmt.where(func.date(Inquiry.created_at) >= created_from)
    if created_to:
        stmt = stmt.where(func.date(Inquiry.created_at) <= created_to)
    if q:
        like = f"%{q}%"
        customer_party = aliased(Party)
        supplier_party = aliased(Party)
        transport_party = aliased(Party)
        customer_product = aliased(Product)
        supplier_product = aliased(Product)
        stmt = (
            stmt.outerjoin(customer_party, customer_party.id == customer.customer_id)
            .outerjoin(supplier_party, supplier_party.id == supplier.supplier_id)
            .outerjoin(transport_party, transport_party.id == transport.transporter_id)
            .outerjoin(customer_product, customer_product.id == customer.product_id)
            .outerjoin(supplier_product, supplier_product.id == supplier.product_id)
        )
        conditions = [
            Inquiry.title.ilike(like),
            customer_party.name.ilike(like),
            supplier_party.name.ilike(like),
            transport_party.name.ilike(like),
            customer_product.display_name.ilike(like),
            supplier_product.display_name.ilike(like),
        ]
        if q.strip().lstrip("#").isdigit():
            conditions.append(Inquiry.id == int(q.strip().lstrip("#")))
        stmt = stmt.where(or_(*conditions))
    return stmt


def list_inquiries(
    session: Session,
    params: PageParams,
    *,
    inquiry_type: InquiryType | None = None,
    status: InquiryStatus | None = None,
    party_id: int | None = None,
    product_id: int | None = None,
    location_id: int | None = None,
    area: str | None = None,
    material_id: int | None = None,
    grade_id: int | None = None,
    manufacturer_id: int | None = None,
    application_id: int | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    q: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> tuple[list[InquiryListItem], int]:
    stmt = select(Inquiry).options(*DETAIL_LOADERS)
    stmt = _apply_filters(
        stmt,
        inquiry_type=inquiry_type,
        status=status,
        party_id=party_id,
        product_id=product_id,
        location_id=location_id,
        area=area,
        created_from=created_from,
        created_to=created_to,
        q=q,
        material_id=material_id,
        grade_id=grade_id,
        manufacturer_id=manufacturer_id,
        application_id=application_id,
    )
    column = getattr(Inquiry, sort_by if sort_by in SORTABLE else "created_at")
    stmt = stmt.order_by(column.desc() if sort_dir.lower() == "desc" else column.asc())
    rows, total = paginate(session, stmt, params)
    return build_list_items(session, rows), total


def inquiries_for_party(
    session: Session, party_id: int, *, status: InquiryStatus, limit: int = 50
) -> list[InquiryListItem]:
    stmt = select(Inquiry).options(*DETAIL_LOADERS)
    stmt = _apply_filters(
        stmt,
        inquiry_type=None,
        status=status,
        party_id=party_id,
        product_id=None,
        location_id=None,
        area=None,
        created_from=None,
        created_to=None,
        q=None,
    )
    stmt = stmt.order_by(Inquiry.created_at.desc()).limit(limit)
    rows = session.execute(stmt).scalars().all()
    return build_list_items(session, rows)
