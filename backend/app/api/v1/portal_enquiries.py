"""The log of enquiries parties raised themselves.

Each one is already an inquiry: a party sends it in and it is on the book, so
there is nothing to approve here. What this screen shows is where an inquiry
came from and what was actually said - their note, and the places in their own
words rather than the location rows we matched them to. Read-only, because
their words are the record of what they asked for.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.core.config import settings
from app.core.deps import SessionDep, StaffUser
from app.core.pagination import Page, PageParams, page_params
from app.models.enums import InquiryType
from app.schemas.portal_enquiry import DeskEnquiryOut, EnquiryLink
from app.services import portal_enquiries as service

router = APIRouter(prefix="/portal-enquiries", tags=["portal enquiries"])


def _public_base(request: Request) -> str:
    """Where a party reaches the portal - see the same helper on bids."""
    if settings.portal_base_url:
        return settings.portal_base_url.rstrip("/")
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("referer")
    if referer:
        parts = referer.split("/")
        if len(parts) >= 3:
            return "/".join(parts[:3])
    return str(request.base_url).rstrip("/")


@router.get("", response_model=Page[DeskEnquiryOut])
def list_enquiries(
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, description="Party, product, place or anything they typed"),
    inquiry_type: InquiryType | None = None,
    party_id: int | None = None,
    product_id: int | None = None,
    material_id: int | None = Query(None, description="Product's material"),
    grade_id: int | None = Query(None, description="Product's grade"),
    manufacturer_id: int | None = Query(None, description="Product's manufacturer (brand)"),
    application_id: int | None = Query(None, description="Product is used for this application"),
) -> Page[DeskEnquiryOut]:
    """Newest first. A hundred of them page like anything else."""
    items, total = service.list_for_desk(
        session,
        params,
        enquiry_type=inquiry_type,
        party_id=party_id,
        product_id=product_id,
        material_id=material_id,
        grade_id=grade_id,
        manufacturer_id=manufacturer_id,
        application_id=application_id,
        search=q,
    )
    return Page.build([DeskEnquiryOut.model_validate(row) for row in items], total, params)


@router.get("/link/{party_id}", response_model=EnquiryLink)
def enquiry_link(request: Request, session: SessionDep, _: StaffUser, party_id: int) -> EnquiryLink:
    """The link this party uses to raise enquiries. Issues their code if needed."""
    return EnquiryLink(**service.link_for(session, party_id, _public_base(request)))


@router.get("/{enquiry_id}", response_model=DeskEnquiryOut)
def get_enquiry(session: SessionDep, _: StaffUser, enquiry_id: int) -> DeskEnquiryOut:
    return DeskEnquiryOut.model_validate(service.get_enquiry(session, enquiry_id))
