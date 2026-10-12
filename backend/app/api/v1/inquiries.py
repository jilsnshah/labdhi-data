"""Inquiry endpoints: list, create, detail, edit.

An inquiry is a recorded quotation. Status is ACTIVE or CLOSED and is changed
with the same PATCH as any other field.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.deps import SessionDep, StaffUser
from app.core.pagination import Page, PageParams, page_params
from app.models.enums import InquiryStatus, InquiryType
from app.schemas.inquiry import (
    InquiryCreate,
    InquiryDetailOut,
    InquiryListItem,
    InquiryUpdate,
)
from app.services import inquiries as service
from app.services import inquiry_queries as queries

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


@router.get("", response_model=Page[InquiryListItem])
def list_inquiries(
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, description="Inquiry id, party name or product name"),
    inquiry_type: InquiryType | None = None,
    status: InquiryStatus | None = None,
    party_id: int | None = None,
    product_id: int | None = None,
    location_id: int | None = Query(None, description="Matches any location on the inquiry"),
    area: str | None = Query(
        None, description="Any location on the inquiry is in this area (case-insensitive)"
    ),
    material_id: int | None = Query(None, description="Product's material"),
    grade_id: int | None = Query(None, description="Product's grade"),
    manufacturer_id: int | None = Query(None, description="Product's manufacturer (brand)"),
    application_id: int | None = Query(None, description="Product is used for this application"),
    created_from: date | None = None,
    created_to: date | None = None,
    sort_by: str | None = Query(None, pattern="^(id|created_at|updated_at|status|closed_at)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
) -> Page[InquiryListItem]:
    items, total = queries.list_inquiries(
        session,
        params,
        inquiry_type=inquiry_type,
        status=status,
        party_id=party_id,
        product_id=product_id,
        location_id=location_id,
        area=area,
        material_id=material_id,
        grade_id=grade_id,
        manufacturer_id=manufacturer_id,
        application_id=application_id,
        created_from=created_from,
        created_to=created_to,
        q=q,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return Page.build(items, total, params)


@router.post("", response_model=InquiryDetailOut, status_code=201)
def create_inquiry(
    payload: InquiryCreate, session: SessionDep, user: StaffUser
) -> InquiryDetailOut:
    """Record a quotation in one step - no request / response workflow."""
    return InquiryDetailOut.model_validate(service.create_inquiry(session, payload, user.id))


@router.get("/{inquiry_id}", response_model=InquiryDetailOut)
def get_inquiry(inquiry_id: int, session: SessionDep, _: StaffUser) -> InquiryDetailOut:
    return InquiryDetailOut.model_validate(service.get_inquiry(session, inquiry_id))


@router.patch("/{inquiry_id}", response_model=InquiryDetailOut)
def update_inquiry(
    inquiry_id: int, payload: InquiryUpdate, session: SessionDep, user: StaffUser
) -> InquiryDetailOut:
    """Edit any field, including ``status`` (ACTIVE <-> CLOSED)."""
    return InquiryDetailOut.model_validate(
        service.update_inquiry(session, inquiry_id, payload, user.id)
    )
