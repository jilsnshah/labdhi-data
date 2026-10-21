"""Bid endpoints for the desk: raise a bid, run it, settle it."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from app.core.config import settings
from app.core.deps import SessionDep, StaffUser
from app.core.pagination import Page, PageParams, page_params
from app.models.enums import BidStatus, BidType
from app.schemas.bid import (
    BidAwardRequest,
    BidCreate,
    BidDetailOut,
    BidEvent,
    BidListItem,
    BidNotifyResult,
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


def _quote_out(quote, winner_id: int | None) -> BidQuoteOut:
    return BidQuoteOut(
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


def _detail(session, bid, base_url: str) -> BidDetailOut:
    counts = service.counts_for(session, bid.id)
    base = BidOut.model_validate(bid).model_dump()
    base["title"] = service.describe(bid)
    return BidDetailOut(
        **base,
        participant_count=counts[0],
        quote_count=counts[1],
        winner=_quote_out(bid.winner_quote, bid.winner_quote_id) if bid.winner_quote else None,
        best_price=service.best_price_of(session, bid),
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
    base_url = _public_base(request)
    before = {participant.id for participant in service.get_bid(session, bid_id).participants}
    bid = service.add_participants(session, bid_id, payload.party_ids, user.id)
    # A bid already running: tell the newcomers, and only them.
    added = [p.id for p in bid.participants if p.id not in before]
    if added:
        service.notify(session, bid.id, base_url, participant_ids=added)
    return _detail(session, service.get_bid(session, bid.id), base_url)


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
    """Open the bid, then WhatsApp every participant their own link."""
    base_url = _public_base(request)
    bid = service.publish(session, bid_id, user.id)
    service.notify(session, bid.id, base_url)
    return _detail(session, service.get_bid(session, bid.id), base_url)


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


@router.get("/{bid_id}/quotes", response_model=Page[BidQuoteOut])
def list_quotes(
    bid_id: int,
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, description="Participant name"),
    sort_by: str | None = Query(None, pattern="^(price|submitted_at|revision)$"),
    sort_dir: str | None = Query(None, pattern="^(asc|desc)$"),
) -> Page[BidQuoteOut]:
    """The offers on this bid, best first unless asked otherwise."""
    bid = service.get_bid(session, bid_id)
    rows, total = service.list_quotes(
        session, bid_id, params, q=q, sort_by=sort_by, sort_dir=sort_dir
    )
    return Page.build([_quote_out(row, bid.winner_quote_id) for row in rows], total, params)


@router.get("/{bid_id}/participants", response_model=Page[BidParticipantOut])
def list_participants(
    bid_id: int,
    session: SessionDep,
    _: StaffUser,
    request: Request,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, description="Participant name"),
    quoted: bool | None = Query(None, description="Only those who have, or have not, quoted"),
    opened: bool | None = Query(None, description="Only those who have, or have not, opened it"),
    sort_by: str | None = Query(None, pattern="^(name|created_at|last_opened_at)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
) -> Page[BidParticipantOut]:
    """Everyone invited, with their link and whether they have answered."""
    bid = service.get_bid(session, bid_id)
    rows, total = service.list_participants(
        session,
        bid_id,
        params,
        q=q,
        quoted=quoted,
        opened=opened,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    base_url = _public_base(request)
    out = []
    for participant in rows:
        code = service.portal_code(session, participant.party)
        out.append(
            BidParticipantOut(
                id=participant.id,
                party=participant.party,
                first_opened_at=participant.first_opened_at,
                last_opened_at=participant.last_opened_at,
                notify_status=participant.notify_status,
                notify_error=participant.notify_error,
                notified_at=participant.notified_at,
                quote=(
                    _quote_out(participant.quote, bid.winner_quote_id)
                    if participant.quote
                    else None
                ),
                bid_link=f"{base_url}/portal/{code}/{bid.id}",
                portal_link=f"{base_url}/portal/{code}",
            )
        )
    return Page.build(out, total, params)


@router.post("/{bid_id}/notify", response_model=BidNotifyResult)
def notify_participants(
    bid_id: int, session: SessionDep, _: StaffUser, request: Request
) -> BidNotifyResult:
    """Send the link again to anyone the message did not reach."""
    tally = service.notify(session, bid_id, _public_base(request), retry_failed=True)
    return BidNotifyResult(**tally)


@router.get("/{bid_id}/history", response_model=Page[BidEvent])
def bid_history(
    bid_id: int,
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
) -> Page[BidEvent]:
    """What happened to this bid, newest first."""
    service.get_bid(session, bid_id)  # 404 for an unknown bid
    rows, total = service.history(session, bid_id, params)
    return Page.build(rows, total, params)


@router.get("/{bid_id}/links", response_model=Message)
def bid_links_hint(bid_id: int, session: SessionDep, _: StaffUser) -> Message:
    """Kept for the future messaging integration: the links live on the detail."""
    bid = service.get_bid(session, bid_id)
    return Message(message=f"Bid #{bid.id} has {len(bid.participants)} participant links.")
