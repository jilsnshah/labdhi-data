"""Parties declare the end-uses they work in, not just products they have traded.

A product link records what a party has actually bought or sold through us. An
application link records what business they are in -- pipes, windows, raffia.
A new extruder has no product history, but "deals in PVC Pipes" is precisely
the fact that makes them worth calling on a pipes grade.

Revision ID: 0006_party_applications
Revises: 0005_name_namespace
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_party_applications"
down_revision: str | None = "0005_name_namespace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "party_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "party_id",
            sa.Integer(),
            sa.ForeignKey("parties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "application_id",
            sa.Integer(),
            # RESTRICT: an application in use by a party must not vanish from
            # under it; master data is deactivated, never deleted.
            sa.ForeignKey("applications.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "party_id", "application_id", name="uq_party_applications_unique_link"
        ),
    )
    op.create_index(
        "ix_party_applications_party_id", "party_applications", ["party_id"]
    )
    op.create_index(
        "ix_party_applications_application_id", "party_applications", ["application_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_party_applications_application_id", table_name="party_applications")
    op.drop_index("ix_party_applications_party_id", table_name="party_applications")
    op.drop_table("party_applications")
