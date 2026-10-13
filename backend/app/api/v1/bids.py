"""Bid endpoints for the desk: raise a bid, run it, settle it."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from app.core.deps import SessionDep, StaffUser
from app.core.pagination import Page, PageParams, page_params
from app.models.enums import BidStatus, BidType
from app.schemas.bid import (
    BidAwardRequest,
    BidCreate,
    BidDetailOut,
    BidEvent,
    BidListItem,
    BidOut,
    BidParticipantOut,
    BidParticipantsRequest,
    BidQuoteOut,
    BidUpdate,
)
from app.schemas.common import Message
from app.services import bids as service

router = APIRouter(prefix="/bids", tags=["bids"])


def _public_base(request: Request) -> str:
    """Where the participants' portal lives.

    The links are handed to people outside the company, so they point at the
    web app the admin is using, not at the API.
    """
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("referer")
    if referer:
        parts = referer.split("/")
        if len(parts) >= 3:
            return "/".join(parts[:3])
    return str(request.base_url).rstrip("/")


def _detail(session, bid, base_url: str) -> BidDetailOut:
    links = service.participant_links(session, bid, base_url)
    quotes = service.quotes_of(bid)
    winner_id = bid.winner_quote_id

    quote_out = [
        BidQuoteOut(
            id=quote.id,
            participant_id=quote.participant_id,
            price=quote.price,
            quantity=quote.quantity,
            notes=quote.notes,
            submitted_at=quote.submitted_at,
            revision=quote.revision,
            party=quote.participant.party,
            is_winner=quote.id == winner_id,
        )
        for quote in quotes
    ]
    by_participant = {quote.participant_id: quote for quote in quote_out}

    participants = [
        BidParticipantOut(
            id=participant.id,
            party=participant.party,
            first_opened_at=participant.first_opened_at,
            last_opened_at=participant.last_opened_at,
            quote=by_participant.get(participant.id),
            bid_link=links[participant.id][0],
            portal_link=links[participant.id][1],
        )
        for participant in sorted(bid.participants, key=lambda p: p.party.name.lower())
    ]

    # Built explicitly: the participant rows carry links that exist only here,
    # so the ORM object cannot be validated straight into the detail shape.
    base = BidOut.model_validate(bid).model_dump()
    base["title"] = service.describe(bid)
    return BidDetailOut(
        **base,
        participants=participants,
        quotes=quote_out,
        winner=by_participant.get(bid.winner_quote.participant_id if bid.winner_quote else -1),
        best_price=service.best_price(bid),
    )


@router.get("", response_model=Page[BidListItem])
def list_bids(
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    bid_type: BidType | None = None,
    status: BidStatus | None = None,
    product_id: int | None = None,
    party_id: int | None = Query(None, description="Bids a given party was invited to"),
    material_id: int | None = Query(None, description="Through the bid's product"),
    grade_id: int | None = None,
    manufacturer_id: int | None = None,
    application_id: int | None = Query(None, description="End use the product serves"),
    area: str | None = Query(None, description="Either end of a transport route"),
    created_from: date | None = None,
    created_to: date | None = None,
    q: str | None = Query(None, description="Bid id, title, product or participant name"),
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> Page[BidListItem]:
    rows, total = service.list_bids(
        session,
        params,
        bid_type=bid_type,
        status=status,
        product_id=product_id,
        party_id=party_id,
        material_id=material_id,
        grade_id=grade_id,
        manufacturer_id=manufacturer_id,
        application_id=application_id,
        area=area,
        created_from=created_from,
        created_to=created_to,
        q=q,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return Page.build(rows, total, params)


@router.post("", response_model=BidDetailOut, status_code=201)
def create_bid(
    payload: BidCreate, session: SessionDep, user: StaffUser, request: Request
) -> BidDetailOut:
    bid = service.create_bid(session, payload, user.id)
    return _detail(session, bid, _public_base(request))


@router.get("/{bid_id}", response_model=BidDetailOut)
def get_bid(bid_id: int, session: SessionDep, _: StaffUser, request: Request) -> BidDetailOut:
    return _detail(session, service.get_bid(session, bid_id), _public_base(request))


@router.patch("/{bid_id}", response_model=BidDetailOut)
def update_bid(
    bid_id: int, payload: BidUpdate, session: SessionDep, user: StaffUser, request: Request
) -> BidDetailOut:
    bid = service.update_bid(session, bid_id, payload, user.id)
    return _detail(session, bid, _public_base(request))


@router.post("/{bid_id}/participants", response_model=BidDetailOut)
def add_participants(
    bid_id: int,
    payload: BidParticipantsRequest,
    session: SessionDep,
    user: StaffUser,
    request: Request,
) -> BidDetailOut:
    bid = service.add_participants(session, bid_id, payload.party_ids, user.id)
    return _detail(session, bid, _public_base(request))


@router.delete("/{bid_id}/participants/{participant_id}", response_model=BidDetailOut)
def remove_participant(
    bid_id: int, participant_id: int, session: SessionDep, user: StaffUser, request: Request
) -> BidDetailOut:
    bid = service.remove_participant(session, bid_id, participant_id, user.id)
    return _detail(session, bid, _public_base(request))


@router.post("/{bid_id}/publish", response_model=BidDetailOut)
def publish_bid(
    bid_id: int, session: SessionDep, user: StaffUser, request: Request
) -> BidDetailOut:
    bid = service.publish(session, bid_id, user.id)
    return _detail(session, bid, _public_base(request))


@router.post("/{bid_id}/close", response_model=BidDetailOut)
def close_bid(
    bid_id: int,
    session: SessionDep,
    user: StaffUser,
    request: Request,
    without_winner: bool = Query(False, description="Close and record that nobody was chosen"),
) -> BidDetailOut:
    bid = service.close(session, bid_id, user.id, without_winner=without_winner)
    return _detail(session, bid, _public_base(request))


@router.post("/{bid_id}/award", response_model=BidDetailOut)
def award_bid(
    bid_id: int,
    payload: BidAwardRequest,
    session: SessionDep,
    user: StaffUser,
    request: Request,
) -> BidDetailOut:
    bid = service.award(session, bid_id, payload, user.id)
    return _detail(session, bid, _public_base(request))


@router.get("/{bid_id}/history", response_model=list[BidEvent])
def bid_history(bid_id: int, session: SessionDep, _: StaffUser) -> list[BidEvent]:
    service.get_bid(session, bid_id)  # 404 for an unknown bid
    return service.history(session, bid_id)


@router.get("/{bid_id}/links", response_model=Message)
def bid_links_hint(bid_id: int, session: SessionDep, _: StaffUser) -> Message:
    """Kept for the future messaging integration: the links live on the detail."""
    bid = service.get_bid(session, bid_id)
    return Message(message=f"Bid #{bid.id} has {len(bid.participants)} participant links.")
