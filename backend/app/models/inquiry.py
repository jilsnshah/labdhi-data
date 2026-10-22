"""Inquiries: one common header + a type specific detail row carrying the quote.

An inquiry records a quotation directly: who, what, how much, where, and the
rate. There is no separate request / response log - the rate lives on the row,
and edits to it are captured by the audit log like any other change.

Historical columns from the earlier request-and-response workflow (closure
reasons, target prices, required dates, notes, supplier-to-customer links) and
the ``inquiry_responses`` table are kept in the database for the record but are
no longer mapped here. See migration ``0007_simplified_inquiries``.
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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    InquirySource,
    InquiryStatus,
    InquiryType,
    QuantityUnit,
    inquiry_source_enum,
    inquiry_status_enum,
    inquiry_type_enum,
    quantity_unit_enum,
)

QTY = Numeric(14, 3)
MONEY = Numeric(14, 2)


class Inquiry(Base, TimestampMixin):
    """Common inquiry header shared by customer / supplier / transport inquiries."""

    __tablename__ = "inquiries"
    __table_args__ = (
        CheckConstraint(
            "(status <> 'CLOSED') OR (closed_at IS NOT NULL)",
            name="ck_inquiries_closed_has_timestamp",
        ),
        Index("ix_inquiries_type_status", "inquiry_type", "status"),
        Index("ix_inquiries_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inquiry_type: Mapped[InquiryType] = mapped_column(inquiry_type_enum, nullable=False, index=True)
    status: Mapped[InquiryStatus] = mapped_column(
        inquiry_status_enum,
        nullable=False,
        default=InquiryStatus.ACTIVE,
        server_default=InquiryStatus.ACTIVE.value,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(200))
    #: Who put it on the book. PORTAL means the party sent it in themselves.
    source: Mapped[InquirySource] = mapped_column(
        inquiry_source_enum,
        nullable=False,
        default=InquirySource.DESK,
        server_default=InquirySource.DESK.value,
        index=True,
    )
    #: The salesperson behind it - null for one a party raised themselves,
    #: because there is nobody to name and borrowing a name would be a lie.
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))

    creator: Mapped[User | None] = relationship(  # noqa: F821
        foreign_keys=[created_by], lazy="joined"
    )
    closer: Mapped[User | None] = relationship(  # noqa: F821
        foreign_keys=[closed_by], lazy="joined"
    )

    customer_detail: Mapped[CustomerInquiry | None] = relationship(
        back_populates="inquiry",
        cascade="all, delete-orphan",
        uselist=False,
        passive_deletes=True,
    )
    supplier_detail: Mapped[SupplierInquiry | None] = relationship(
        back_populates="inquiry",
        cascade="all, delete-orphan",
        uselist=False,
        passive_deletes=True,
    )
    transport_detail: Mapped[TransportInquiry | None] = relationship(
        back_populates="inquiry",
        cascade="all, delete-orphan",
        uselist=False,
        passive_deletes=True,
    )

    @property
    def is_active(self) -> bool:
        return self.status == InquiryStatus.ACTIVE

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Inquiry {self.id} {self.inquiry_type} {self.status}>"


class CustomerInquiry(Base):
    """'ABC Pipes: 20 MT Reliance PVC K-67, delivered Rajkot, at ₹91.50/kg.'"""

    __tablename__ = "customer_inquiries"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_customer_inquiries_quantity_positive"),
        CheckConstraint("rate IS NULL OR rate > 0", name="ck_customer_inquiries_rate_positive"),
        Index("ix_customer_inquiries_customer_product", "customer_id", "product_id"),
    )

    inquiry_id: Mapped[int] = mapped_column(
        ForeignKey("inquiries.id", ondelete="CASCADE"), primary_key=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    unit: Mapped[QuantityUnit] = mapped_column(
        quantity_unit_enum, nullable=False, server_default=QuantityUnit.MT.value
    )
    #: Any Master Data location - deliberately not restricted to the customer's own.
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    #: Quoted rate in rupees per kilogram.
    rate: Mapped[Decimal | None] = mapped_column(MONEY)

    inquiry: Mapped[Inquiry] = relationship(back_populates="customer_detail")
    customer: Mapped[Party] = relationship(lazy="joined")  # noqa: F821
    product: Mapped[Product] = relationship(lazy="joined")  # noqa: F821
    location: Mapped[Location | None] = relationship(lazy="joined")  # noqa: F821


class SupplierInquiry(Base):
    """'Mahavir Polymers: 25 MT Reliance PVC K-67, ex-Ahmedabad, at ₹90.80/kg.'"""

    __tablename__ = "supplier_inquiries"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_supplier_inquiries_quantity_positive"),
        CheckConstraint("rate IS NULL OR rate > 0", name="ck_supplier_inquiries_rate_positive"),
        Index("ix_supplier_inquiries_supplier_product", "supplier_id", "product_id"),
    )

    inquiry_id: Mapped[int] = mapped_column(
        ForeignKey("inquiries.id", ondelete="CASCADE"), primary_key=True
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    unit: Mapped[QuantityUnit] = mapped_column(
        quantity_unit_enum, nullable=False, server_default=QuantityUnit.MT.value
    )
    #: Any Master Data location - deliberately not restricted to the supplier's own.
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    #: Quoted rate in rupees per kilogram.
    rate: Mapped[Decimal | None] = mapped_column(MONEY)

    inquiry: Mapped[Inquiry] = relationship(back_populates="supplier_detail")
    supplier: Mapped[Party] = relationship(lazy="joined")  # noqa: F821
    product: Mapped[Product] = relationship(lazy="joined")  # noqa: F821
    location: Mapped[Location | None] = relationship(lazy="joined")  # noqa: F821


class TransportInquiry(Base):
    """'Jay Transport: 20 MT Ahmedabad -> Rajkot for ₹18,000.'"""

    __tablename__ = "transport_inquiries"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_transport_inquiries_quantity_positive"),
        CheckConstraint(
            "pickup_location_id <> delivery_location_id",
            name="ck_transport_inquiries_distinct_locations",
        ),
        CheckConstraint("price IS NULL OR price > 0", name="ck_transport_inquiries_price_positive"),
        Index("ix_transport_inquiries_route", "pickup_location_id", "delivery_location_id"),
    )

    inquiry_id: Mapped[int] = mapped_column(
        ForeignKey("inquiries.id", ondelete="CASCADE"), primary_key=True
    )
    transporter_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    unit: Mapped[QuantityUnit] = mapped_column(
        quantity_unit_enum, nullable=False, server_default=QuantityUnit.MT.value
    )
    pickup_location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False
    )
    delivery_location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False
    )
    #: Quoted transport amount in rupees.
    price: Mapped[Decimal | None] = mapped_column(MONEY)

    inquiry: Mapped[Inquiry] = relationship(back_populates="transport_detail")
    transporter: Mapped[Party] = relationship(lazy="joined")  # noqa: F821
    pickup_location: Mapped[Location] = relationship(  # noqa: F821
        lazy="joined", foreign_keys=[pickup_location_id]
    )
    delivery_location: Mapped[Location] = relationship(  # noqa: F821
        lazy="joined", foreign_keys=[delivery_location_id]
    )
