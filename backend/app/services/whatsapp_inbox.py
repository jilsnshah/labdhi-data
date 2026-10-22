"""Receiving WhatsApp messages. The mirror of ``whatsapp.py``, which only sends.

Three jobs, and no more than three:

* **Prove the call came from Meta.** This is a public endpoint that writes to
  the database, so a payload without a valid signature is refused outright.
* **Read what arrived.** Meta's envelope is deep and carries several kinds of
  thing; this pulls out the messages and leaves the rest alone.
* **Write each message down once.** Meta retries a webhook until it gets a
  200, so the same message arrives again after any blip, and the desk seeing
  one reply three times would be worse than seeing none. Meta's own message id
  is unique in our table, and a repeat is counted and dropped.

What it deliberately does not do is act on anything. A message is recorded,
matched to a party when the number is one we know, and left there.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import RecordStatus
from app.models.party import Party
from app.models.whatsapp_message import WhatsAppMessage

logger = logging.getLogger(__name__)

#: Meta signs the raw body with the app secret and sends it in this header.
SIGNATURE_HEADER = "X-Hub-Signature-256"

#: Where the words live, per message kind. Everything else has no text at all.
_TEXT_AT = {
    "text": ("text", "body"),
    "button": ("button", "text"),
}


def verify_signature(raw_body: bytes, header: str | None) -> bool:
    """True when this body really was signed by our Meta app.

    Compared with ``compare_digest`` rather than ``==`` so that a wrong
    signature takes the same time to reject whatever is wrong with it.
    """
    secret = settings.whatsapp_app_secret
    if not secret or not header:
        return False
    sent = header.removeprefix("sha256=").strip()
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sent, expected)


def signature_required() -> bool:
    """Whether an unsigned payload may be accepted at all.

    With a secret configured, always no. Without one, a developer running this
    on their own machine can still post a sample payload - but a production
    deployment that has not been given a secret refuses everything, because an
    open write endpoint is worse than a webhook that does not work yet.
    """
    return bool(settings.whatsapp_app_secret) or settings.is_production


def verification_challenge(
    mode: str | None, token: str | None, challenge: str | None
) -> str | None:
    """Meta's subscribe handshake: echo the challenge, or refuse.

    Called once, when the webhook URL is first saved in the Meta dashboard.
    """
    if not settings.whatsapp_verify_token:
        return None
    matches = bool(token) and hmac.compare_digest(token or "", settings.whatsapp_verify_token)
    return challenge if mode == "subscribe" and matches else None


@dataclass
class InboundMessage:
    """One message, lifted out of Meta's envelope."""

    wa_message_id: str
    from_number: str
    message_type: str
    sent_at: datetime
    body: str | None = None
    profile_name: str | None = None
    phone_number_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def _when(timestamp: Any) -> datetime:
    """Meta sends unix seconds as a string. A missing one means 'now'."""
    try:
        return datetime.fromtimestamp(int(timestamp), tz=UTC)
    except (TypeError, ValueError):
        return datetime.now(UTC)


def _words(message: dict[str, Any]) -> str | None:
    """The text of a message, where its kind has any.

    An image or a document carries a caption instead, and plenty of kinds -
    a location, a contact card - carry nothing at all. None is an ordinary
    answer here, not a failure.
    """
    kind = message.get("type")
    if kind in _TEXT_AT:
        outer, inner = _TEXT_AT[kind]
        return (message.get(outer) or {}).get(inner)
    if kind == "interactive":
        interactive = message.get("interactive") or {}
        chosen = interactive.get("button_reply") or interactive.get("list_reply") or {}
        return chosen.get("title")
    caption = (message.get(kind) or {}).get("caption") if isinstance(kind, str) else None
    return caption


