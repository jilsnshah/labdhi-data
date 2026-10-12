"""Deliberately narrow payloads for the field app.

Nothing here exposes a CRM object graph: a salesperson sees the customer's name,
contact and address for the activity they must execute - no ids to probe with, no
products, no inquiries, no other parties.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import ActivityOutcome, ActivityStatus, ActivityType


class SalespersonProfile(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None = None
    role: str


class ActivityCustomerView(BaseModel):
    """Only what is needed to make the call or reach the customer."""

    name: str
    contact_person: str | None = None
    phone: str | None = None


class ActivityLocationView(BaseModel):
    label: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    #: One-line address for display and for the maps fallback.
    formatted: str
    #: Ready-to-open Google Maps directions link (coordinates when known).
    maps_url: str


class SalespersonActivity(BaseModel):
    id: int
    activity_type: ActivityType
    status: ActivityStatus
    subject: str | None = None
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    #: The admin's purpose/brief for this activity.
    purpose: str | None = None
    #: What the salesperson reported.
    completion_note: str | None = None
    outcome_code: ActivityOutcome | None = None
    parent_activity_id: int | None = None
    is_visit: bool = False
    can_complete: bool = False
    #: Logged by the salesperson themselves (a cold call or visit), not assigned.
    self_logged: bool = False
    customer: ActivityCustomerView
    location: ActivityLocationView | None = None


class SalespersonDayCounts(BaseModel):
    today_total: int = 0
    today_pending: int = 0
    today_completed: int = 0
    today_visits: int = 0
    overdue: int = 0
    upcoming: int = 0


class SalespersonDashboard(BaseModel):
    profile: SalespersonProfile
    counts: SalespersonDayCounts
    today: list[SalespersonActivity] = Field(default_factory=list)
    overdue: list[SalespersonActivity] = Field(default_factory=list)
    next_activity: SalespersonActivity | None = None


class CompleteActivityRequest(BaseModel):
    outcome_code: ActivityOutcome
    completion_note: str = Field(min_length=1, max_length=4000)
    completed_at: datetime | None = None
    #: Optional client-generated id so a retried submission is not applied twice.
    client_token: str | None = Field(default=None, max_length=64)


class FollowUpRequest(BaseModel):
    """customer_id, salesperson and parent are derived server-side, never sent."""

    activity_type: ActivityType
    scheduled_at: datetime
    note: str | None = Field(default=None, max_length=4000)


class LocationFixRequest(BaseModel):
    """Coordinates captured by the person actually standing there."""

    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=128)


class CompleteActivityResponse(BaseModel):
    activity: SalespersonActivity
    already_completed: bool = False


class FollowUpResponse(BaseModel):
    activity: SalespersonActivity


# --- Logging an activity from the field ------------------------------------
class FieldContact(BaseModel):
    """Someone this salesperson has already worked with.

    Referenced by ``ref`` - the id of the salesperson's own latest activity with
    them - never by a party id, so the app cannot be used to enumerate parties.
    """

    ref: int
    name: str
    contact_person: str | None = None
    phone: str | None = None
    party_type: str
    is_prospect: bool = False
    place: str | None = None
    last_activity_at: datetime | None = None
    activity_count: int = 0


class FieldNewContact(BaseModel):
    """A party met cold in the field: saved as a FIELD prospect for the office."""

    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    contact_person: str | None = Field(default=None, max_length=120)
    party_type: str = Field(default="CUSTOMER", pattern="^(CUSTOMER|SUPPLIER)$")


class LogActivityRequest(BaseModel):
    """A call or visit the salesperson did - or is about to do - on their own.

    Exactly one of ``contact_ref`` / ``new_contact``. The assignee is always the
    signed-in salesperson; there is nothing in this payload that can change that.
    """

    contact_ref: int | None = None
    new_contact: FieldNewContact | None = None
    activity_type: ActivityType
    #: True: it already happened (needs an outcome). False: plan it for later.
    done: bool = True
    outcome_code: ActivityOutcome | None = None
    #: What happened (done) or what it is for (planned).
    note: str | None = Field(default=None, max_length=4000)
    subject: str | None = Field(default=None, max_length=200)
    #: When it happened (done, defaults to now) or when it is planned for.
    at: datetime | None = None
    #: Where a visit is - typed by the salesperson.
    place: str | None = Field(default=None, max_length=200)
    #: Where a visit is - from the phone's GPS.
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    #: Client-generated id so an offline retry never logs the same thing twice.
    client_token: str | None = Field(default=None, max_length=64)


class LogActivityResponse(BaseModel):
    activity: SalespersonActivity
    #: True when this exact submission was already recorded (an offline retry).
    duplicate: bool = False
    #: True when a new prospect was created for the office to review.
    new_contact_created: bool = False


class DayTally(BaseModel):
    date: str
    completed: int = 0


class FieldStats(BaseModel):
    """The salesperson's own last seven days - nobody else's."""

    days: list[DayTally] = Field(default_factory=list)
    completed_7d: int = 0
    visits_7d: int = 0
    calls_7d: int = 0
    self_logged_7d: int = 0
    new_contacts_7d: int = 0
    #: Share of completed assigned work finished on or before its scheduled day.
    on_time_rate: float | None = None
