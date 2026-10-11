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
