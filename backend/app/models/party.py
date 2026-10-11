"""Parties (customer / supplier / transporter), locations and party-product links."""

from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    LocationType,
    PartyProductRelationship,
    PartySource,
    PartyStage,
    PartyType,
    location_type_enum,
    party_product_rel_enum,
    party_source_enum,
    party_stage_enum,
    party_type_enum,
)
from app.models.mixins import StatusMixin

#: Phone shape the duplicate check keys on: digits only, last 10 (Indian numbers).
_PHONE_DIGITS = re.compile(r"\D+")


def normalize_phone(value: str | None) -> str | None:
    """Digits-only phone used for duplicate detection (never for display)."""
    if not value:
        return None
    digits = _PHONE_DIGITS.sub("", value)
    if not digits:
        return None
    return digits[-10:] if len(digits) > 10 else digits


class Party(Base, TimestampMixin, StatusMixin):
    """One table for all three party types - keeps the model extensible."""

    __tablename__ = "parties"
    __table_args__ = (
        UniqueConstraint("gst_number", name="uq_parties_gst_number"),
        # Only verified parties own the unique-name namespace: two different
        # walk-ins may both be called "Patel Traders", and a merged duplicate
        # must not block its own survivor from being promoted.
        Index(
            "uq_parties_type_name_known",
            "party_type",
            "name",
            unique=True,
            postgresql_where=text("stage = 'ACTIVE'"),
        ),
        Index("ix_parties_type_status", "party_type", "status"),
        Index("ix_parties_type_name", "party_type", "name"),
        Index("ix_parties_type_stage", "party_type", "stage"),
        # Dedupe key: digits-only phone. Not unique - a warning, never a block.
        Index("ix_parties_phone_normalized", "phone_normalized"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    party_type: Mapped[PartyType] = mapped_column(party_type_enum, nullable=False, index=True)
    contact_person: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    gst_number: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text())
    stage: Mapped[PartyStage] = mapped_column(
        party_stage_enum,
        nullable=False,
        default=PartyStage.ACTIVE,
        server_default=PartyStage.ACTIVE.value,
        index=True,
    )
    source: Mapped[PartySource] = mapped_column(
        party_source_enum,
        nullable=False,
        default=PartySource.DESK,
        server_default=PartySource.DESK.value,
    )
    #: Digits-only phone, maintained by the service layer for duplicate detection.
    phone_normalized: Mapped[str | None] = mapped_column(String(20))
    #: Set when this row was folded into another party.
    merged_into_id: Mapped[int | None] = mapped_column(
        ForeignKey("parties.id", ondelete="SET NULL")
    )

    merged_into: Mapped[Party | None] = relationship(remote_side=[id], lazy="joined")

    locations: Mapped[list[PartyLocation]] = relationship(
        back_populates="party", cascade="all, delete-orphan", passive_deletes=True
    )
    products: Mapped[list[PartyProduct]] = relationship(
        back_populates="party", cascade="all, delete-orphan", passive_deletes=True
    )
    applications: Mapped[list[PartyApplication]] = relationship(
        back_populates="party", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Party {self.id} {self.party_type} {self.name}>"


@event.listens_for(Party, "before_insert")
@event.listens_for(Party, "before_update")
def _sync_phone_normalized(_mapper, _connection, target: Party) -> None:
    """Keep the dedupe key in step with the phone, whoever wrote the row.

    Doing this in the mapper rather than the service means a seed script, an
    importer or a future endpoint cannot forget it and quietly break duplicate
    detection.
    """
    target.phone_normalized = normalize_phone(target.phone)


class Location(Base, TimestampMixin, StatusMixin):
    """Independent address entity - shared by parties, transport inquiries, future jobs."""

    __tablename__ = "locations"
    __table_args__ = (Index("ix_locations_city_state", "city", "state"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str | None] = mapped_column(String(120))
    address_line_1: Mapped[str | None] = mapped_column(String(200))
    address_line_2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    state: Mapped[str | None] = mapped_column(String(120), index=True)
    country: Mapped[str] = mapped_column(String(120), nullable=False, server_default="India")
    pincode: Mapped[str | None] = mapped_column(String(12))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))

    @property
    def display_name(self) -> str:
        parts = [self.label, self.city, self.state]
        return " - ".join(p for p in parts if p)


class PartyLocation(Base, TimestampMixin):
    """A party can have a head office, a factory and several delivery points."""

    __tablename__ = "party_locations"
    __table_args__ = (
        UniqueConstraint("party_id", "location_id", name="uq_party_locations_party_location"),
        Index(
            "uq_party_locations_one_primary",
            "party_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
        Index("ix_party_locations_location_id", "location_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    party_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False
    )
    location_type: Mapped[LocationType] = mapped_column(
        location_type_enum, nullable=False, server_default=LocationType.OTHER.value
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    party: Mapped[Party] = relationship(back_populates="locations")
    location: Mapped[Location] = relationship(lazy="joined")


class PartyProduct(Base, TimestampMixin):
    """Which products a party supplies / purchases / is interested in."""

    __tablename__ = "party_products"
    __table_args__ = (
        UniqueConstraint(
            "party_id", "product_id", "relationship_type", name="uq_party_products_unique_link"
        ),
        Index("ix_party_products_product_rel", "product_id", "relationship_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    party_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    relationship_type: Mapped[PartyProductRelationship] = mapped_column(
        party_product_rel_enum, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text())
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    party: Mapped[Party] = relationship(back_populates="products")
    product: Mapped[Product] = relationship(lazy="joined")  # noqa: F821


class PartyApplication(Base, TimestampMixin):
    """Which end-uses a party works in: pipes, windows, raffia, cable.

    Separate from :class:`PartyProduct` on purpose. A party's product list says
    what they have traded with us; their application list says what business
    they are in. A new pipe extruder has no product history at all, but "deals
    in PVC Pipes" is exactly the fact that makes them worth a call on a pipes
    grade -- so the two answer different questions and both have to exist.
    """

    __tablename__ = "party_applications"
    # No explicit Index here: both columns already carry index=True, and
    # SQLAlchemy's auto-generated name collides with a hand-declared one.
    __table_args__ = (
        UniqueConstraint("party_id", "application_id", name="uq_party_applications_unique_link"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    party_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text())
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    party: Mapped[Party] = relationship(back_populates="applications")
    application: Mapped[Application] = relationship(lazy="joined")  # noqa: F821
