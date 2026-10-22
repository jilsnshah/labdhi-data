"""Bids: creating them, running them, and serving the participants' side.

Two audiences, two sets of rules, both enforced here rather than in the UI:

* The desk sees every quotation with the party attached.
* A participant, holding only an opaque portal code, sees the bids they were
  invited to, their own quotation, and the single best price standing. They
  never see another party's name or another party's number, and they cannot
  reach a bid they were not invited to.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.pagination import PageParams, paginate
from app.models.audit import AuditLog
from app.models.bid import Bid, BidParticipant, BidQuote
from app.models.enums import (
    AuditAction,
    BidStatus,
    BidType,
    MessageDeliveryStatus,
    PartyStage,
    PartyType,
    RecordStatus,
)
from app.models.masters import Product, product_applications
from app.models.party import Location, Party
from app.schemas.bid import (
    BidAwardRequest,
    BidCreate,
    BidEvent,
    BidListItem,
    BidUpdate,
    PortalBid,
    PortalHome,
    PortalQuote,
    PortalQuoteRequest,
    PortalResult,
)
from app.services import audit, whatsapp
from app.services.common import get_or_404
from app.services.portal import party_by_code, portal_code

#: Which book a bid is addressed to.
PARTY_TYPE_FOR: dict[BidType, PartyType] = {
    BidType.CUSTOMER: PartyType.CUSTOMER,
    BidType.SUPPLIER: PartyType.SUPPLIER,
    BidType.TRANSPORT: PartyType.TRANSPORTER,
}

DETAIL_LOADERS = (
    selectinload(Bid.participants).selectinload(BidParticipant.quote),
    selectinload(Bid.participants).selectinload(BidParticipant.party),
)

SORTABLE = {"created_at", "closes_at", "status", "quantity", "id"}
QUOTE_SORTABLE = {"price", "submitted_at", "revision"}
PARTICIPANT_SORTABLE = {"name", "created_at", "last_opened_at"}


def _counts(session: Session, bid_ids: Sequence[int]) -> dict[int, tuple[int, int]]:
    """Participants and quotations per bid, counted in the database.

    A bid can hold a hundred participants; loading them to call len() would
    make the list page grow with the size of the rooms it is listing.
    """
    if not bid_ids:
        return {}
    rows = session.execute(
        select(
            BidParticipant.bid_id,
            func.count(BidParticipant.id),
            func.count(BidQuote.id),
        )
        .select_from(BidParticipant)
        .outerjoin(BidQuote, BidQuote.participant_id == BidParticipant.id)
        .where(BidParticipant.bid_id.in_(bid_ids))
        .group_by(BidParticipant.bid_id)
    ).all()
    return {bid_id: (participants, quotes) for bid_id, participants, quotes in rows}


def _best_prices(session: Session, bids: Sequence[Bid]) -> dict[int, Decimal | None]:
    """The price to beat per bid: the highest when selling, the lowest when buying."""
    if not bids:
        return {}
    highest = [bid.id for bid in bids if bid.best_is_highest]
    lowest = [bid.id for bid in bids if not bid.best_is_highest]
    best: dict[int, Decimal | None] = {}
    for ids, aggregate in ((highest, func.max), (lowest, func.min)):
        if not ids:
            continue
        rows = session.execute(
            select(BidParticipant.bid_id, aggregate(BidQuote.price))
            .select_from(BidQuote)
            .join(BidParticipant, BidParticipant.id == BidQuote.participant_id)
            .where(BidParticipant.bid_id.in_(ids))
            .group_by(BidParticipant.bid_id)
        ).all()
        best.update(dict(rows))
    return best


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _now() -> datetime:
    return datetime.now(UTC)


def _amount(quantity: Decimal) -> str:
    """40.000 reads as 40; 2.500 as 2.5. Trailing zeros help nobody in a title."""
    whole = quantity == quantity.to_integral_value()
    return f"{quantity.quantize(Decimal(1)) if whole else quantity.normalize():f}"


def describe(bid: Bid) -> str:
    """A title for the bid, written if the desk did not write one."""
    if bid.title:
        return bid.title
    amount = f"{_amount(bid.quantity)} {bid.unit.value}"
    if bid.bid_type == BidType.TRANSPORT:
        start = bid.pickup_location.display_name if bid.pickup_location else "?"
        end = bid.delivery_location.display_name if bid.delivery_location else "?"
        return f"{amount} · {start} to {end}"
    product = bid.product.display_name if bid.product else "?"
    return f"{amount} · {product}"


def best_price(bid: Bid) -> Decimal | None:
    """The price to beat: highest when we sell, lowest when we buy."""
    prices = [p.quote.price for p in bid.participants if p.quote is not None]
    if not prices:
        return None
    return max(prices) if bid.best_is_highest else min(prices)


def quotes_of(bid: Bid) -> list[BidQuote]:
    """Every quotation, best first."""
    quotes = [p.quote for p in bid.participants if p.quote is not None]
    return sorted(quotes, key=lambda q: q.price, reverse=bid.best_is_highest)


def _editable(bid: Bid) -> None:
    if bid.status == BidStatus.CLOSED:
        raise ConflictError(f"Bid #{bid.id} is closed.")


# --------------------------------------------------------------------------- #
# The desk
# --------------------------------------------------------------------------- #
def _validate_refs(session: Session, bid_type: BidType, payload: BidCreate | BidUpdate) -> None:
    if getattr(payload, "product_id", None) is not None:
        product = session.get(Product, payload.product_id)
        if product is None or product.status != RecordStatus.ACTIVE:
            raise ValidationError("That product is not available.", field="product_id")
    for field in ("pickup_location_id", "delivery_location_id"):
        location_id = getattr(payload, field, None)
        if location_id is not None and session.get(Location, location_id) is None:
            raise ValidationError("That location was not found.", field=field)
    if bid_type != BidType.TRANSPORT and getattr(payload, "product_id", None) is None:
        return


def create_bid(session: Session, payload: BidCreate, user_id: int) -> Bid:
    _validate_refs(session, payload.bid_type, payload)
    bid = Bid(
        bid_type=payload.bid_type,
        status=BidStatus.DRAFT,
        title=payload.title,
        product_id=payload.product_id,
        quantity=payload.quantity,
        unit=payload.unit,
        pickup_location_id=payload.pickup_location_id,
        delivery_location_id=payload.delivery_location_id,
        specifications=payload.specifications,
        closes_at=payload.closes_at,
        created_by=user_id,
    )
    session.add(bid)
    session.flush()

    if payload.party_ids:
        add_participants(session, bid.id, payload.party_ids, user_id, _audit=False)

    audit.record(
        session,
        user_id=user_id,
        entity_type="bid",
        entity_id=bid.id,
        action=AuditAction.CREATE,
        new_value={
            "bid_type": bid.bid_type.value,
            "title": describe(bid),
            "participants": len(payload.party_ids),
        },
    )
    session.flush()
    return get_bid(session, bid.id)


def get_bid(session: Session, bid_id: int) -> Bid:
    # populate_existing: participants and quotes are added mid-request, and a
    # stale collection on the identity-mapped object would hide them.
    bid = session.scalar(
        select(Bid)
        .options(*DETAIL_LOADERS)
        .where(Bid.id == bid_id)
        .execution_options(populate_existing=True)
    )
    if bid is None:
        raise NotFoundError(f"Bid #{bid_id} was not found.")
    return bid


def update_bid(session: Session, bid_id: int, payload: BidUpdate, user_id: int) -> Bid:
    bid = get_bid(session, bid_id)
    _editable(bid)
    data = payload.model_dump(exclude_unset=True)

    # Once participants can see it, only the closing time may move: changing the
    # lot under a live auction would invalidate the quotes already given.
    if bid.status == BidStatus.OPEN:
        disallowed = set(data) - {"closes_at", "title"}
        if disallowed:
            fields = ", ".join(sorted(disallowed))
            raise ConflictError(
                "An open bid's terms cannot change; close it and raise a new one. "
                f"Only the closing time and title may be edited (got: {fields})."
            )

    _validate_refs(session, bid.bid_type, payload)
    changes: dict[str, tuple] = {}
    for field, value in data.items():
        before = getattr(bid, field)
        if before != value:
            changes[field] = (str(before), str(value))
            setattr(bid, field, value)
    if changes:
        audit.record_changes(
            session, user_id=user_id, entity_type="bid", entity_id=bid.id, changes=changes
        )
    session.flush()
    return get_bid(session, bid.id)


def add_participants(
    session: Session, bid_id: int, party_ids: list[int], user_id: int, *, _audit: bool = True
) -> Bid:
    """Invite parties. The book must match the bid: customers bid on a sale."""
    bid = get_bid(session, bid_id)
    _editable(bid)
    expected = PARTY_TYPE_FOR[bid.bid_type]
    already = {p.party_id for p in bid.participants}
    added: list[str] = []

    for party_id in dict.fromkeys(party_ids):
        if party_id in already:
            continue
        party = get_or_404(session, Party, party_id, "Party")
        if party.party_type != expected:
            raise ValidationError(
                f"'{party.name}' is a {party.party_type.value.lower()}; "
                f"a {bid.bid_type.value.lower()} bid goes to {expected.value.lower()}s.",
                field="party_ids",
            )
        if party.stage == PartyStage.MERGED:
            raise ValidationError(
                f"'{party.name}' was merged into another party.", field="party_ids"
            )
        if party.status != RecordStatus.ACTIVE:
            raise ValidationError(f"'{party.name}' is inactive.", field="party_ids")
        session.add(BidParticipant(bid_id=bid.id, party_id=party.id))
        portal_code(session, party)
        added.append(party.name)

    session.flush()
    if added and _audit:
        audit.record(
            session,
            user_id=user_id,
            entity_type="bid",
            entity_id=bid.id,
            action=AuditAction.UPDATE,
            new_value={"invited": added},
        )
    return get_bid(session, bid.id)


def remove_participant(session: Session, bid_id: int, participant_id: int, user_id: int) -> Bid:
    bid = get_bid(session, bid_id)
    _editable(bid)
    participant = next((p for p in bid.participants if p.id == participant_id), None)
    if participant is None:
        raise NotFoundError("That participant is not on this bid.")
    if participant.quote is not None:
        raise ConflictError(
            f"'{participant.party.name}' has already quoted; their offer would be lost."
        )
    name = participant.party.name
    session.delete(participant)
    session.flush()
    audit.record(
        session,
        user_id=user_id,
        entity_type="bid",
        entity_id=bid.id,
        action=AuditAction.UPDATE,
        new_value={"removed": name},
    )
    return get_bid(session, bid.id)


def invite_message(party_name: str, bid: Bid, link: str) -> str:
    """What the participant reads on their phone.

    Short, because it arrives on a phone and is read in a second: who it is
    for, what is on offer, and the one link that is theirs.
    """
    lot = describe(bid)
    lines = [
        f"Hello {party_name}, a new bid is open on the Labdhi trading desk.",
        "",
        f"Lot: {lot}",
    ]
    if bid.closes_at:
        lines.append(f"Closes: {bid.closes_at.astimezone().strftime('%d %b %Y, %H:%M')}")
    lines += [
        "",
        "Open this link to see the details and place your offer:",
        link,
        "",
        "You can revise your offer at any time while the bid is open.",
        "",
        "Reply to this message so we can reach you on future bids.",
    ]
    return "\n".join(lines)


def _send_invite(party_name: str, phone: str | None, bid: Bid, link: str):
    """Plain text, which reads like a message from a person, not a form letter.

    It reaches anyone who has written to the desk's number in the last 24
    hours. For anyone who has not, WhatsApp accepts the message, hands back a
    message id, and drops it without ever saying so - verified against a real
    handset both ways. That is why the invitation asks them to reply: one reply
    opens the window for every bid after it.

    Error 131047 is the one case where Meta admits the window is shut, so a
    text refused for that reason is retried as the approved template, and
    ``whatsapp_use_template`` sends everything that way.
    """
    body = invite_message(party_name, bid, link)
    params = [party_name, f"{_amount(bid.quantity)} {bid.unit.value}", link]

    if settings.whatsapp_use_template:
        return whatsapp.send_template(phone, template=settings.whatsapp_bid_template, params=params)

    result = whatsapp.send_text(phone, body)
    if not result.ok and not result.skipped and "131047" in (result.error or ""):
        return whatsapp.send_template(phone, template=settings.whatsapp_bid_template, params=params)
    return result


def notify(
    session: Session,
    bid_id: int,
    base_url: str,
    *,
    participant_ids: Sequence[int] | None = None,
    retry_failed: bool = False,
) -> dict[str, int]:
    """WhatsApp each participant the link that belongs to them.

    Called when a bid is opened, and when someone is invited to one already
    running. Never raises: the desk asked for the bid to open, so a phone
    network that will not cooperate is recorded against the participant rather
    than thrown back at the caller.

    Only a participant who has not already been told is messaged, so pressing
    Open twice does not message the room twice.
    """
    bid = get_bid(session, bid_id)
    if bid.status != BidStatus.OPEN:
        return {"sent": 0, "failed": 0, "skipped": 0}

    participants = session.scalars(
        select(BidParticipant)
        .options(selectinload(BidParticipant.party))
        .where(BidParticipant.bid_id == bid_id)
    ).all()

    tally = {"sent": 0, "failed": 0, "skipped": 0}
    for participant in participants:
        if participant.id in (participant_ids or []) or participant_ids is None:
            already_told = participant.notify_status == MessageDeliveryStatus.SENT
            worth_retrying = retry_failed and participant.notify_status in {
                MessageDeliveryStatus.FAILED,
                MessageDeliveryStatus.SKIPPED,
            }
            if already_told or (participant.notify_status is not None and not worth_retrying):
                continue
        else:
            continue

        party = participant.party
        code = portal_code(session, party)
        link = f"{base_url}/portal/{code}/{bid.id}"
        result = _send_invite(party.name, party.phone, bid, link)

        participant.notified_at = _now()
        participant.notify_message_id = result.message_id
        participant.notify_error = result.error
        if result.ok:
            participant.notify_status = MessageDeliveryStatus.SENT
            tally["sent"] += 1
        elif result.skipped or not party.phone:
            participant.notify_status = MessageDeliveryStatus.SKIPPED
            tally["skipped"] += 1
        else:
            participant.notify_status = MessageDeliveryStatus.FAILED
            tally["failed"] += 1

    session.flush()
    return tally


def publish(session: Session, bid_id: int, user_id: int) -> Bid:
    bid = get_bid(session, bid_id)
    if bid.status == BidStatus.CLOSED:
        raise ConflictError(f"Bid #{bid.id} is closed.")
    if bid.status == BidStatus.OPEN:
        return bid
    if not bid.participants:
        raise ValidationError(
            "Invite at least one participant before opening the bid.", field="party_ids"
        )
    bid.status = BidStatus.OPEN
    bid.published_at = _now()
    session.flush()
    audit.record(
        session,
        user_id=user_id,
        entity_type="bid",
        entity_id=bid.id,
        action=AuditAction.PUBLISH,
        new_value={"status": BidStatus.OPEN.value, "participants": len(bid.participants)},
    )
    session.flush()
    return get_bid(session, bid.id)


def close(session: Session, bid_id: int, user_id: int, *, without_winner: bool = False) -> Bid:
    """Stop the auction. Quotations are kept exactly as they stand.

    Closing plainly leaves the award open, to be made by judgement afterwards.
    Closing without a winner records that the desk walked away.
    """
    bid = get_bid(session, bid_id)
    if bid.status == BidStatus.DRAFT:
        raise ConflictError("A draft bid has not been opened; there is nothing to close.")
    if bid.status == BidStatus.CLOSED:
        raise ConflictError(f"Bid #{bid.id} is already closed.")

    bid.status = BidStatus.CLOSED
    bid.closed_at = _now()
    bid.closed_by = user_id
    bid.no_winner = without_winner
    session.flush()
    audit.record(
        session,
        user_id=user_id,
        entity_type="bid",
        entity_id=bid.id,
        action=AuditAction.CLOSE,
        new_value={
            "status": BidStatus.CLOSED.value,
            "no_winner": without_winner,
            "quotes": len(quotes_of(bid)),
        },
    )
    session.flush()
    return get_bid(session, bid.id)


def award(session: Session, bid_id: int, payload: BidAwardRequest, user_id: int) -> Bid:
    """Pick the winning quotation. The desk's judgement, not the best number."""
    bid = get_bid(session, bid_id)
    if bid.status != BidStatus.CLOSED:
        raise ConflictError("Close the bid before choosing a winner.")

    quote = next((q for q in quotes_of(bid) if q.id == payload.quote_id), None)
    if quote is None:
        raise NotFoundError("That quotation is not on this bid.")

    bid.winner_quote_id = quote.id
    bid.no_winner = False
    bid.awarded_at = _now()
    bid.awarded_by = user_id
    session.flush()
    audit.record(
        session,
        user_id=user_id,
        entity_type="bid",
        entity_id=bid.id,
        action=AuditAction.AWARD,
        new_value={
            "party": quote.participant.party.name,
            "price": str(quote.price),
        },
    )
    session.flush()
    return get_bid(session, bid.id)


