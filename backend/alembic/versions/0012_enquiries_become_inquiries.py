"""An enquiry from a party becomes an inquiry on arrival.

There is no longer a queue to approve: what a party sends through their portal
link is written straight onto the book, creating whatever master data they
named that we did not have. Two consequences here.

An inquiry can now have no author. ``created_by`` becomes nullable, because
there is no salesperson behind one a customer raised themselves, and borrowing
somebody's name to satisfy a NOT NULL would be a lie. ``source`` says which
kind it is; every row that exists today was keyed in by the desk.

And ``portal_enquiries`` loses its decision workflow - status, who handled it
and when - keeping only what an inquiry cannot hold: the party's own note, the
places in their words, and the inquiry each one became. Any row still waiting
for a decision never became an inquiry and has nowhere to point, so it is
removed; the table was added one release ago and has never run anywhere but a
developer's machine.

Revision ID: 0012_enquiries_become_inquiries
Revises: 0011_portal_enquiries
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_enquiries_become_inquiries"
down_revision: str | None = "0011_portal_enquiries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCES = ("DESK", "PORTAL")


def upgrade() -> None:
    # --- inquiries: an author is now optional, and we record who sent it --- #
    op.add_column(
        "inquiries",
        sa.Column("source", sa.String(length=32), nullable=False, server_default="DESK"),
    )
    op.create_check_constraint(
        "ck_inquiries_source", "inquiries", sa.text("source IN " + str(SOURCES))
    )
    op.create_index("ix_inquiries_source", "inquiries", ["source"])
    op.alter_column("inquiries", "created_by", existing_type=sa.Integer(), nullable=True)

    # --- portal_enquiries: no queue, so no decision to record -------------- #
    op.execute("DELETE FROM portal_enquiries WHERE inquiry_id IS NULL")

    op.drop_constraint("ck_portal_enquiries_accepted_has_inquiry", "portal_enquiries")
    op.drop_constraint("ck_portal_enquiries_handled_is_recorded", "portal_enquiries")
    op.drop_constraint("ck_portal_enquiries_product_named", "portal_enquiries")
    op.drop_constraint("ck_portal_enquiries_status", "portal_enquiries")
    op.drop_index("ix_portal_enquiries_status_created_at", table_name="portal_enquiries")
    op.drop_index("ix_portal_enquiries_party_status", table_name="portal_enquiries")
    op.drop_index("ix_portal_enquiries_status", table_name="portal_enquiries")

    op.drop_column("portal_enquiries", "status")
    op.drop_column("portal_enquiries", "handled_by")
    op.drop_column("portal_enquiries", "handled_at")
    op.drop_column("portal_enquiries", "product_text")

    op.create_check_constraint(
        "ck_portal_enquiries_product_named",
        "portal_enquiries",
        sa.text("inquiry_type = 'TRANSPORT' OR product_id IS NOT NULL"),
    )
    op.create_index(
        "ix_portal_enquiries_party_created_at", "portal_enquiries", ["party_id", "created_at"]
    )

    # The inquiry is written in the same breath as the row, and deleting it
    # takes the enquiry with it: the words only mean anything beside the record.
    op.alter_column("portal_enquiries", "inquiry_id", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint("portal_enquiries_inquiry_id_fkey", "portal_enquiries", type_="foreignkey")
    op.create_foreign_key(
        "portal_enquiries_inquiry_id_fkey",
        "portal_enquiries",
        "inquiries",
        ["inquiry_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("portal_enquiries_inquiry_id_fkey", "portal_enquiries", type_="foreignkey")
    op.create_foreign_key(
        "portal_enquiries_inquiry_id_fkey",
        "portal_enquiries",
        "inquiries",
        ["inquiry_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("portal_enquiries", "inquiry_id", existing_type=sa.Integer(), nullable=True)
    op.drop_index("ix_portal_enquiries_party_created_at", table_name="portal_enquiries")
    op.drop_constraint("ck_portal_enquiries_product_named", "portal_enquiries")

    op.add_column("portal_enquiries", sa.Column("product_text", sa.String(length=200)))
    op.add_column("portal_enquiries", sa.Column("handled_at", sa.DateTime(timezone=True)))
    op.add_column(
        "portal_enquiries",
        sa.Column("handled_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
    )
    # Anything that arrived while the workflow was gone became an inquiry with
    # nobody deciding it, and the old shape cannot say that: ACCEPTED there
    # means a named person accepted it. NEW is the least wrong of the two, and
    # the inquiry each row points at is still the truth of what happened.
    op.add_column(
        "portal_enquiries",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="NEW"),
    )
    op.create_index("ix_portal_enquiries_status", "portal_enquiries", ["status"])
    op.create_index(
        "ix_portal_enquiries_party_status", "portal_enquiries", ["party_id", "status"]
    )
    op.create_index(
        "ix_portal_enquiries_status_created_at", "portal_enquiries", ["status", "created_at"]
    )
    op.create_check_constraint(
        "ck_portal_enquiries_status",
        "portal_enquiries",
        sa.text("status IN ('NEW', 'ACCEPTED', 'DECLINED')"),
    )
    op.create_check_constraint(
        "ck_portal_enquiries_product_named",
        "portal_enquiries",
        sa.text(
            "inquiry_type = 'TRANSPORT' OR product_id IS NOT NULL OR product_text IS NOT NULL"
        ),
    )
    op.create_check_constraint(
        "ck_portal_enquiries_handled_is_recorded",
        "portal_enquiries",
        sa.text("status = 'NEW' OR (handled_at IS NOT NULL AND handled_by IS NOT NULL)"),
    )
    op.create_check_constraint(
        "ck_portal_enquiries_accepted_has_inquiry",
        "portal_enquiries",
        sa.text("status <> 'ACCEPTED' OR inquiry_id IS NOT NULL"),
    )

    op.alter_column("inquiries", "created_by", existing_type=sa.Integer(), nullable=False)
    op.drop_index("ix_inquiries_source", table_name="inquiries")
    op.drop_constraint("ck_inquiries_source", "inquiries")
    op.drop_column("inquiries", "source")
