"""Inquiries record quotations directly; status is ACTIVE or CLOSED.

What changes
------------
* ``inquiries.status`` collapses to ACTIVE / CLOSED.
  OPEN, IN_PROGRESS, WAITING and QUOTED become ACTIVE; CLOSED and CANCELLED
  become CLOSED. A closure reason is no longer required to close.
* Supplier and customer inquiries carry ``rate`` (rupees per kilogram) and an
  independent ``location_id``. Transport inquiries carry ``price`` (rupees).
* ``customer_inquiries.delivery_location_id`` is renamed to ``location_id`` so
  both sides use the same field.

What is preserved
-----------------
Nothing historical is deleted. These stay in the database, unused by the app:
``inquiries.closure_reason`` / ``closure_note``, ``customer_inquiries.target_price``
/ ``price_unit`` / ``required_by`` / ``notes``, ``supplier_inquiries.required_by`` /
``notes`` / ``source_customer_inquiry_id``, ``transport_inquiries.product_id`` /
``required_date`` / ``vehicle_type`` / ``notes`` / ``source_customer_inquiry_id``,
and the whole ``inquiry_responses`` table.

Backfill
--------
``rate`` takes the latest priced response, converted to rupees per kilogram
(per-MT prices are divided by 1000; a missing price unit is read as MT, the old
form's default). Quotes in bags, litres or pieces cannot be converted and are
left empty rather than guessed. Customer inquiries without a priced response
fall back to their old target price, converted the same way. Transport ``price``
takes the latest quoted amount as it was entered.

Revision ID: 0007_simplified_inquiries
Revises: 0006_party_applications
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_simplified_inquiries"
down_revision: str | None = "0006_party_applications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_STATUSES = ("OPEN", "IN_PROGRESS", "WAITING", "QUOTED", "CLOSED", "CANCELLED")
NEW_STATUSES = ("ACTIVE", "CLOSED")

#: Converts a stored price to rupees per kilogram given its unit; NULL when the
#: unit is not a weight. ``{price}`` and ``{unit}`` are SQL expressions.
PER_KG = (
    "CASE "
    "WHEN {price} IS NULL THEN NULL "
    "WHEN {unit} IS NULL OR {unit} = 'MT' THEN ROUND({price} / 1000.0, 2) "
    "WHEN {unit} = 'KG' THEN {price} "
    "ELSE NULL END"
)

#: Latest priced response per inquiry.
LATEST_QUOTE = """
    SELECT DISTINCT ON (inquiry_id) inquiry_id, quoted_price, price_unit
    FROM inquiry_responses
    WHERE quoted_price IS NOT NULL AND quoted_price > 0
    ORDER BY inquiry_id, responded_at DESC, id DESC