def parse(payload: dict[str, Any]) -> list[InboundMessage]:
    """Pull the messages out of a webhook payload.

    Meta's envelope is entry[] -> changes[] -> value, and ``value`` may carry
    messages, delivery receipts for things we sent, account updates, or
    nothing. Only messages are read here; the rest is acknowledged and ignored,
    which is what keeps Meta from retrying them forever.

    Nothing in here raises. A payload we cannot read is a payload we answer 200
    to and log, because the alternative is Meta retrying it every few minutes
    until it gives up and disables the webhook.
    """
    found: list[InboundMessage] = []
    for entry in payload.get("entry") or []:
        for change in (entry or {}).get("changes") or []:
            value = (change or {}).get("value") or {}
            metadata = value.get("metadata") or {}
            names = {
                contact.get("wa_id"): (contact.get("profile") or {}).get("name")
                for contact in value.get("contacts") or []
                if isinstance(contact, dict)
            }
            for message in value.get("messages") or []:
                if not isinstance(message, dict):
                    continue
                wa_id = message.get("id")
                sender = message.get("from")
                if not wa_id or not sender:
                    logger.warning("whatsapp webhook: message with no id or sender, skipped")
                    continue
                found.append(
                    InboundMessage(
                        wa_message_id=str(wa_id),
                        from_number=str(sender),
                        message_type=str(message.get("type") or "unknown"),
                        sent_at=_when(message.get("timestamp")),
                        body=_words(message),
                        profile_name=names.get(sender),
                        phone_number_id=metadata.get("phone_number_id"),
                        raw=message,
                    )
                )
    return found


def party_for(session: Session, number: str) -> Party | None:
    """The party this number belongs to, if we know it.

    Numbers are written half a dozen ways in the book - with +91, with spaces,
    with a leading zero - so the comparison is on the last ten digits of each,
    which is the part that identifies an Indian mobile. No match is the normal
    case: anyone at all can write to a WhatsApp number.
    """
    digits = "".join(character for character in number if character.isdigit())
    if len(digits) < 10:
        return None
    last_ten = digits[-10:]
    stored = func.regexp_replace(Party.phone, r"[^0-9]", "", "g")
    return session.scalars(
        select(Party)
        .where(
            Party.phone.is_not(None),
            func.right(stored, 10) == last_ten,
            Party.status == RecordStatus.ACTIVE,
            Party.merged_into_id.is_(None),
        )
        # Two parties can share a number; pick the same one every time rather
        # than whichever the database happens to return first.
        .order_by(Party.id)
        .limit(1)
    ).first()


def already_have(session: Session, wa_message_id: str) -> bool:
    return (
        session.scalar(
            select(WhatsAppMessage.id).where(WhatsAppMessage.wa_message_id == wa_message_id)
        )
        is not None
    )


def record(session: Session, messages: list[InboundMessage]) -> dict[str, int]:
    """Write down the ones we have not seen. Returns what happened to each.

    The check and the insert are not one atomic step, so two deliveries of the
    same message arriving at once could both pass the check; the unique
    constraint is what actually settles it, and the savepoint here means losing
    that race costs one row rather than the whole batch.
    """
    stored = duplicates = 0
    for message in messages:
        if already_have(session, message.wa_message_id):
            duplicates += 1
            continue
        party = party_for(session, message.from_number)
        row = WhatsAppMessage(
            wa_message_id=message.wa_message_id,
            from_number=message.from_number,
            phone_number_id=message.phone_number_id,
            profile_name=message.profile_name,
            message_type=message.message_type,
            body=message.body,
            sent_at=message.sent_at,
            party_id=party.id if party else None,
            raw=message.raw,
        )
        try:
            with session.begin_nested():
                session.add(row)
        except IntegrityError:
            duplicates += 1
            continue
        stored += 1

    if stored:
        logger.info("whatsapp webhook: stored %d message(s)", stored)
    return {"received": len(messages), "stored": stored, "duplicates": duplicates}


def receive(session: Session, payload: dict[str, Any]) -> dict[str, int]:
    """Read a webhook payload and write down what was in it."""
    return record(session, parse(payload))
