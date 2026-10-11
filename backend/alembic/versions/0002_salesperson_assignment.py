"""Salesperson role, activity assignment, visit locations and enum checks.

Revision ID: 0002_salesperson
Revises: 0001_initial
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_salesperson"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OUTCOME_CODES = (
    "COMPLETED",
    "CUSTOMER_INTERESTED",
    "CUSTOMER_NOT_INTERESTED",
    "FOLLOW_UP_REQUIRED",
    "NO_RESPONSE",
    "RESCHEDULED",
    "OTHER",
)

#: Value whitelists enforced in the database for the columns where an invalid
#: value would be a security or reporting problem. (Columns that repeat the same
#: enum twice in one table are validated at the application layer only, so the
#: constraint names stay unique and obvious.)
ENUM_CHECKS: tuple[tuple[str, str, tuple[str, ...], bool], ...] = (
    ("users", "role", ("ADMIN", "USER", "SALESPERSON"), False),
    ("parties", "party_type", ("CUSTOMER", "SUPPLIER", "TRANSPORTER"), False),
    (
        "party_products",
        "relationship_type",
        ("SUPPLIES", "PURCHASES", "INTERESTED_IN"),
        False,
    ),
    (
        "party_locations",
        "location_type",
        ("HEAD_OFFICE", "FACTORY", "WAREHOUSE", "DELIVERY_LOCATION", "OTHER"),
        False,
    ),
    ("inquiries", "inquiry_type", ("CUSTOMER", "SUPPLIER", "TRANSPORT"), False),
    (
        "inquiries",
        "status",
        ("OPEN", "IN_PROGRESS", "WAITING", "QUOTED", "CLOSED", "CANCELLED"),
        False,
    ),
    (
        "inquiries",
        "closure_reason",
        (
            "CONVERTED_TO_DEAL",
            "PRICE_TOO_HIGH",
            "NO_STOCK",
            "SUPPLIER_UNAVAILABLE",
            "TRANSPORT_UNAVAILABLE",
            "CUSTOMER_CANCELLED",
            "NO_RESPONSE",
            "DUPLICATE",
            "OTHER",
        ),
        True,
    ),
    (
        "inquiry_responses",
        "response_type",
        ("QUOTE", "COUNTER_OFFER", "NO_STOCK", "DECLINED", "NO_RESPONSE", "INFO"),
        False,
    ),
    (
        "activities",
        "activity_type",
        ("CALL", "WHATSAPP", "SMS", "VISIT", "EMAIL", "MEETING"),
        False,
    ),
    (
        "activities",
        "status",
        ("SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"),
        False,
    ),
    ("activities", "outcome_code", OUTCOME_CODES, True),
)


def _check_sql(column: str, values: tuple[str, ...], nullable: bool) -> str:
    allowed = ", ".join(f"'{value}'" for value in values)
    condition = f"{column} IN ({allowed})"
    return f"({column} IS NULL) OR ({condition})" if nullable else condition


def upgrade() -> None:
    # --- users: phone + salesperson role ---------------------------------- #
    op.add_column("users", sa.Column("phone", sa.String(length=30), nullable=True))
    op.create_index("ix_users_role", "users", ["role"], unique=False)

    # --- activities: assignment, completion author, outcome, location ----- #
    op.add_column(
        "activities", sa.Column("assigned_salesperson_id", sa.Integer(), nullable=True)
    )
    op.add_column("activities", sa.Column("completed_by", sa.Integer(), nullable=True))
    op.add_column(
        "activities",
        sa.Column(
            "outcome_code",
            sa.Enum(*OUTCOME_CODES, name="activity_outcome", native_enum=False, length=32),
            nullable=True,
        ),
    )
    op.add_column("activities", sa.Column("location_id", sa.Integer(), nullable=True))
    op.add_column(
        "activities",
        sa.Column("location_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_foreign_key(
        "activities_assigned_salesperson_id_fkey",
        "activities",
        "users",
        ["assigned_salesperson_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "activities_completed_by_fkey",
        "activities",
        "users",
        ["completed_by"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "activities_location_id_fkey",
        "activities",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "ix_activities_assigned_salesperson_id",
        "activities",
        ["assigned_salesperson_id"],
        unique=False,
    )
    op.create_index("ix_activities_location_id", "activities", ["location_id"], unique=False)
    op.create_index(
        "ix_activities_salesperson_scheduled_at",
        "activities",
        ["assigned_salesperson_id", "scheduled_at"],
        unique=False,
    )
    op.create_index(
        "ix_activities_salesperson_status",
        "activities",
        ["assigned_salesperson_id", "status"],
        unique=False,
    )

    # Existing completed activities were reported by whoever created them.
    op.execute(
        "UPDATE activities SET completed_by = created_by "
        "WHERE status = 'COMPLETED' AND completed_by IS NULL"
    )
    op.execute(
        "UPDATE activities SET outcome_code = 'COMPLETED' "
        "WHERE status = 'COMPLETED' AND outcome_code IS NULL"
    )

    # Backfill visit locations from the customer's primary location, then take a
    # snapshot so later address edits do not rewrite history.
    op.execute(
        """
        UPDATE activities a
           SET location_id = pl.location_id
          FROM (
                SELECT DISTINCT ON (party_id) party_id, location_id
                  FROM party_locations
                 ORDER BY party_id, is_primary DESC, id
               ) pl
         WHERE pl.party_id = a.customer_id
           AND a.activity_type = 'VISIT'
           AND a.location_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE activities a
           SET location_snapshot = jsonb_strip_nulls(
                   jsonb_build_object(
                       'location_id', l.id,
                       'label', l.label,
                       'address_line_1', l.address_line_1,
                       'address_line_2', l.address_line_2,
                       'city', l.city,
                       'state', l.state,
                       'country', l.country,
                       'pincode', l.pincode,
                       'latitude', l.latitude::text,
                       'longitude', l.longitude::text
                   )
               )
          FROM locations l
         WHERE l.id = a.location_id
           AND a.location_snapshot IS NULL
        """
    )
    # NOT VALID: any legacy visit without an address stays readable, while every
    # new or updated row must carry a location.
    op.execute(
        "ALTER TABLE activities ADD CONSTRAINT ck_activities_visit_requires_location "
        "CHECK ((activity_type <> 'VISIT') OR (location_id IS NOT NULL)) NOT VALID"
    )

    # --- enum whitelists at the database level ---------------------------- #
    for table, column, values, nullable in ENUM_CHECKS:
        op.create_check_constraint(
            f"ck_{table}_{column}_allowed", table, _check_sql(column, values, nullable)
        )


def downgrade() -> None:
    for table, column, _values, _nullable in reversed(ENUM_CHECKS):
        op.drop_constraint(f"ck_{table}_{column}_allowed", table, type_="check")

    op.drop_constraint("ck_activities_visit_requires_location", "activities", type_="check")
    op.drop_index("ix_activities_salesperson_status", table_name="activities")
    op.drop_index("ix_activities_salesperson_scheduled_at", table_name="activities")
    op.drop_index("ix_activities_location_id", table_name="activities")
    op.drop_index("ix_activities_assigned_salesperson_id", table_name="activities")
    op.drop_constraint("activities_location_id_fkey", "activities", type_="foreignkey")
    op.drop_constraint("activities_completed_by_fkey", "activities", type_="foreignkey")
    op.drop_constraint(
        "activities_assigned_salesperson_id_fkey", "activities", type_="foreignkey"
    )
    op.drop_column("activities", "location_snapshot")
    op.drop_column("activities", "location_id")
    op.drop_column("activities", "outcome_code")
    op.drop_column("activities", "completed_by")
    op.drop_column("activities", "assigned_salesperson_id")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "phone")
