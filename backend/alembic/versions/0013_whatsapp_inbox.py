"""Messages people send to the desk's WhatsApp number.

One row per message. ``wa_message_id`` is unique because Meta retries a webhook
until it gets a 200, so the same message arrives again after any blip; the
constraint is what makes a retry harmless rather than a duplicate.

Revision ID: 0013_whatsapp_inbox
Revises: 0012_enquiries_become_inquiries
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013_whatsapp_inbox"
down_revision: str | None = "0012_enquiries_become_inquiries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wa_message_id", sa.String(length=128), nullable=False),
        sa.Column("from_number", sa.String(length=32), nullable=False),
        sa.Column("phone_number_id", sa.String(length=32), nullable=True),
        sa.Column("profile_name", sa.String(length=120), nullable=True),
        sa.Column("message_type", sa.String(length=32), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "party_id", sa.Integer(), sa.ForeignKey("parties.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("raw", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint("wa_message_id", name="uq_whatsapp_messages_wa_message_id"),
    )
    op.create_index("ix_whatsapp_messages_from_number", "whatsapp_messages", ["from_number"])
    op.create_index("ix_whatsapp_messages_message_type", "whatsapp_messages", ["message_type"])
    op.create_index("ix_whatsapp_messages_party_id", "whatsapp_messages", ["party_id"])
    op.create_index(
        "ix_whatsapp_messages_from_received", "whatsapp_messages", ["from_number", "received_at"]
    )


def downgrade() -> None:
    op.drop_table("whatsapp_messages")
