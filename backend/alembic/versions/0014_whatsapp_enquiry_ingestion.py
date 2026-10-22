"""Reading an inbound WhatsApp message, and what comes of it.

A message is recorded by the webhook and read afterwards, so each row carries
how far it has got. Only PENDING rows are ever picked up, which is what stops a
webhook Meta delivers twice from producing two enquiries.

A party can now be introduced by WhatsApp, and an inquiry can have been read out
of one, so both source lists gain a value.

Revision ID: 0014_whatsapp_enquiry_ingestion
Revises: 0013_whatsapp_inbox
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014_whatsapp_enquiry_ingestion"
down_revision: str | None = "0013_whatsapp_inbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROCESSING = ("PENDING", "IGNORED", "PROCESSED", "SKIPPED", "FAILED")
PARTY_SOURCES = ("DESK", "QUICK_CREATE", "IMPORT", "FIELD", "WHATSAPP")
INQUIRY_SOURCES = ("DESK", "PORTAL", "WHATSAPP")


def upgrade() -> None:
    op.add_column(
        "whatsapp_messages",
        sa.Column(
            "processing_status", sa.String(length=32), nullable=False, server_default="PENDING"
        ),
    )
    op.add_column(
        "whatsapp_messages", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "whatsapp_messages", sa.Column("processing_note", sa.String(length=300), nullable=True)
    )
    op.add_column(
        "whatsapp_messages",
        sa.Column(
            "inquiry_id",
            sa.Integer(),
            sa.ForeignKey("inquiries.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_whatsapp_messages_processing_status",
        "whatsapp_messages",
        sa.text("processing_status IN " + str(PROCESSING)),
    )
    op.create_index(
        "ix_whatsapp_messages_processing_status", "whatsapp_messages", ["processing_status"]
    )
    op.create_index("ix_whatsapp_messages_inquiry_id", "whatsapp_messages", ["inquiry_id"])

    # Both source lists gain WHATSAPP. The constraint is dropped and rebuilt
    # because that is the only way to widen a CHECK.
    op.drop_constraint("ck_parties_source_allowed", "parties", type_="check")
    op.create_check_constraint(
        "ck_parties_source_allowed", "parties", sa.text("source IN " + str(PARTY_SOURCES))
    )
    op.drop_constraint("ck_inquiries_source", "inquiries", type_="check")
    op.create_check_constraint(
        "ck_inquiries_source", "inquiries", sa.text("source IN " + str(INQUIRY_SOURCES))
    )


def downgrade() -> None:
    # Anything introduced or raised by WhatsApp has to be called something the
    # old lists allow. QUICK_CREATE and PORTAL are the nearest true statements:
    # somebody outside the desk caused the row to exist.
    op.execute("UPDATE parties SET source = 'QUICK_CREATE' WHERE source = 'WHATSAPP'")
    op.execute("UPDATE inquiries SET source = 'PORTAL' WHERE source = 'WHATSAPP'")
    op.drop_constraint("ck_inquiries_source", "inquiries", type_="check")
    op.create_check_constraint(
        "ck_inquiries_source", "inquiries", sa.text("source IN ('DESK', 'PORTAL')")
    )
    op.drop_constraint("ck_parties_source_allowed", "parties", type_="check")
    op.create_check_constraint(
        "ck_parties_source_allowed",
        "parties",
        sa.text("source IN ('DESK', 'QUICK_CREATE', 'IMPORT', 'FIELD')"),
    )

    op.drop_index("ix_whatsapp_messages_inquiry_id", table_name="whatsapp_messages")
    op.drop_index("ix_whatsapp_messages_processing_status", table_name="whatsapp_messages")
    op.drop_constraint("ck_whatsapp_messages_processing_status", "whatsapp_messages")
    op.drop_column("whatsapp_messages", "inquiry_id")
    op.drop_column("whatsapp_messages", "processing_note")
    op.drop_column("whatsapp_messages", "processed_at")
    op.drop_column("whatsapp_messages", "processing_status")
