"""Enquiries parties send in themselves, through their portal link.

Its own table, not the inquiries one: what a party types into a public form is
a request in their own words, and only becomes an inquiry when the desk accepts
it and maps it onto master data. ``inquiry_id`` then says which one it became.

Revision ID: 0011_portal_enquiries
Revises: 0010_bid_notifications
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_portal_enquiries"
down_revision: str | None = "0010_bid_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TYPES = ("CUSTOMER", "SUPPLIER", "TRANSPORT")
STATUSES = ("NEW", "ACCEPTED", "DECLINED")
UNITS = ("MT", "KG", "BAG", "LITRE", "PIECE")


def upgrade() -> None:
    op.create_table(
        "portal_enquiries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "party_id",
            sa.Integer(),
            sa.ForeignKey("parties.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("inquiry_type", sa.String(length=32), nullable=False),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("product_text", sa.String(length=200), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="MT"),
        sa.Column("from_place", sa.String(length=200), nullable=True),
        sa.Column("to_place", sa.String(length=200), nullable=True),
        sa.Column("rate", sa.Numeric(14, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="NEW"),
        sa.Column(
            "inquiry_id",
            sa.Integer(),
            sa.ForeignKey("inquiries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "handled_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
        ),
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "inquiry_type IN " + str(TYPES), name="ck_portal_enquiries_inquiry_type"
        ),
        sa.CheckConstraint("status IN " + str(STATUSES), name="ck_portal_enquiries_status"),
        sa.CheckConstraint("unit IN " + str(UNITS), name="ck_portal_enquiries_unit"),
        sa.CheckConstraint("quantity > 0", name="ck_portal_enquiries_quantity_positive"),
        sa.CheckConstraint("rate IS NULL OR rate > 0", name="ck_portal_enquiries_rate_positive"),
        sa.CheckConstraint(
            "inquiry_type = 'TRANSPORT' OR product_id IS NOT NULL OR product_text IS NOT NULL",
            name="ck_portal_enquiries_product_named",
        ),
        sa.CheckConstraint(
            "status = 'NEW' OR (handled_at IS NOT NULL AND handled_by IS NOT NULL)",
            name="ck_portal_enquiries_handled_is_recorded",
        ),
        sa.CheckConstraint(
            "status <> 'ACCEPTED' OR inquiry_id IS NOT NULL",
            name="ck_portal_enquiries_accepted_has_inquiry",
        ),
    )
    op.create_index("ix_portal_enquiries_party_id", "portal_enquiries", ["party_id"])
    op.create_index("ix_portal_enquiries_product_id", "portal_enquiries", ["product_id"])
    op.create_index("ix_portal_enquiries_inquiry_id", "portal_enquiries", ["inquiry_id"])
    op.create_index("ix_portal_enquiries_inquiry_type", "portal_enquiries", ["inquiry_type"])
    op.create_index("ix_portal_enquiries_status", "portal_enquiries", ["status"])
    op.create_index(
        "ix_portal_enquiries_status_created_at", "portal_enquiries", ["status", "created_at"]
    )
    op.create_index("ix_portal_enquiries_party_status", "portal_enquiries", ["party_id", "status"])


def downgrade() -> None:
    op.drop_table("portal_enquiries")
