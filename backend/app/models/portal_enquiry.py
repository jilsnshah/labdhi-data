"""Enquiries that parties send in themselves, through their portal link.

An enquiry sent in through a portal link becomes an inquiry the moment it
arrives - no queue, no approval. Whatever the party named that we did not have
is created as they go: a material, a grade, a manufacturer, the product the
three of them make, and the town they typed. By the time this row is written
there is a real inquiry behind it.

The table still exists because an inquiry cannot hold everything they sent.
Their note is theirs, the places are the words they used rather than the rows
we matched them to, and ``inquiry_id`` ties the two together. It is the record
of where an inquiry came from and what was actually said.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    InquiryType,
    QuantityUnit,
    inquiry_type_enum,
    quantity_unit_enum,
)

QTY = Numeric(14, 3)
MONEY = Numeric(14, 2)


class PortalEnquiry(Base, TimestampMixin):
    """One enquiry, as a party typed it into their own link."""

    __tablename__ = "portal_enquiries"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_portal_enquiries_quantity_positive"),
        CheckConstraint("rate IS NULL OR rate > 0", name="ck_portal_enquiries_rate_positive"),
        # A load needs no product; anything bought or sold resolves to one,
        # creating the material, grade and manufacturer if they were new.
        CheckConstraint(
            "inquiry_type = 'TRANSPORT' OR product_id IS NOT NULL",
            name="ck_portal_enquiries_product_named",
        ),
        Index("ix_portal_enquiries_party_created_at", "party_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    #: Who sent it, resolved from the portal code - never taken from the form.
    party_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    #: Decided by what the party is, not by what they say they want.
    inquiry_type: Mapped[InquiryType] = mapped_column(inquiry_type_enum, nullable=False, index=True)

    #: The grade they asked about, resolved from what they picked or typed.
    #: Null only for a load, which carries no product.
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )

    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    unit: Mapped[QuantityUnit] = mapped_column(
        quantity_unit_enum, nullable=False, server_default=QuantityUnit.MT.value
    )

    #: Places in the words they used, because a party cannot be asked to know
    #: our location master. A customer says where they want it, a transporter
    #: both ends of the run. The matching location rows hang off the inquiry;
    #: these are what was actually typed.
    from_place: Mapped[str | None] = mapped_column(String(200))
    to_place: Mapped[str | None] = mapped_column(String(200))

    #: The rate they are asking for or offering: per kilogram for a product,
    #: the whole freight for a load. Optional - plenty of enquiries are only
    #: "what's your price".
    rate: Mapped[Decimal | None] = mapped_column(MONEY)
    notes: Mapped[str | None] = mapped_column(Text())

    #: The inquiry this became. Written in the same breath as the row itself.
    inquiry_id: Mapped[int] = mapped_column(
        ForeignKey("inquiries.id", ondelete="CASCADE"), nullable=False, index=True
    )

    party: Mapped[Party] = relationship(lazy="joined")  # noqa: F821
    product: Mapped[Product | None] = relationship(lazy="joined")  # noqa: F821
    inquiry: Mapped[Inquiry] = relationship(lazy="joined")  # noqa: F821

    @property
    def product_name(self) -> str | None:
        return self.product.display_name if self.product is not None else None

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PortalEnquiry {self.id} {self.inquiry_type} -> inquiry {self.inquiry_id}>"