"""


def _status_check(values: tuple[str, ...]) -> str:
    allowed = ", ".join(f"'{value}'" for value in values)
    return f"status IN ({allowed})"


def upgrade() -> None:
    # --- status ------------------------------------------------------------ #
    op.drop_constraint("ck_inquiries_closed_requires_reason", "inquiries", type_="check")
    op.drop_constraint("ck_inquiries_status_allowed", "inquiries", type_="check")
    op.execute(
        "UPDATE inquiries SET status = 'ACTIVE' "
        "WHERE status IN ('OPEN', 'IN_PROGRESS', 'WAITING', 'QUOTED')"
    )
    op.execute(
        "UPDATE inquiries SET status = 'CLOSED', "
        "closed_at = COALESCE(closed_at, updated_at) "
        "WHERE status IN ('CLOSED', 'CANCELLED')"
    )
    op.create_check_constraint(
        "ck_inquiries_status_allowed", "inquiries", _status_check(NEW_STATUSES)
    )
    op.create_check_constraint(
        "ck_inquiries_closed_has_timestamp",
        "inquiries",
        "(status <> 'CLOSED') OR (closed_at IS NOT NULL)",
    )
    op.alter_column("inquiries", "status", server_default="ACTIVE")

    # --- supplier inquiries ------------------------------------------------ #
    op.add_column("supplier_inquiries", sa.Column("rate", sa.Numeric(14, 2), nullable=True))
    op.add_column("supplier_inquiries", sa.Column("location_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "supplier_inquiries_location_id_fkey",
        "supplier_inquiries",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_supplier_inquiries_location_id", "supplier_inquiries", ["location_id"])
    per_kg = PER_KG.format(price="q.quoted_price", unit="q.price_unit")
    op.execute(
        f"""
        UPDATE supplier_inquiries s SET rate = {per_kg}
        FROM ({LATEST_QUOTE}) q
        WHERE q.inquiry_id = s.inquiry_id
        """
    )
    op.create_check_constraint(
        "ck_supplier_inquiries_rate_positive", "supplier_inquiries", "rate IS NULL OR rate > 0"
    )

    # --- customer inquiries ------------------------------------------------ #
    op.alter_column("customer_inquiries", "delivery_location_id", new_column_name="location_id")
    op.execute(
        "ALTER TABLE customer_inquiries RENAME CONSTRAINT "
        "customer_inquiries_delivery_location_id_fkey TO customer_inquiries_location_id_fkey"
    )
    op.create_index("ix_customer_inquiries_location_id", "customer_inquiries", ["location_id"])
    op.add_column("customer_inquiries", sa.Column("rate", sa.Numeric(14, 2), nullable=True))
    op.execute(
        f"""
        UPDATE customer_inquiries c SET rate = {per_kg}
        FROM ({LATEST_QUOTE}) q
        WHERE q.inquiry_id = c.inquiry_id
        """
    )
    target_per_kg = PER_KG.format(price="target_price", unit="price_unit")
    op.execute(
        f"UPDATE customer_inquiries SET rate = {target_per_kg} "
        "WHERE rate IS NULL AND target_price IS NOT NULL"
    )
    # A conversion can round a tiny price to zero; such a rate is not a quote.
    op.execute("UPDATE customer_inquiries SET rate = NULL WHERE rate <= 0")
    op.execute("UPDATE supplier_inquiries SET rate = NULL WHERE rate <= 0")
    op.create_check_constraint(
        "ck_customer_inquiries_rate_positive", "customer_inquiries", "rate IS NULL OR rate > 0"
    )

    # --- transport inquiries ----------------------------------------------- #
    op.add_column("transport_inquiries", sa.Column("price", sa.Numeric(14, 2), nullable=True))
    op.execute(
        f"""
        UPDATE transport_inquiries t SET price = q.quoted_price
        FROM ({LATEST_QUOTE}) q
        WHERE q.inquiry_id = t.inquiry_id
        """
    )
    op.create_check_constraint(
        "ck_transport_inquiries_price_positive",
        "transport_inquiries",
        "price IS NULL OR price > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_transport_inquiries_price_positive", "transport_inquiries", type_="check"
    )
    op.drop_column("transport_inquiries", "price")

    op.drop_constraint("ck_customer_inquiries_rate_positive", "customer_inquiries", type_="check")
    op.drop_column("customer_inquiries", "rate")
    op.drop_index("ix_customer_inquiries_location_id", table_name="customer_inquiries")
    op.execute(
        "ALTER TABLE customer_inquiries RENAME CONSTRAINT "
        "customer_inquiries_location_id_fkey TO customer_inquiries_delivery_location_id_fkey"
    )
    op.alter_column("customer_inquiries", "location_id", new_column_name="delivery_location_id")

    op.drop_constraint("ck_supplier_inquiries_rate_positive", "supplier_inquiries", type_="check")
    op.drop_index("ix_supplier_inquiries_location_id", table_name="supplier_inquiries")
    op.drop_constraint(
        "supplier_inquiries_location_id_fkey", "supplier_inquiries", type_="foreignkey"
    )
    op.drop_column("supplier_inquiries", "location_id")
    op.drop_column("supplier_inquiries", "rate")

    # The old ladder cannot be reconstructed; ACTIVE maps back to its start, and
    # a CLOSED row without a recorded reason gets OTHER so the old rule holds.
    op.alter_column("inquiries", "status", server_default="OPEN")
    op.drop_constraint("ck_inquiries_closed_has_timestamp", "inquiries", type_="check")
    op.drop_constraint("ck_inquiries_status_allowed", "inquiries", type_="check")
    op.execute("UPDATE inquiries SET status = 'OPEN' WHERE status = 'ACTIVE'")
    op.execute(
        "UPDATE inquiries SET closure_reason = 'OTHER', "
        "closure_note = COALESCE(closure_note, 'Closed without a reason') "
        "WHERE status = 'CLOSED' AND closure_reason IS NULL"
    )
    op.create_check_constraint(
        "ck_inquiries_status_allowed", "inquiries", _status_check(OLD_STATUSES)
    )
    op.create_check_constraint(
        "ck_inquiries_closed_requires_reason",
        "inquiries",
        "(status <> 'CLOSED') OR (closure_reason IS NOT NULL AND closed_at IS NOT NULL)",
    )