# --------------------------------------------------------------------------- #
# Listing
# --------------------------------------------------------------------------- #
def _apply_filters(
    stmt: Select,
    *,
    bid_type: BidType | None,
    status: BidStatus | None,
    product_id: int | None,
    party_id: int | None,
    material_id: int | None = None,
    grade_id: int | None = None,
    manufacturer_id: int | None = None,
    application_id: int | None = None,
    area: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    q: str | None = None,
) -> Select:
    if bid_type is not None:
        stmt = stmt.where(Bid.bid_type == bid_type)
    if status is not None:
        stmt = stmt.where(Bid.status == status)
    if product_id is not None:
        stmt = stmt.where(Bid.product_id == product_id)
    if party_id is not None:
        stmt = stmt.where(
            Bid.id.in_(select(BidParticipant.bid_id).where(BidParticipant.party_id == party_id))
        )
    if any(v is not None for v in (material_id, grade_id, manufacturer_id, application_id)):
        # Narrow through the product the bid is for; transport bids carry none,
        # so asking what the material is drops them out.
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
        stmt = stmt.where(Bid.product_id.in_(products))
    if area:
        # Either end of a transport route sits in that locality.
        in_area = select(Location.id).where(func.lower(Location.area) == area.strip().lower())
        stmt = stmt.where(
            or_(Bid.pickup_location_id.in_(in_area), Bid.delivery_location_id.in_(in_area))
        )
    if created_from:
        stmt = stmt.where(func.date(Bid.created_at) >= created_from)
    if created_to:
        stmt = stmt.where(func.date(Bid.created_at) <= created_to)
    if q:
        like = f"%{q.strip()}%"
        conditions = [Bid.title.ilike(like), Bid.specifications.ilike(like)]
        if q.strip().isdigit():
            conditions.append(Bid.id == int(q.strip()))
        conditions.append(
            Bid.product_id.in_(select(Product.id).where(Product.display_name.ilike(like)))
        )
        conditions.append(
            Bid.id.in_(
                select(BidParticipant.bid_id)
                .join(Party, Party.id == BidParticipant.party_id)
                .where(Party.name.ilike(like))
            )
        )
        stmt = stmt.where(or_(*conditions))
    return stmt


