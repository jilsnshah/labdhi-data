"""Activity schemas (customer activities only in this scope)."""

from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ActivityOutcome, ActivityStatus, ActivityType
from app.schemas.common import LocationRef, ORMBase, PartyRef, UserRef
from app.schemas.party import LocationCreate, PartyQuickCreate

#: Activity types that need a location (validated for admin creation).
LOCATION_REQUIRED_TYPES = {ActivityType.VISIT, ActivityType.MEETING}


class ActivityCreate(BaseModel):
    """Create an activity for an existing party, or for one met just now.

    Exactly one of ``party_id`` / ``new_party`` is required. ``customer_id`` is
    still accepted as a deprecated alias of ``party_id``.
    """

    model_config = ConfigDict(populate_by_name=True)

    party_id: int | None = Field(
        default=None, validation_alias=AliasChoices("party_id", "customer_id")
    )
    new_party: PartyQuickCreate | None = Field(
        default=None, description="Creates a PROSPECT party in the same transaction."
    )
    activity_type: ActivityType
    subject: str | None = Field(default=None, max_length=200)
    scheduled_at: datetime | None = None
    note: str | None = Field(default=None, description="Why is this activity scheduled?")
    parent_activity_id: int | None = None
    related_inquiry_id: int | None = None
    assigned_salesperson_id: int | None = Field(
        default=None, description="Must reference an active SALESPERSON account."
    )
    location_id: int | None = Field(
        default=None,
        description="Where to go. For a VISIT provide this, new_location or location_text.",
    )
    new_location: LocationCreate | None = Field(
        default=None, description="Create the address inline; it is reusable afterwards."
    )
    location_text: str | None = Field(
        default=None,
        max_length=200,
        description="Address known only as text, e.g. 'his shop, Gondal Road'. Stored as a "
        "snapshot on the activity without creating a location row.",
    )
    # Log something that already happened in one shot.
    status: ActivityStatus = ActivityStatus.SCHEDULED
    completed_at: datetime | None = None
    outcome: str | None = None

    @model_validator(mode="after")
    def _consistent(self) -> ActivityCreate:
        if (self.party_id is None) == (self.new_party is None):
            raise ValueError("provide either party_id or new_party, not both")
        if self.status == ActivityStatus.SCHEDULED and self.scheduled_at is None:
            raise ValueError("scheduled_at is required for a SCHEDULED activity")
        if self.status == ActivityStatus.COMPLETED and self.completed_at is None:
            raise ValueError("completed_at is required when creating a COMPLETED activity")
        if self.location_id is not None and self.new_location is not None:
            raise ValueError("provide either location_id or new_location, not both")
        return self


class ActivityUpdate(BaseModel):
    """Admin/desk patch. The customer of an activity can never be changed."""

    activity_type: ActivityType | None = None
    subject: str | None = Field(default=None, max_length=200)
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    note: str | None = None
    outcome: str | None = None
    status: ActivityStatus | None = None
    related_inquiry_id: int | None = None
    assigned_salesperson_id: int | None = None
    location_id: int | None = None
    location_text: str | None = Field(default=None, max_length=200)


class ActivityCompleteRequest(BaseModel):
    outcome: str = Field(min_length=1, description="What happened? (free-text note)")
    outcome_code: ActivityOutcome = Field(
        default=ActivityOutcome.COMPLETED, description="Structured result"
    )
    completed_at: datetime | None = None
    follow_up: ActivityFollowUp | None = None


class ActivityFollowUp(BaseModel):
    """Completing an activity can immediately schedule the next one."""

    activity_type: ActivityType
    scheduled_at: datetime
    subject: str | None = Field(default=None, max_length=200)
    note: str | None = None


class ActivityOut(ORMBase):
    id: int
    party_id: int
    activity_type: ActivityType
    status: ActivityStatus
    subject: str | None
    scheduled_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    note: str | None
    outcome: str | None
    outcome_code: ActivityOutcome | None = None
    parent_activity_id: int | None
    related_inquiry_id: int | None
    created_by: int
    created_at: datetime
    updated_at: datetime
    party: PartyRef | None = None
    creator: UserRef | None = None
    assigned_salesperson_id: int | None = None
    assigned_salesperson: UserRef | None = None
    completed_by: int | None = None
    completer: UserRef | None = None
    location_id: int | None = None
    location: LocationRef | None = None


class ActivityWithChain(ActivityOut):
    follow_ups: list[ActivityOut] = Field(default_factory=list)


class ActivityCompleteResponse(BaseModel):
    activity: ActivityOut
    follow_up: ActivityOut | None = None


class ActivityAssignRequest(BaseModel):
    """Admin reassignment. ``null`` clears the assignment (desk handles it)."""

    assigned_salesperson_id: int | None = None


class ScheduleConflict(BaseModel):
    activity_id: int
    scheduled_at: datetime
    activity_type: ActivityType
    customer_name: str
    minutes_apart: int


class ConflictCheckResult(BaseModel):
    """Warning only - the admin may still save a conflicting activity."""

    has_conflict: bool
    conflicts: list[ScheduleConflict] = Field(default_factory=list)


class SalespersonWorkload(ORMBase):
    id: int
    name: str
    email: str
    phone: str | None = None
    status: str
    today_total: int = 0
    today_completed: int = 0
    today_pending: int = 0
    upcoming: int = 0
    overdue: int = 0


ActivityCompleteRequest.model_rebuild()
