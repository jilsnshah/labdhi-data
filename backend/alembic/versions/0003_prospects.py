"""Unknown parties: prospect stage, dedupe keys, merge support.

Revision ID: 0003_prospects
Revises: 0002_salesperson
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_prospects"
down_revision: str | None = "0002_salesperson"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STAGES = ("PROSPECT", "ACTIVE", "MERGED")
SOURCES = ("DESK", "QUICK_CREATE", "IMPORT", "FIELD")


def upgrade() -> None:
    # Trigram search powers the "did you mean this party?" duplicate check.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.add_column(
        "parties",
        sa.Column(
            "stage",
            sa.Enum(*STAGES, name="party_stage", native_enum=False, length=32),
            nullable=False,
            server_default="ACTIVE",
        ),
    )
    op.add_column(
        "parties",
        sa.Column(
            "source",
            sa.Enum(*SOURCES, name="party_source", native_enum=False, length=32),
            nullable=False,
            server_default="DESK",
        ),
    )
    op.add_column("parties", sa.Column("phone_normalized", sa.String(length=20), nullable=True))
    op.add_column("parties", sa.Column("merged_into_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "parties_merged_into_id_fkey",
        "parties",
        "parties",
        ["merged_into_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Dedupe key for existing rows: digits only, last 10 (Indian numbers).
    op.execute(
        """
        UPDATE parties
           SET phone_normalized = NULLIF(
                   right(regexp_replace(phone, '\\D', '', 'g'), 10), '')
         WHERE phone IS NOT NULL
        """
    )

    # Verified parties keep a unique name per type; two different walk-ins may
    # legitimately both be called "Patel Traders".
    op.drop_constraint("uq_parties_type_name", "parties", type_="unique")
    op.create_index(
        "uq_parties_type_name_known",
        "parties",
        ["party_type", "name"],
        unique=True,
        postgresql_where=sa.text("stage <> 'PROSPECT'"),
    )
    op.create_index("ix_parties_stage", "parties", ["stage"], unique=False)
    op.create_index("ix_parties_type_stage", "parties", ["party_type", "stage"], unique=False)
    op.create_index(
        "ix_parties_phone_normalized", "parties", ["phone_normalized"], unique=False
    )
    op.execute(
        "CREATE INDEX ix_parties_name_trgm ON parties USING gin (name gin_trgm_ops)"
    )

    allowed_stages = ", ".join(f"'{value}'" for value in STAGES)
    allowed_sources = ", ".join(f"'{value}'" for value in SOURCES)
    op.create_check_constraint(
        "ck_parties_stage_allowed", "parties", f"stage IN ({allowed_stages})"
    )
    op.create_check_constraint(
        "ck_parties_source_allowed", "parties", f"source IN ({allowed_sources})"
    )
    # A merged row points somewhere; a live row does not.
    op.create_check_constraint(
        "ck_parties_merged_has_target",
        "parties",
        "(stage <> 'MERGED') OR (merged_into_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_parties_merged_has_target", "parties", type_="check")
    op.drop_constraint("ck_parties_source_allowed", "parties", type_="check")
    op.drop_constraint("ck_parties_stage_allowed", "parties", type_="check")
    op.execute("DROP INDEX IF EXISTS ix_parties_name_trgm")
    op.drop_index("ix_parties_phone_normalized", table_name="parties")
    op.drop_index("ix_parties_type_stage", table_name="parties")
    op.drop_index("ix_parties_stage", table_name="parties")
    op.drop_index("uq_parties_type_name_known", table_name="parties")
    # Reinstating the hard unique constraint requires prospect duplicates to be
    # gone; merged rows are retired first so their names stop colliding.
    op.execute("UPDATE parties SET name = name || ' (merged ' || id || ')' WHERE stage = 'MERGED'")
    op.create_unique_constraint("uq_parties_type_name", "parties", ["party_type", "name"])
    op.drop_constraint("parties_merged_into_id_fkey", "parties", type_="foreignkey")
    op.drop_column("parties", "merged_into_id")
    op.drop_column("parties", "phone_normalized")
    op.drop_column("parties", "source")
    op.drop_column("parties", "stage")
