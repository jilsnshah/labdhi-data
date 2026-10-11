"""Customer activities: calls, WhatsApp, SMS, visits - scheduled and completed."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    ActivityOutcome,
    ActivityStatus,
    ActivityType,
    MessageDeliveryStatus,
    activity_outcome_enum,
    activity_status_enum,
    activity_type_enum,
    message_delivery_status_enum,
)


class Activity(Base, TimestampMixin):
    """A scheduled activity is just an Activity with status=SCHEDULED and a future
    ``scheduled_at``; a follow-up is a new Activity pointing at its parent.

    Activities hang off any party: customers mostly, but also a cold supplier you
    want to call or a transporter you need to meet. The admin UI still defaults to
    customers; the field app only ever sees activities assigned to the caller.
    """

    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint(
            "(status <> 'COMPLETED') OR (completed_at IS NOT NULL)",
            name="ck_activities_completed_requires_timestamp",
        ),
        CheckConstraint(
            "(status <> 'SCHEDULED') OR (scheduled_at IS NOT NULL)",
            name="ck_activities_scheduled_requires_timestamp",
        ),
        CheckConstraint("id <> parent_activity_id", name="ck_activities_no_self_parent"),
        # A visit needs somewhere to go: either a location row or, for an
        # address we only know as text ("his shop, Gondal Road"), a snapshot.
        CheckConstraint(
            "(activity_type <> 'VISIT') OR (location_id IS NOT NULL) "
            "OR (location_snapshot IS NOT NULL)",
            name="ck_activities_visit_requires_location",
        ),
        Index("ix_activities_party_status", "party_id", "status"),
        Index("ix_activities_status_scheduled_at", "status", "scheduled_at"),
        Index("ix_activities_party_scheduled_at", "party_id", "scheduled_at"),
        # The salesperson app only ever queries "my activities, by time".
        Index(
            "ix_activities_salesperson_scheduled_at",
            "assigned_salesperson_id",
            "scheduled_at",
        ),
        Index(
            "ix_activities_salesperson_status",
            "assigned_salesperson_id",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    party_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    activity_type: Mapped[ActivityType] = mapped_column(
        activity_type_enum, nullable=False, index=True
    )
    status: Mapped[ActivityStatus] = mapped_column(
        activity_status_enum,
        nullable=False,
        default=ActivityStatus.SCHEDULED,
        server_default=ActivityStatus.SCHEDULED.value,
        index=True,
    )
    subject: Mapped[str | None] = mapped_column(String(200))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    #: Field user who must execute this activity (role must be SALESPERSON,
    #: validated in the service layer). Null = handled by the desk itself.
    assigned_salesperson_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    #: Who actually reported the completion (salesperson or desk user).
    completed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    #: Structured result, alongside the free-text ``outcome`` note.
    outcome_code: Mapped[ActivityOutcome | None] = mapped_column(activity_outcome_enum)
    #: Where the activity happens (required for VISIT, unused for calls/messages).
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    #: Address as it was when the activity was created, so a later change to the
    #: customer's location does not rewrite history.
    location_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # "Why is this activity scheduled?"
    note: Mapped[str | None] = mapped_column(Text())
    # "What happened / what was the outcome?"
    outcome: Mapped[str | None] = mapped_column(Text())
    parent_activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id", ondelete="SET NULL"), index=True
    )
    # Optional business context, e.g. "called the customer about inquiry #1001".
    related_inquiry_id: Mapped[int | None] = mapped_column(
        ForeignKey("inquiries.id", ondelete="SET NULL"), index=True
    )

    # --- Reserved for the future WhatsApp / SMS integration (no logic yet) ---
    external_message_id: Mapped[str | None] = mapped_column(String(120), index=True)
    delivery_status: Mapped[MessageDeliveryStatus | None] = mapped_column(
        message_delivery_status_enum
    )
    read_status: Mapped[bool | None] = mapped_column()

    party: Mapped[Party] = relationship(lazy="joined")  # noqa: F821
    creator: Mapped[User] = relationship(  # noqa: F821
        lazy="joined", foreign_keys=[created_by]
    )
    assigned_salesperson: Mapped[User | None] = relationship(  # noqa: F821
        lazy="joined", foreign_keys=[assigned_salesperson_id]
    )
    completer: Mapped[User | None] = relationship(  # noqa: F821
        lazy="joined", foreign_keys=[completed_by]
    )
    location: Mapped[Location | None] = relationship(lazy="joined")  # noqa: F821
    parent_activity: Mapped[Activity | None] = relationship(
        back_populates="follow_ups", remote_side=[id]
    )
    follow_ups: Mapped[list[Activity]] = relationship(back_populates="parent_activity")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Activity {self.id} {self.activity_type} {self.status}>"
