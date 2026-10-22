"""Messages people send to the desk's WhatsApp number.

The other half of ``services/whatsapp.py``, which only ever speaks. This is
what comes back: a customer replying to a bid invitation, a transporter asking
a question, anyone who has the number writing in.

One row per message, and the row exists at most once however many times Meta
tells us about it. That matters more here than it looks: Meta retries a webhook
until it gets a 200, so the same message arrives again after any blip, and a
desk that saw one reply three times would be worse than one that saw none.
``wa_message_id`` is Meta's own id for the message and is unique here, which is
what makes a retry harmless.

Reading one is a separate step: ``services/enquiry_ingestion`` picks up the
PENDING rows afterwards and decides whether anything should come of them. That
separation is what keeps Meta's 200 fast, and it is also what makes the reading
idempotent - a message delivered twice is one row, and one row is read once.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MessageProcessing, message_processing_enum


class WhatsAppMessage(Base):
    """One inbound WhatsApp message, as Meta handed it to us."""

    __tablename__ = "whatsapp_messages"
    __table_args__ = (
        Index("ix_whatsapp_messages_from_received", "from_number", "received_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    #: Meta's id for this message. Unique, and the whole reason this table can
    #: be written to by a public endpoint that may be called twice.
    wa_message_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    #: Who sent it, as Meta gives it: country code and number, no plus.
    from_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    #: Which of our numbers it arrived on, when more than one is in play.
    phone_number_id: Mapped[str | None] = mapped_column(String(32))
    #: The name on their WhatsApp account. Theirs to change, so never trusted
    #: as identity - it is only here to make an unmatched number readable.
    profile_name: Mapped[str | None] = mapped_column(String(120))

    #: text, image, audio, document, button, interactive, and so on.
    message_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    #: What they actually said, when the message has words in it at all.
    body: Mapped[str | None] = mapped_column(Text())

    #: When they sent it, by Meta's clock.
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: When the webhook reached us. The two differ after an outage.
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    #: The party this number belongs to, where we recognise it. Null is
    #: ordinary: anyone at all can write to a WhatsApp number.
    party_id: Mapped[int | None] = mapped_column(
        ForeignKey("parties.id", ondelete="SET NULL"), index=True
    )

    #: The message object exactly as it arrived, so a kind we do not read yet
    #: is not lost - and so a bug here can be diagnosed from what was sent.
    raw: Mapped[dict | None] = mapped_column(JSONB)

    #: How far this message has got. Only PENDING rows are ever picked up.
    processing_status: Mapped[MessageProcessing] = mapped_column(
        message_processing_enum,
        nullable=False,
        default=MessageProcessing.PENDING,
        server_default=MessageProcessing.PENDING.value,
        index=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Why it ended where it did, in one line - the agent's reason for ignoring
    #: it, or what failed. Kept short, and never the message itself.
    processing_note: Mapped[str | None] = mapped_column(String(300))
    #: The inquiry this message produced, when it produced one.
    inquiry_id: Mapped[int | None] = mapped_column(
        ForeignKey("inquiries.id", ondelete="SET NULL"), index=True
    )

    party: Mapped[Party | None] = relationship(lazy="joined")  # noqa: F821
    inquiry: Mapped[Inquiry | None] = relationship(lazy="joined")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WhatsAppMessage {self.wa_message_id} from {self.from_number}>"
