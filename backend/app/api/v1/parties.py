"""Party endpoints: customers, suppliers, transporters, their links and the 360 view."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import AdminUser, SessionDep, StaffUser
from app.core.pagination import Page, PageParams, page_params
from app.models.enums import PartyStage, PartyType, RecordStatus
from app.schemas.common import Message
from app.schemas.dashboard import Party360Out
from app.schemas.party import (
    DuplicateCheckResult,
    PartyApplicationCreate,
    PartyApplicationOut,
    PartyApplicationUpdate,
    PartyBookSummary,
    PartyCreate,
    PartyDetailOut,
    PartyListItem,
    PartyLocationCreate,
    PartyLocationOut,
    PartyLocationUpdate,
    PartyMergeRequest,
    PartyMergeResult,
    PartyMoveRequest,
    PartyMoveResponse,
    PartyProductCreate,
    PartyProductOut,
    PartyProductUpdate,
    PartyProspectCreate,
    PartyUpdate,
)
from app.services import dashboard as dashboard_service
from app.services import parties as service

router = APIRouter(prefix="/parties", tags=["parties"])


@router.post("/{party_id}/move", response_model=PartyMoveResponse)
def move_party(
    party_id: int,
    payload: PartyMoveRequest,
    session: SessionDep,
    user: StaffUser,
) -> PartyMoveResponse:
    """Move a party into another book, keeping its history, notes and products."""
    party, moved = service.move_party(session, party_id, payload.party_type, user.id)
    return PartyMoveResponse(party=party, products_repointed=moved["products"])


@router.get("/summary", response_model=PartyBookSummary)
def party_book_summary(
    session: SessionDep,
    _: StaffUser,
    party_type: PartyType = Query(..., description="Which book to summarise"),
) -> PartyBookSummary:
    """Totals across the whole book, so the cards do not count only one page."""
    return PartyBookSummary(**service.book_summary(session, party_type))


@router.get("", response_model=Page[PartyListItem])
def list_parties(
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, description="Name, phone, email, GST or contact person"),
    party_type: PartyType | None = None,
    status: RecordStatus | None = None,
    stage: PartyStage | None = Query(
        None, description="PROSPECT for leads met on the phone, ACTIVE for verified parties"
    ),
    include_merged: bool = Query(False, description="Include rows folded into another party"),
    stale_days: int | None = Query(
        None,
        ge=1,
        description="Prospects older than N days with no inquiry and no activity (cleanup list)",
    ),
    city: str | None = None,
    area: str | None = Query(None, description="Locality, e.g. Odhav or Aslali"),
    location_id: int | None = None,
    product_id: int | None = Query(None, description="Parties linked to this product"),
    material_id: int | None = Query(None, description="Through the products they deal in"),
    grade_id: int | None = None,
    manufacturer_id: int | None = Query(None, description="Brand they deal in"),
    application_id: int | None = Query(
        None, description="End use: declared on the party, or implied by their products"
    ),
    sort_by: str | None = Query(None, pattern="^(name|created_at|updated_at|id)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
) -> Page[PartyListItem]:
    rows, total, extras = service.list_parties(
        session,
        params,
        q=q,
        party_type=party_type,
        status=status,
        stage=stage,
        include_merged=include_merged,
        stale_days=stale_days,
        city=city,
        area=area,
        location_id=location_id,
        product_id=product_id,
        material_id=material_id,
        grade_id=grade_id,
        manufacturer_id=manufacturer_id,
        application_id=application_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    items = []
    for row in rows:
        item = PartyListItem.model_validate(row)
        item.open_inquiry_count = extras["open_inquiry_count"].get(row.id, 0)
        item.product_count = extras["product_count"].get(row.id, 0)
        item.primary_city = extras["primary_city"].get(row.id)
        items.append(item)
    return Page.build(items, total, params)


@router.get("/duplicates", response_model=DuplicateCheckResult)
def check_duplicates(
    session: SessionDep,
    _: StaffUser,
    party_type: PartyType | None = None,
    name: str | None = None,
    phone: str | None = None,
    gst_number: str | None = None,
    exclude_id: int | None = None,
) -> DuplicateCheckResult:
    """Parties that look like the one about to be created.

    Ranked exact GST, exact phone, then similar name. A warning for the UI, never
    a block - the trader may genuinely have two parties with the same name.
    """
    return service.find_duplicates(
        session,
        party_type=party_type,
        name=name,
        phone=phone,
        gst_number=gst_number,
        exclude_id=exclude_id,
    )


@router.post("/prospects", response_model=PartyDetailOut, status_code=201)
def create_prospect(
    payload: PartyProspectCreate, session: SessionDep, user: StaffUser
) -> PartyDetailOut:
    """Save an unknown customer, supplier or transporter from a name and phone.

    The party lands as a PROSPECT in Master Data and is returned so the calling
    form can select it immediately.
    """
    return PartyDetailOut.model_validate(service.create_prospect(session, payload, user.id))


@router.post("", response_model=PartyDetailOut, status_code=201)
def create_party(payload: PartyCreate, session: SessionDep, user: StaffUser) -> PartyDetailOut:
    return PartyDetailOut.model_validate(service.create_party(session, payload, user.id))


@router.get("/{party_id}", response_model=PartyDetailOut)
def get_party(party_id: int, session: SessionDep, _: StaffUser) -> PartyDetailOut:
    return PartyDetailOut.model_validate(service.get_party(session, party_id))


@router.patch("/{party_id}", response_model=PartyDetailOut)
def update_party(
    party_id: int, payload: PartyUpdate, session: SessionDep, user: StaffUser
) -> PartyDetailOut:
    return PartyDetailOut.model_validate(service.update_party(session, party_id, payload, user.id))


@router.post("/{party_id}/promote", response_model=PartyDetailOut)
def promote_party(party_id: int, session: SessionDep, user: StaffUser) -> PartyDetailOut:
    """PROSPECT -> ACTIVE once the relationship is real."""
    service.promote_party(session, party_id, user.id)
    return PartyDetailOut.model_validate(service.get_party(session, party_id))


@router.post("/{party_id}/merge", response_model=PartyMergeResult)
def merge_party(
    party_id: int, payload: PartyMergeRequest, session: SessionDep, admin: AdminUser
) -> PartyMergeResult:
    """Fold a duplicate into this party, keeping every inquiry, activity and note."""
    moved = service.merge_parties(session, party_id, payload.loser_id, admin.id, payload.note)
    return PartyMergeResult(
        survivor_id=party_id,
        merged_party_id=payload.loser_id,
        moved=moved,
        message=f"Party #{payload.loser_id} merged into #{party_id}.",
    )


@router.get("/{party_id}/overview", response_model=Party360Out)
def party_overview(party_id: int, session: SessionDep, _: StaffUser) -> Party360Out:
    """Everything about one party on a single screen (the 360-degree view)."""
    return dashboard_service.party_360(session, party_id)


# --- locations --------------------------------------------------------------
@router.get("/{party_id}/locations", response_model=list[PartyLocationOut])
def list_party_locations(
    party_id: int, session: SessionDep, _: StaffUser
) -> list[PartyLocationOut]:
    party = service.get_party(session, party_id)
    return [PartyLocationOut.model_validate(link) for link in party.locations]


@router.post("/{party_id}/locations", response_model=PartyLocationOut, status_code=201)
def add_party_location(
    party_id: int, payload: PartyLocationCreate, session: SessionDep, user: StaffUser
) -> PartyLocationOut:
    return PartyLocationOut.model_validate(
        service.add_party_location(session, party_id, payload, user.id)
    )


@router.patch("/{party_id}/locations/{link_id}", response_model=PartyLocationOut)
def update_party_location(
    party_id: int,
    link_id: int,
    payload: PartyLocationUpdate,
    session: SessionDep,
    user: StaffUser,
) -> PartyLocationOut:
    return PartyLocationOut.model_validate(
        service.update_party_location(session, party_id, link_id, payload, user.id)
    )


@router.delete("/{party_id}/locations/{link_id}", response_model=Message)
def remove_party_location(
    party_id: int, link_id: int, session: SessionDep, user: StaffUser
) -> Message:
    service.remove_party_location(session, party_id, link_id, user.id)
    return Message(message="Location unlinked from party.")


# --- products ---------------------------------------------------------------
@router.get("/{party_id}/products", response_model=list[PartyProductOut])
def list_party_products(party_id: int, session: SessionDep, _: StaffUser) -> list[PartyProductOut]:
    party = service.get_party(session, party_id)
    return [PartyProductOut.model_validate(link) for link in party.products]


@router.post("/{party_id}/products", response_model=PartyProductOut, status_code=201)
def add_party_product(
    party_id: int, payload: PartyProductCreate, session: SessionDep, user: StaffUser
) -> PartyProductOut:
    return PartyProductOut.model_validate(
        service.add_party_product(session, party_id, payload, user.id)
    )


@router.patch("/{party_id}/products/{link_id}", response_model=PartyProductOut)
def update_party_product(
    party_id: int,
    link_id: int,
    payload: PartyProductUpdate,
    session: SessionDep,
    user: StaffUser,
) -> PartyProductOut:
    return PartyProductOut.model_validate(
        service.update_party_product(session, party_id, link_id, payload, user.id)
    )


@router.delete("/{party_id}/products/{link_id}", response_model=Message)
def remove_party_product(
    party_id: int, link_id: int, session: SessionDep, user: StaffUser
) -> Message:
    service.remove_party_product(session, party_id, link_id, user.id)
    return Message(message="Product unlinked from party.")


# --- applications -----------------------------------------------------------
@router.get("/{party_id}/applications", response_model=list[PartyApplicationOut])
def list_party_applications(
    party_id: int, session: SessionDep, _: StaffUser
) -> list[PartyApplicationOut]:
    party = service.get_party(session, party_id)
    return [PartyApplicationOut.model_validate(link) for link in party.applications]


@router.post("/{party_id}/applications", response_model=PartyApplicationOut, status_code=201)
def add_party_application(
    party_id: int, payload: PartyApplicationCreate, session: SessionDep, user: StaffUser
) -> PartyApplicationOut:
    """Record the end-use a party works in, independent of what they have traded."""
    return PartyApplicationOut.model_validate(
        service.add_party_application(session, party_id, payload, user.id)
    )


@router.patch("/{party_id}/applications/{link_id}", response_model=PartyApplicationOut)
def update_party_application(
    party_id: int,
    link_id: int,
    payload: PartyApplicationUpdate,
    session: SessionDep,
    user: StaffUser,
) -> PartyApplicationOut:
    return PartyApplicationOut.model_validate(
        service.update_party_application(session, party_id, link_id, payload, user.id)
    )


@router.delete("/{party_id}/applications/{link_id}", response_model=Message)
def remove_party_application(
    party_id: int, link_id: int, session: SessionDep, user: StaffUser
) -> Message:
    service.remove_party_application(session, party_id, link_id, user.id)
    return Message(message="Application unlinked from party.")
