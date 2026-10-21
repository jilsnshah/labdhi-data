"""Record what happened when we WhatsApped a participant their bid link.

Nullable throughout: a participant invited before this existed simply has no
record of being told, which is the truth.

Revision ID: 0010_bid_notifications
Revises: 0009_bids
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_bid_notifications"
down_revision: str | None = "0009_bids"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = ("PENDING", "SKIPPED", "SENT", "DELIVERED", "READ", "FAILED")


def upgrade() -> None:
    op.add_column(
        "bid_participants", sa.Column("notify_status", sa.String(length=32), nullable=True)
    )
    op.add_column("bid_participants", sa.Column("notify_error", sa.Text(), nullable=True))
    op.add_column(
        "bid_participants", sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "bid_participants", sa.Column("notify_message_id", sa.String(length=80), nullable=True)
    )
    op.create_check_constraint(
        "ck_bid_participants_notify_status_allowed",
        "bid_participants",
        sa.text("notify_status IS NULL OR notify_status IN " + str(STATUSES)),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_bid_participants_notify_status_allowed", "bid_participants", type_="check"
    )
    op.drop_column("bid_participants", "notify_message_id")
    op.drop_column("bid_participants", "notified_at")
    op.drop_column("bid_participants", "notify_error")
    op.drop_column("bid_participants", "notify_status")
