"""Only ACTIVE parties own the unique-name namespace.

A merged duplicate kept its name reserved, which blocked promoting the very party
it had been folded into.

Revision ID: 0005_name_namespace
Revises: 0004_activity_party
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_name_namespace"
down_revision: str | None = "0004_activity_party"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("uq_parties_type_name_known", table_name="parties")
    op.create_index(
        "uq_parties_type_name_known",
        "parties",
        ["party_type", "name"],
        unique=True,
        postgresql_where=sa.text("stage = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index("uq_parties_type_name_known", table_name="parties")
    # The older predicate let merged rows reserve a name, so a duplicate that was
    # folded into a now-ACTIVE survivor would collide. Retire those names first.
    op.execute(
        """
        UPDATE parties p
           SET name = p.name || ' (merged ' || p.id || ')'
         WHERE p.stage = 'MERGED'
           AND EXISTS (
                 SELECT 1 FROM parties other
                  WHERE other.id <> p.id
                    AND other.party_type = p.party_type
                    AND lower(other.name) = lower(p.name)
                    AND other.stage <> 'PROSPECT'
               )
        """
    )
    op.create_index(
        "uq_parties_type_name_known",
        "parties",
        ["party_type", "name"],
        unique=True,
        postgresql_where=sa.text("stage <> 'PROSPECT'"),
    )
