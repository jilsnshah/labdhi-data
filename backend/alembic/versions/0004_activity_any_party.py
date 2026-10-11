"""Activities hang off any party, and a visit may carry a text-only address.

Revision ID: 0004_activity_party
Revises: 0003_prospects
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_activity_party"
down_revision: str | None = "0003_prospects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # customer_id -> party_id: the column always pointed at parties.id, and
    # suppliers/transporters now get activities too.
    op.alter_column("activities", "customer_id", new_column_name="party_id")
    op.execute(
        "ALTER TABLE activities RENAME CONSTRAINT activities_customer_id_fkey "
        "TO activities_party_id_fkey"
    )
    op.execute("ALTER INDEX ix_activities_customer_id RENAME TO ix_activities_party_id")
    op.execute("ALTER INDEX ix_activities_customer_status RENAME TO ix_activities_party_status")
    op.execute(
        "ALTER INDEX ix_activities_customer_scheduled_at "
        "RENAME TO ix_activities_party_scheduled_at"
    )

    # A visit needs somewhere to go, but "his shop, Gondal Road" is a valid
    # answer: accept a snapshot-only address.
    op.drop_constraint("ck_activities_visit_requires_location", "activities", type_="check")
    op.execute(
        "ALTER TABLE activities ADD CONSTRAINT ck_activities_visit_requires_location "
        "CHECK ((activity_type <> 'VISIT') OR (location_id IS NOT NULL) "
        "OR (location_snapshot IS NOT NULL)) NOT VALID"
    )


def downgrade() -> None:
    op.drop_constraint("ck_activities_visit_requires_location", "activities", type_="check")
    # Text-only visits cannot satisfy the stricter rule; give them no location
    # requirement rather than deleting field history.
    op.execute(
        "ALTER TABLE activities ADD CONSTRAINT ck_activities_visit_requires_location "
        "CHECK ((activity_type <> 'VISIT') OR (location_id IS NOT NULL)) NOT VALID"
    )
    op.execute(
        "ALTER INDEX ix_activities_party_scheduled_at "
        "RENAME TO ix_activities_customer_scheduled_at"
    )
    op.execute("ALTER INDEX ix_activities_party_status RENAME TO ix_activities_customer_status")
    op.execute("ALTER INDEX ix_activities_party_id RENAME TO ix_activities_customer_id")
    op.execute(
        "ALTER TABLE activities RENAME CONSTRAINT activities_party_id_fkey "
        "TO activities_customer_id_fkey"
    )
    op.alter_column("activities", "party_id", new_column_name="customer_id")