def list_bids(
    session: Session,
    params: PageParams,
    *,
    bid_type: BidType | None = None,
    status: BidStatus | None = None,
    product_id: int | None = None,
    party_id: int | None = None,
    material_id: int | None = None,
    grade_id: int | None = None,
    manufacturer_id: int | None = None,
    application_id: int | None = None,
    area: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    q: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> tuple[list[BidListItem], int]:
    # No participant loading here: the row needs counts, not the room.
    stmt = select(Bid)
    stmt = _apply_filters(
        stmt,
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
    )
    column = getattr(Bid, sort_by if sort_by in SORTABLE else "created_at")
    stmt = stmt.order_by(column.desc() if sort_dir.lower() == "desc" else column.asc())
    rows, total = paginate(session, stmt, params)

    counts = _counts(session, [bid.id for bid in rows])
    best = _best_prices(session, rows)
    return [to_list_item(bid, counts=counts, best=best) for bid in rows], total


def to_list_item(
    bid: Bid,
    *,
    counts: dict[int, tuple[int, int]] | None = None,
    best: dict[int, Decimal | None] | None = None,
) -> BidListItem:
    participant_count, quote_count = (counts or {}).get(bid.id, (0, 0))
    winner = bid.winner_quote
    return BidListItem(
        id=bid.id,
        bid_type=bid.bid_type,
        status=bid.status,
        title=describe(bid),
        product_id=bid.product_id,
        product_name=bid.product.display_name if bid.product else None,
        quantity=bid.quantity,
        unit=bid.unit,
        pickup_name=bid.pickup_location.display_name if bid.pickup_location else None,
        delivery_name=bid.delivery_location.display_name if bid.delivery_location else None,
        closes_at=bid.closes_at,
        participant_count=participant_count,
        quote_count=quote_count,
        best_price=(best or {}).get(bid.id),
        winner_party_name=winner.participant.party.name if winner else None,
        no_winner=bid.no_winner,
        created_by=bid.created_by,
        created_by_name=bid.creator.name if bid.creator else None,
        created_at=bid.created_at,
        published_at=bid.published_at,
        closed_at=bid.closed_at,
    )


def counts_for(session: Session, bid_id: int) -> tuple[int, int]:
    """(participants, quotations) for one bid, counted in the database."""
    return _counts(session, [bid_id]).get(bid_id, (0, 0))


def best_price_of(session: Session, bid: Bid) -> Decimal | None:
    """The price to beat, without loading the room to find it."""
    return _best_prices(session, [bid]).get(bid.id)


def list_quotes(
    session: Session,
    bid_id: int,
    params: PageParams,
    *,
    q: str | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> tuple[list[BidQuote], int]:
    """The offers on one bid, best first unless the desk asks otherwise.

    Paginated: a hundred parties can be quoting, and the desk still has to be
    able to find one of them.
    """
    bid = get_bid(session, bid_id)
    stmt = (
        select(BidQuote)
        .join(BidParticipant, BidParticipant.id == BidQuote.participant_id)
        .where(BidParticipant.bid_id == bid_id)
        .options(selectinload(BidQuote.participant).selectinload(BidParticipant.party))
    )
    if q:
        stmt = stmt.where(
            BidQuote.participant_id.in_(
                select(BidParticipant.id)
                .join(Party, Party.id == BidParticipant.party_id)
                .where(BidParticipant.bid_id == bid_id, Party.name.ilike(f"%{q.strip()}%"))
            )
        )

    column = {
        "price": BidQuote.price,
        "submitted_at": BidQuote.submitted_at,
        "revision": BidQuote.revision,
    }.get(sort_by or "", BidQuote.price)
    if sort_dir:
        descending = sort_dir.lower() == "desc"
    else:
        # No preference: best first, which depends on which way the bid runs.
        descending = bid.best_is_highest if column is BidQuote.price else True
    stmt = stmt.order_by(column.desc() if descending else column.asc(), BidQuote.id.asc())
    return paginate(session, stmt, params)


def list_participants(
    session: Session,
    bid_id: int,
    params: PageParams,
    *,
    q: str | None = None,
    quoted: bool | None = None,
    opened: bool | None = None,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> tuple[list[BidParticipant], int]:
    """Everyone invited to one bid, with who has answered and who has not."""
    get_bid(session, bid_id)
    stmt = (
        select(BidParticipant)
        .join(Party, Party.id == BidParticipant.party_id)
        .where(BidParticipant.bid_id == bid_id)
        .options(
            selectinload(BidParticipant.party),
            selectinload(BidParticipant.quote),
        )
    )
    if q:
        stmt = stmt.where(Party.name.ilike(f"%{q.strip()}%"))
    if quoted is not None:
        has_quote = BidParticipant.id.in_(select(BidQuote.participant_id))
        stmt = stmt.where(has_quote if quoted else ~has_quote)
    if opened is not None:
        stmt = stmt.where(
            BidParticipant.first_opened_at.is_not(None)
            if opened
            else BidParticipant.first_opened_at.is_(None)
        )

    column = {
        "name": Party.name,
        "created_at": BidParticipant.created_at,
        "last_opened_at": BidParticipant.last_opened_at,
    }.get(sort_by or "", Party.name)
    stmt = stmt.order_by(column.desc() if sort_dir.lower() == "desc" else column.asc())
    return paginate(session, stmt, params)


def history(session: Session, bid_id: int, params: PageParams) -> tuple[list[BidEvent], int]:
    """What happened to this bid, newest first and a page at a time.

    A busy auction writes an entry per quotation and per re-quote, so a bid
    with a hundred bidders has hundreds of lines; the rail shows the latest.
    """
    stmt = (
        select(AuditLog)
        .where(AuditLog.entity_type == "bid", AuditLog.entity_id == bid_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    rows, total = paginate(session, stmt, params)

    events: list[BidEvent] = []
    for row in rows:
        new = row.new_value or {}
        action = row.action.value if hasattr(row.action, "value") else str(row.action)
        if action == AuditAction.CREATE.value:
            summary = f"Bid raised: {new.get('title', '')}"
        elif action == AuditAction.PUBLISH.value:
            summary = f"Opened to {new.get('participants', 0)} participants"
        elif action == AuditAction.QUOTE.value:
            revision = new.get("revision", 1)
            verb = "quoted" if revision == 1 else f"re-quoted (revision {revision})"
            summary = f"{new.get('party', 'A participant')} {verb} at {new.get('price', '')}"
        elif action == AuditAction.CLOSE.value:
            summary = (
                "Closed without a winner" if new.get("no_winner") else "Closed to further quotes"
            )
        elif action == AuditAction.AWARD.value:
            summary = f"Awarded to {new.get('party', '')} at {new.get('price', '')}"
        elif new.get("invited"):
            summary = f"Invited {', '.join(new['invited'])}"
        elif new.get("removed"):
            summary = f"Removed {new['removed']}"
        else:
            summary = "Updated"
        events.append(
            BidEvent(
                at=row.created_at,
                action=action,
                summary=summary,
                actor=row.user.name if row.user else None,
            )
        )
    return events, total


# --------------------------------------------------------------------------- #
# The participants' side
# --------------------------------------------------------------------------- #
def _participant(session: Session, party: Party, bid_id: int) -> BidParticipant:
    participant = session.scalar(
        select(BidParticipant)
        .options(selectinload(BidParticipant.quote))
        .where(BidParticipant.bid_id == bid_id, BidParticipant.party_id == party.id)
    )
    # A bid they were not invited to is indistinguishable from one that does
    # not exist, so the portal cannot be used to count the desk's bids.
    if participant is None:
        raise NotFoundError("This bid is not available.")
    return participant


def _portal_result(bid: Bid, participant: BidParticipant) -> PortalResult | None:
    """How a closed bid ended, told from this participant's seat.

    An open bid has no result yet. A closed one does, and the party who quoted
    on it is owed the answer either way - but only their own half of it: that
    their offer was taken or that another was, never whose.
    """
    if bid.status != BidStatus.CLOSED:
        return None
    if bid.no_winner:
        return PortalResult.NO_WINNER
    if bid.winner_quote_id is None:
        return PortalResult.UNDECIDED
    quote = participant.quote
    if quote is not None and quote.id == bid.winner_quote_id:
        return PortalResult.WON
    return PortalResult.NOT_SELECTED


def to_portal_bid(bid: Bid, participant: BidParticipant) -> PortalBid:
    quote = participant.quote
    best = best_price(bid)
    return PortalBid(
        id=bid.id,
        bid_type=bid.bid_type,
        status=bid.status,
        title=describe(bid),
        product_name=bid.product.display_name if bid.product else None,
        quantity=bid.quantity,
        unit=bid.unit,
        pickup_name=bid.pickup_location.display_name if bid.pickup_location else None,
        delivery_name=bid.delivery_location.display_name if bid.delivery_location else None,
        specifications=bid.specifications,
        closes_at=bid.closes_at,
        best_is_highest=bid.best_is_highest,
        best_price=best,
        bidders=len([p for p in bid.participants if p.quote is not None]),
        leading=bool(quote and best is not None and quote.price == best),
        my_quote=(
            PortalQuote(
                price=quote.price,
                quantity=quote.quantity,
                notes=quote.notes,
                submitted_at=quote.submitted_at,
                revision=quote.revision,
            )
            if quote
            else None
        ),
        can_quote=bid.status == BidStatus.OPEN,
        closed_at=bid.closed_at,
        result=_portal_result(bid, participant),
    )


def portal_home(session: Session, code: str) -> PortalHome:
    party = party_by_code(session, code)
    rows = session.scalars(
        select(Bid)
        .options(*DETAIL_LOADERS)
        .join(BidParticipant, BidParticipant.bid_id == Bid.id)
        .where(
            BidParticipant.party_id == party.id,
            # A draft is the desk's own business until it is opened.
            Bid.status != BidStatus.DRAFT,
        )
        .order_by(Bid.created_at.desc())
    ).all()

    open_bids: list[PortalBid] = []
    closed_bids: list[PortalBid] = []
    for bid in rows:
        participant = next(p for p in bid.participants if p.party_id == party.id)
        view = to_portal_bid(bid, participant)
        (open_bids if bid.status == BidStatus.OPEN else closed_bids).append(view)

    return PortalHome(
        participant_name=party.name,
        party_type=party.party_type.value,
        open_bids=open_bids,
        closed_bids=closed_bids[:20],
    )


def portal_bid(session: Session, code: str, bid_id: int, *, record_open: bool = True) -> PortalBid:
    party = party_by_code(session, code)
    participant = _participant(session, party, bid_id)
    bid = get_bid(session, bid_id)
    if bid.status == BidStatus.DRAFT:
        raise NotFoundError("This bid is not available.")

    if record_open:
        now = _now()
        if participant.first_opened_at is None:
            participant.first_opened_at = now
        participant.last_opened_at = now
        session.flush()

    return to_portal_bid(bid, participant)


def submit_quote(
    session: Session, code: str, bid_id: int, payload: PortalQuoteRequest
) -> PortalBid:
    """Record what a participant is offering, or replace what they offered."""
    party = party_by_code(session, code)
    participant = _participant(session, party, bid_id)
    bid = get_bid(session, bid_id)

    if bid.status != BidStatus.OPEN:
        raise ConflictError(
            "This bid is closed and is not taking quotations."
            if bid.status == BidStatus.CLOSED
            else "This bid is not available."
        )
    if payload.quantity is not None and payload.quantity > bid.quantity:
        raise ValidationError(
            f"The lot is {bid.quantity:g} {bid.unit.value}; you cannot bid for more.",
            field="quantity",
        )

    now = _now()
    price = payload.price.quantize(Decimal("0.01"))
    quantity = payload.quantity.quantize(Decimal("0.001")) if payload.quantity else None
    quote = participant.quote
    if quote is None:
        quote = BidQuote(
            participant_id=participant.id,
            price=price,
            quantity=quantity,
            notes=payload.notes,
            submitted_at=now,
            revision=1,
        )
        session.add(quote)
    else:
        quote.price = price
        quote.quantity = quantity
        quote.notes = payload.notes
        quote.submitted_at = now
        quote.revision += 1
    session.flush()

    # The row holds only the latest offer; the log holds every one of them.
    audit.record(
        session,
        user_id=None,
        entity_type="bid",
        entity_id=bid.id,
        action=AuditAction.QUOTE,
        new_value={
            "party": party.name,
            "party_id": party.id,
            "price": str(quote.price),
            "quantity": str(quote.quantity) if quote.quantity is not None else None,
            "revision": quote.revision,
        },
    )
    session.flush()
    bid = get_bid(session, bid_id)
    participant = next(p for p in bid.participants if p.party_id == party.id)
    return to_portal_bid(bid, participant)


def participant_links(session: Session, bid: Bid, base_url: str) -> dict[int, tuple[str, str]]:
    """Copy-ready links per participant: the bid itself, and their portal."""
    links: dict[int, tuple[str, str]] = {}
    for participant in bid.participants:
        code = portal_code(session, participant.party)
        links[participant.id] = (
            f"{base_url}/portal/{code}/{bid.id}",
            f"{base_url}/portal/{code}",
        )
    return links


def quote_count(session: Session, bid_id: int) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(BidQuote)
            .join(BidParticipant, BidParticipant.id == BidQuote.participant_id)
            .where(BidParticipant.bid_id == bid_id)
        )
        or 0
    )
