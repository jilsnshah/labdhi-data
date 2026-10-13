"""Bids: the desk asks several parties to quote on one thing, at once.

An inquiry records a quote the desk already has. A bid is the opposite motion:
one lot of material (or one movement) is put in front of several parties, each
quotes against the others, and the desk picks. The two never touch - a bid
carries its own participants, quotations and history.

The auction is blind. A participant sees the best price standing against them
and how many are bidding, never who the others are or what each of them wrote.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    BidStatus,
    BidType,
    QuantityUnit,
    bid_status_enum,
    bid_type_enum,
    quantity_unit_enum,
)

QTY = Numeric(14, 3)
MONEY = Numeric(14, 2)

#: Which way a quotation is good. Selling to customers, the highest price wins;
#: buying material or a truck, the lowest does.
BEST_IS_HIGHEST: dict[BidType, bool] = {
    BidType.CUSTOMER: True,
    BidType.SUPPLIER: False,
    BidType.TRANSPORT: False,
}


class Bid(Base, TimestampMixin):
    """One lot put out to several parties.

    Customer and supplier bids name a product and a quantity; transport bids
    name two places and what is moving. The columns that do not apply to a type
    are null, and the check constraints keep an impossible row out.
    """

    __tablename__ = "bids"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_bids_quantity_positive"),
        CheckConstraint(
            "(bid_type = 'TRANSPORT') OR (product_id IS NOT NULL)",
            name="ck_bids_product_required",
        ),
        CheckConstraint(
            "(bid_type <> 'TRANSPORT') OR "
            "(pickup_location_id IS NOT NULL AND delivery_location_id IS NOT NULL)",
            name="ck_bids_transport_has_route",
        ),
        CheckConstraint(
            "(bid_type <> 'TRANSPORT') OR (pickup_location_id <> delivery_location_id)",
            name="ck_bids_transport_route_distinct",
        ),
        CheckConstraint(
            "(status <> 'CLOSED') OR (closed_at IS NOT NULL)",
            name="ck_bids_closed_has_timestamp",
        ),
        CheckConstraint(
            "(status = 'OPEN') OR (published_at IS NOT NULL) OR (status = 'DRAFT')",
            name="ck_bids_open_has_published",
        ),
        Index("ix_bids_type_status", "bid_type", "status"),
        Index("ix_bids_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bid_type: Mapped[BidType] = mapped_column(bid_type_enum, nullable=False, index=True)
    status: Mapped[BidStatus] = mapped_column(
        bid_status_enum,
        nullable=False,
        default=BidStatus.DRAFT,
        server_default=BidStatus.DRAFT.value,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(200))

    #: Customer and supplier bids: what is being sold or bought.
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    unit: Mapped[QuantityUnit] = mapped_column(
        quantity_unit_enum, nullable=False, server_default=QuantityUnit.MT.value
    )

    #: Transport bids: where it moves from and to.
    pickup_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT")
    )
    delivery_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT")
    )

    #: Free text the participants need: grade notes, packing, what is moving.
    specifications: Mapped[str | None] = mapped_column(Text())
    #: Shown to participants as the time to beat. Advisory - the desk closes.
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    #: Closed deliberately without picking anyone - the desk walked away.
    no_winner: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    winner_quote_id: Mapped[int | None] = mapped_column(
        ForeignKey("bid_quotes.id", ondelete="SET NULL", use_alter=True)
    )
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    awarded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))

    product: Mapped[Product | None] = relationship(lazy="joined")  # noqa: F821
    pickup_location: Mapped[Location | None] = relationship(  # noqa: F821
        foreign_keys=[pickup_location_id], lazy="joined"
    )
    delivery_location: Mapped[Location | None] = relationship(  # noqa: F821
        foreign_keys=[delivery_location_id], lazy="joined"
    )
    creator: Mapped[User] = relationship(foreign_keys=[created_by], lazy="joined")  # noqa: F821
    closer: Mapped[User | None] = relationship(  # noqa: F821
        foreign_keys=[closed_by], lazy="joined"
    )
    winner_quote: Mapped[BidQuote | None] = relationship(
        foreign_keys=[winner_quote_id], lazy="joined", post_update=True
    )
    participants: Mapped[list[BidParticipant]] = relationship(
        back_populates="bid", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def best_is_highest(self) -> bool:
        return BEST_IS_HIGHEST[self.bid_type]

    @property
    def is_open(self) -> bool:
        return self.status == BidStatus.OPEN

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Bid {self.id} {self.bid_type} {self.status}>"


class BidParticipant(Base, TimestampMixin):
    """One party invited to one bid, and the record of them opening it."""

    __tablename__ = "bid_participants"
    __table_args__ = (
        UniqueConstraint("bid_id", "party_id", name="uq_bid_participants_bid_party"),
        Index("ix_bid_participants_party_id", "party_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bid_id: Mapped[int] = mapped_column(
        ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True
    )
    party_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="RESTRICT"), nullable=False
    )
    first_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    bid: Mapped[Bid] = relationship(back_populates="participants")
    party: Mapped[Party] = relationship(lazy="joined")  # noqa: F821
    quote: Mapped[BidQuote | None] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
        uselist=False,
        passive_deletes=True,
        foreign_keys="BidQuote.participant_id",
    )


class BidQuote(Base, TimestampMixin):
    """What a participant is offering, as it stands.

    One row per participant: re-quoting overwrites it and bumps ``revision``,
    so the bid always shows what each party is offering now. Every revision is
    written to the audit log, so the history survives the overwrite.
    """

    __tablename__ = "bid_quotes"
    __table_args__ = (
        UniqueConstraint("participant_id", name="uq_bid_quotes_participant"),
        CheckConstraint("price > 0", name="ck_bid_quotes_price_positive"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_bid_quotes_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("bid_participants.id", ondelete="CASCADE"), nullable=False
    )
    #: Rupees per kilogram for material, rupees for a movement.
    price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    #: How much of the lot they will take, when that is theirs to choose.
    quantity: Mapped[Decimal | None] = mapped_column(QTY)
    notes: Mapped[str | None] = mapped_column(Text())
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: 1 on the first submission, then one more for each re-quote.
    revision: Mapped[int] = mapped_column(nullable=False, server_default="1")

    participant: Mapped[BidParticipant] = relationship(
        back_populates="quote", foreign_keys=[participant_id], lazy="joined"
    )
