"""The desk's inbox for enquiries parties raised themselves.

What arrives through a portal link is a request in somebody else's words. These
endpoints are where the desk reads one, and either accepts it - which creates a
real inquiry, owned and audited like any other - or declines it. Nothing here
edits what the party wrote: their words are the record of what they asked for.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.core.config import settings
from app.core.deps import SessionDep, StaffUser
from app.core.pagination import Page, PageParams, page_params
from app.models.enums import InquiryType, PortalEnquiryStatus
from app.schemas.portal_enquiry import (
    DeskEnquiryCounts,
    DeskEnquiryOut,
    EnquiryAcceptRequest,
    EnquiryLink,
)
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
    status: PortalEnquiryStatus | None = None,
    inquiry_type: InquiryType | None = None,
    party_id: int | None = None,
    product_id: int | None = None,
    material_id: int | None = Query(None, description="Product's material"),
    grade_id: int | None = Query(None, description="Product's grade"),
    manufacturer_id: int | None = Query(None, description="Product's manufacturer (brand)"),
    application_id: int | None = Query(None, description="Product is used for this application"),
) -> Page[DeskEnquiryOut]:
    """Waiting ones first, then newest. A hundred of them page like anything else."""
    items, total = service.list_for_desk(
        session,
        params,
        status=status,
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


@router.get("/counts", response_model=DeskEnquiryCounts)
def enquiry_counts(session: SessionDep, _: StaffUser) -> DeskEnquiryCounts:
    """For the badge: how many are waiting to be read."""
    return DeskEnquiryCounts(**service.counts(session))


@router.get("/link/{party_id}", response_model=EnquiryLink)
def enquiry_link(request: Request, session: SessionDep, _: StaffUser, party_id: int) -> EnquiryLink:
    """The link this party uses to raise enquiries. Issues their code if needed."""
    return EnquiryLink(**service.link_for(session, party_id, _public_base(request)))


@router.get("/{enquiry_id}", response_model=DeskEnquiryOut)
def get_enquiry(session: SessionDep, _: StaffUser, enquiry_id: int) -> DeskEnquiryOut:
    return DeskEnquiryOut.model_validate(service.get_enquiry(session, enquiry_id))


@router.post("/{enquiry_id}/accept", response_model=DeskEnquiryOut)
def accept_enquiry(
    session: SessionDep,
    user: StaffUser,
    enquiry_id: int,
    payload: EnquiryAcceptRequest,
) -> DeskEnquiryOut:
    """Create the inquiry this enquiry asked for, and record where it went."""
    return DeskEnquiryOut.model_validate(service.accept(session, enquiry_id, payload, user.id))


@router.post("/{enquiry_id}/decline", response_model=DeskEnquiryOut)
def decline_enquiry(session: SessionDep, user: StaffUser, enquiry_id: int) -> DeskEnquiryOut:
    """Read, not taken up. What they wrote stays on the record."""
    return DeskEnquiryOut.model_validate(service.decline(session, enquiry_id, user.id))
