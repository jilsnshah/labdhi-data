"""Reading inbound WhatsApp messages, and putting the real ones on the book.

The pipeline, and only the pipeline. Which agent runs when lives here; how an
agent runs lives in ``agentic_ai``; what an enquiry is lives in
``portal_enquiries``, which this reaches through the agents' tools and never
goes around.

Two paths, decided by whether we recognise the number.

**A party we know.** Their own classifier reads the message. Most of what
arrives is not an enquiry - "thanks", "ok", "when is the truck coming" - and
those end here, recorded as read and ignored. The rest go to the enquiry agent
for their side of the trade.

**A stranger.** A harder classifier first, because a number nobody introduced
could be anyone. If it is an enquiry, a second agent works out which side of
the trade they are on; without an answer to that, nothing is created, because a
party filed under the wrong side is worse than one nobody filed. Then they are
written down as a prospect, and only then does the enquiry agent run - so there
is never an enquiry pointing at nobody.

What makes it safe to run twice: a message is read only while it is PENDING,
and the row's state is the last thing written. Meta can deliver the same
webhook all day.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models.enums import (
    MessageProcessing,
    PartySource,
    PartyType,
    RecordStatus,
)
from app.models.party import Party
from app.models.whatsapp_message import WhatsAppMessage
from app.schemas.party import PartyQuickCreate
from app.services import agentic_ai, parties, whatsapp_inbox

logger = logging.getLogger(__name__)

#: What a stranger's inferred role means in the book.
PARTY_TYPE_FOR = {
    "CUSTOMER": PartyType.CUSTOMER,
    "SUPPLIER": PartyType.SUPPLIER,
    "TRANSPORTER": PartyType.TRANSPORTER,
}


@dataclass
class Outcome:
    """What became of one message."""

    status: MessageProcessing
    note: str = ""
    inquiry_id: int | None = None
    party_id: int | None = None

    @property
    def created(self) -> bool:
        return self.inquiry_id is not None


def _now() -> datetime:
    return datetime.now(UTC)


def _finish(session: Session, message: WhatsAppMessage, outcome: Outcome) -> Outcome:
    """Write the verdict onto the message. Always the last thing done.

    Flushed here and not left to the end of the batch: sessions in this
    application do not autoflush, so without it the next pass over the pending
    messages would read this one as still waiting.
    """
    message.processing_status = outcome.status
    message.processing_note = outcome.note[:300] or None
    message.processed_at = _now()
    if outcome.inquiry_id is not None:
        message.inquiry_id = outcome.inquiry_id
    if outcome.party_id is not None:
        message.party_id = outcome.party_id
    session.flush()
    logger.info(
        "enquiry ingestion: %s -> %s%s",
        message.wa_message_id,
        outcome.status.value,
        f" (inquiry #{outcome.inquiry_id})" if outcome.inquiry_id else "",
    )
    return outcome


def _sure_enough(answer) -> bool:
    """A low-confidence yes is treated as a no, deliberately.

    The desk loses a follow-up when this is too strict, and gains a wrong row
    on the book when it is too loose. The first is cheaper.
    """
    return answer.is_enquiry and answer.confidence >= settings.ai_min_confidence


def process(session: Session, message: WhatsAppMessage) -> Outcome:
    """Read one message and act on it. Never raises.

    Every failure becomes a FAILED row with a line saying what went wrong, so a
    message is never lost and can be retried once whatever broke is fixed.
    """
    if message.processing_status != MessageProcessing.PENDING:
        return Outcome(message.processing_status, "Already read.", message.inquiry_id)

    if not agentic_ai.available():
        return _finish(session, message, Outcome(MessageProcessing.SKIPPED, agentic_ai.why_not()))

    if not (message.body or "").strip():
        # A photo, a location, a sticker. There is nothing to read.
        return _finish(
            session,
            message,
            Outcome(MessageProcessing.IGNORED, f"A {message.message_type} with no text in it."),
        )

    try:
        party = _sender(session, message)
        outcome = (
            _known_party(session, message, party)
            if party is not None
            else _stranger(session, message)
        )
    except agentic_ai.AIUnavailable as error:
        outcome = Outcome(MessageProcessing.SKIPPED, str(error))
    except agentic_ai.AgentError as error:
        outcome = Outcome(MessageProcessing.FAILED, f"The agent failed: {error}")
    except AppError as error:
        outcome = Outcome(MessageProcessing.FAILED, f"Refused: {error}")
    except Exception as error:  # a database fault, a bug - still not lost
        logger.exception("enquiry ingestion: %s failed", message.wa_message_id)
        outcome = Outcome(MessageProcessing.FAILED, f"Unexpected: {error}")

    return _finish(session, message, outcome)


def _sender(session: Session, message: WhatsAppMessage) -> Party | None:
    """The party behind the number, if the desk knows it.

    The match the webhook already made is used where there is one, so one
    message is matched one way; otherwise the same lookup is done again, which
    covers a party added between the message arriving and it being read.
    """
    if message.party_id is not None:
        party = session.get(Party, message.party_id)
        if party is not None and party.status == RecordStatus.ACTIVE:
            return party
    return whatsapp_inbox.party_for(session, message.from_number)


# --------------------------------------------------------------------------- #
# A party the desk knows
# --------------------------------------------------------------------------- #
def _known_party(session: Session, message: WhatsAppMessage, party: Party) -> Outcome:
    verdict = agentic_ai.classify_known(party.party_type, message.body or "")
    if not _sure_enough(verdict):
        return Outcome(
            MessageProcessing.IGNORED,
            _why_not_an_enquiry(verdict),
            party_id=party.id,
        )
    return _record(session, message, party)


def _why_not_an_enquiry(verdict) -> str:
    if verdict.is_enquiry:
        return f"Possibly an enquiry but not certain ({verdict.confidence:.2f}): {verdict.reason}"
    return f"Not an enquiry: {verdict.reason}"


# --------------------------------------------------------------------------- #
# A number nobody has introduced
# --------------------------------------------------------------------------- #
def _stranger(session: Session, message: WhatsAppMessage) -> Outcome:
    verdict = agentic_ai.classify_unknown(message.body or "")
    if not _sure_enough(verdict):
        # Nothing is created for a stranger who has not clearly asked to trade.
        # Not a prospect, not a note - the message itself is the whole record.
        return Outcome(MessageProcessing.IGNORED, _why_not_an_enquiry(verdict))

    identity = agentic_ai.identify_sender(message.body or "", message.profile_name)
    if identity.role is None or identity.confidence < settings.ai_min_confidence:
        return Outcome(
            MessageProcessing.IGNORED,
            f"An enquiry, but which side of the trade is unclear: {identity.reason}",
        )

    party = _prospect(session, message, identity)
    return _record(session, message, party)


def _prospect(session: Session, message: WhatsAppMessage, identity) -> Party:
    """Write a stranger down, once.

    Looked up again first. Two messages from the same new number arriving
    together would otherwise make two prospects, and the lookup is against the
    number rather than anything the model said.
    """
    existing = whatsapp_inbox.party_for(session, message.from_number)
    if existing is not None:
        logger.info(
            "enquiry ingestion: %s already belongs to party %s",
            message.wa_message_id,
            existing.id,
        )
        return existing

    party = parties.quick_create_party(
        session,
        PartyQuickCreate(
            # Their firm if they named one, the name on their account if not,
            # and the number itself if neither - always something a person can
            # recognise in a list.
            name=identity.name or message.profile_name or f"+{message.from_number}",
            phone=message.from_number,
            contact_person=identity.contact_person,
            city=identity.city,
            notes="Introduced themselves over WhatsApp.",
        ),
        party_type=PARTY_TYPE_FOR[identity.role],
        user_id=None,
        source=PartySource.WHATSAPP,
    )
    logger.info(
        "enquiry ingestion: %s introduced party %s as %s",
        message.wa_message_id,
        party.id,
        identity.role,
    )
    return party


# --------------------------------------------------------------------------- #
# Recording the enquiry
# --------------------------------------------------------------------------- #
def _record(session: Session, message: WhatsAppMessage, party: Party) -> Outcome:
    """Hand the message to the enquiry agent for this party's side of the trade.

    What was created is read off the tools' own record, never off what the
    agent says about itself: a model that reports success it did not have would
    otherwise mark a message done with nothing on the book.
    """
    outcome = agentic_ai.ToolOutcome()
    tools = agentic_ai.tools_for(session, party, outcome)
    said = agentic_ai.record_enquiry(party.party_type, message.body or "", tools)

    if outcome.created:
        return Outcome(
            MessageProcessing.PROCESSED,
            said.note or "Recorded from WhatsApp.",
            inquiry_id=outcome.inquiry_id,
            party_id=party.id,
        )

    if outcome.errors:
        # A tool was called and the desk's own rules refused it. That is a
        # failure to look at, not a message to throw away.
        return Outcome(
            MessageProcessing.FAILED,
            f"The enquiry was refused: {'; '.join(outcome.errors)}",
            party_id=party.id,
        )

    # No tool call at all: the message was an enquiry but did not carry enough
    # to write one down. The desk reads it themselves.
    return Outcome(
        MessageProcessing.IGNORED,
        said.note or "An enquiry, but it did not say enough to record one.",
        party_id=party.id,
    )


# --------------------------------------------------------------------------- #
# Running it
# --------------------------------------------------------------------------- #
def pending(session: Session, limit: int | None = None) -> list[WhatsAppMessage]:
    """Messages waiting to be read, oldest first."""
    return list(
        session.scalars(
            select(WhatsAppMessage)
            .where(WhatsAppMessage.processing_status == MessageProcessing.PENDING)
            .order_by(WhatsAppMessage.received_at, WhatsAppMessage.id)
            .limit(limit or settings.ai_batch_size)
        ).all()
    )


def process_pending(session: Session, limit: int | None = None) -> dict[str, int]:
    """Read everything waiting. Returns a tally, for the log and the caller.

    One message failing does not stop the rest: each is its own decision, and
    the only thing they share is the batch they arrived in.
    """
    tally = {status.value.lower(): 0 for status in MessageProcessing}
    tally.pop("pending", None)
    for message in pending(session, limit):
        outcome = process(session, message)
        tally[outcome.status.value.lower()] = tally.get(outcome.status.value.lower(), 0) + 1
    return tally


def run_pending_in_background() -> dict[str, int]:
    """Read what is waiting, in a session of this task's own.

    Called after the webhook has already answered Meta, so it cannot use that
    request's session - it has been committed and closed by then. Failures are
    logged and swallowed: a background task that raises helps nobody.
    """
    from app.db.session import SessionLocal

    if not agentic_ai.available():
        return {}
    session = SessionLocal()
    try:
        tally = process_pending(session)
        session.commit()
        if any(tally.values()):
            logger.info("enquiry ingestion: %s", tally)
        return tally
    except Exception:
        session.rollback()
        logger.exception("enquiry ingestion: the background pass failed")
        return {}
    finally:
        session.close()
