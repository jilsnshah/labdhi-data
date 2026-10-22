"""Enquiries that parties send in themselves, through their portal link.

These are deliberately *not* inquiries. An inquiry is the desk's own record:
every field points at master data, the rate is one the desk stands behind, and
a salesperson's name is on it. What arrives through a public link is none of
those things - it is a customer saying "I want about 20 tonnes of K-67 in
Rajkot, what's your rate", typed on a phone, possibly naming a grade we do not
carry.

So it lands here first, in its own table, with the party's own words kept as
they were written. The desk reads it, maps it onto a real product and location,
and accepts it; accepting creates the inquiry and this row records which one.
Declining leaves the words on the record too. Nothing a stranger types can put
a row in the book, and nothing is thrown away.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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
    PortalEnquiryStatus,
    QuantityUnit,
    inquiry_type_enum,
    portal_enquiry_status_enum,
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
        # A load needs no product; anything bought or sold does, even if all we
        # have is the name the party typed.
        CheckConstraint(
            "inquiry_type = 'TRANSPORT' OR product_id IS NOT NULL OR product_text IS NOT NULL",
            name="ck_portal_enquiries_product_named",
        ),
        # Still NEW means nobody has touched it; anything else was decided by
        # somebody, at some time.
        CheckConstraint(
            "status = 'NEW' OR (handled_at IS NOT NULL AND handled_by IS NOT NULL)",
            name="ck_portal_enquiries_handled_is_recorded",
        ),
        # Accepted means there is an inquiry to point at.
        CheckConstraint(
            "status <> 'ACCEPTED' OR inquiry_id IS NOT NULL",
            name="ck_portal_enquiries_accepted_has_inquiry",
        ),
        Index("ix_portal_enquiries_status_created_at", "status", "created_at"),
        Index("ix_portal_enquiries_party_status", "party_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    #: Who sent it, resolved from the portal code - never taken from the form.
    party_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    #: Decided by what the party is, not by what they say they want.
    inquiry_type: Mapped[InquiryType] = mapped_column(inquiry_type_enum, nullable=False, index=True)

    #: The grade they picked from the list, when they found it there.
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    #: What they typed when they did not. Kept exactly as written.
    product_text: Mapped[str | None] = mapped_column(String(200))

    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    unit: Mapped[QuantityUnit] = mapped_column(
        quantity_unit_enum, nullable=False, server_default=QuantityUnit.MT.value
    )

    #: Places as plain text, because a party cannot be asked to know our
    #: location master. A supplier fills in where it ships from, a customer
    #: where they want it, a transporter both.
    from_place: Mapped[str | None] = mapped_column(String(200))
    to_place: Mapped[str | None] = mapped_column(String(200))

    #: The rate they are asking for or offering: per kilogram for a product,
    #: the whole freight for a load. Optional - plenty of enquiries are only
    #: "what's your price".
    rate: Mapped[Decimal | None] = mapped_column(MONEY)
    notes: Mapped[str | None] = mapped_column(Text())

    status: Mapped[PortalEnquiryStatus] = mapped_column(
        portal_enquiry_status_enum,
        nullable=False,
        default=PortalEnquiryStatus.NEW,
        server_default=PortalEnquiryStatus.NEW.value,
        index=True,
    )
    #: The inquiry this became, once the desk accepted it.
    inquiry_id: Mapped[int | None] = mapped_column(
        ForeignKey("inquiries.id", ondelete="SET NULL"), index=True
    )
    handled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    party: Mapped[Party] = relationship(lazy="joined")  # noqa: F821
    product: Mapped[Product | None] = relationship(lazy="joined")  # noqa: F821
    inquiry: Mapped[Inquiry | None] = relationship(lazy="joined")  # noqa: F821
    handler: Mapped[User | None] = relationship(  # noqa: F821
        foreign_keys=[handled_by], lazy="joined"
    )

    @property
    def product_name(self) -> str | None:
        """What to show for the grade: ours if they picked it, theirs if not."""
        if self.product is not None:
            return self.product.display_name
        return self.product_text

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PortalEnquiry {self.id} {self.inquiry_type} {self.status}>"
