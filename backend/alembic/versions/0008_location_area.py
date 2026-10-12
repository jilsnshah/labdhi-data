"""Locations get an area: the locality within a city that traders filter by.

Nullable, so every existing location stays valid; areas are filled in as the
desk edits locations.

Revision ID: 0008_location_area
Revises: 0007_simplified_inquiries
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_location_area"
down_revision: str | None = "0007_simplified_inquiries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("locations", sa.Column("area", sa.String(length=120), nullable=True))
    op.create_index("ix_locations_area", "locations", ["area"])


def downgrade() -> None:
    op.drop_index("ix_locations_area", table_name="locations")
    op.drop_column("locations", "area")
