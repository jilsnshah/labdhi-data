"""Bids: one lot, several parties quoting against each other.

Independent of inquiries: its own tables, its own history. Parties gain an
opaque portal code so a public bid link never carries a row id.

Revision ID: 0009_bids
Revises: 0008_location_area
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_bids"
down_revision: str | None = "0008_location_area"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BID_TYPES = ("CUSTOMER", "SUPPLIER", "TRANSPORT")
BID_STATUSES = ("DRAFT", "OPEN", "CLOSED")
UNITS = ("MT", "KG", "BAG", "LITRE", "PIECE")


def upgrade() -> None:
    op.add_column("parties", sa.Column("portal_code", sa.String(length=32), nullable=True))
    op.create_unique_constraint("uq_parties_portal_code", "parties", ["portal_code"])

    op.create_table(
        "bids",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bid_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="MT"),
        sa.Column(
            "pickup_location_id",
            sa.Integer(),
            sa.ForeignKey("locations.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "delivery_location_id",
            sa.Integer(),
            sa.ForeignKey("locations.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("specifications", sa.Text(), nullable=True),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "closed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
        ),
        sa.Column("no_winner", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("winner_quote_id", sa.Integer(), nullable=True),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "awarded_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("quantity > 0", name="ck_bids_quantity_positive"),
        sa.CheckConstraint(
            "(bid_type = 'TRANSPORT') OR (product_id IS NOT NULL)",
            name="ck_bids_product_required",
        ),
        sa.CheckConstraint(
            "(bid_type <> 'TRANSPORT') OR "
            "(pickup_location_id IS NOT NULL AND delivery_location_id IS NOT NULL)",
            name="ck_bids_transport_has_route",
        ),
        sa.CheckConstraint(
            "(bid_type <> 'TRANSPORT') OR (pickup_location_id <> delivery_location_id)",
            name="ck_bids_transport_route_distinct",
        ),
        sa.CheckConstraint(
            "(status <> 'CLOSED') OR (closed_at IS NOT NULL)",
            name="ck_bids_closed_has_timestamp",
        ),
        sa.CheckConstraint(
            "(status = 'OPEN') OR (published_at IS NOT NULL) OR (status = 'DRAFT')",
            name="ck_bids_open_has_published",
        ),
        sa.CheckConstraint(
            "bid_type IN " + str(BID_TYPES),
            name="ck_bids_bid_type_allowed",
        ),
        sa.CheckConstraint("status IN " + str(BID_STATUSES), name="ck_bids_status_allowed"),
        sa.CheckConstraint("unit IN " + str(UNITS), name="ck_bids_unit_allowed"),
    )
    op.create_index("ix_bids_bid_type", "bids", ["bid_type"])
    op.create_index("ix_bids_status", "bids", ["status"])
    op.create_index("ix_bids_product_id", "bids", ["product_id"])
    op.create_index("ix_bids_created_by", "bids", ["created_by"])
    op.create_index("ix_bids_type_status", "bids", ["bid_type", "status"])
    op.create_index("ix_bids_status_created_at", "bids", ["status", "created_at"])

    op.create_table(
        "bid_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bid_id", sa.Integer(), sa.ForeignKey("bids.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "party_id",
            sa.Integer(),
            sa.ForeignKey("parties.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("first_opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("bid_id", "party_id", name="uq_bid_participants_bid_party"),
    )
    op.create_index("ix_bid_participants_bid_id", "bid_participants", ["bid_id"])
    op.create_index("ix_bid_participants_party_id", "bid_participants", ["party_id"])

    op.create_table(
        "bid_quotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "participant_id",
            sa.Integer(),
            sa.ForeignKey("bid_participants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("participant_id", name="uq_bid_quotes_participant"),
        sa.CheckConstraint("price > 0", name="ck_bid_quotes_price_positive"),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0", name="ck_bid_quotes_quantity_positive"
        ),
    )

    # Added after bid_quotes exists: the two tables point at each other.
    op.create_foreign_key(
        "fk_bids_winner_quote_id",
        "bids",
        "bid_quotes",
        ["winner_quote_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_bids_winner_quote_id", "bids", type_="foreignkey")
    op.drop_table("bid_quotes")
    op.drop_table("bid_participants")
    op.drop_table("bids")
    op.drop_constraint("uq_parties_portal_code", "parties", type_="unique")
    op.drop_column("parties", "portal_code")
