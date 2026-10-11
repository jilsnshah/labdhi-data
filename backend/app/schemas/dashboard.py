"""Dashboard, search, audit and 360-view payloads."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AuditAction
from app.schemas.activity import ActivityOut
from app.schemas.common import ORMBase, UserRef
from app.schemas.inquiry import InquiryListItem, TimelineEvent
from app.schemas.note import NoteOut
from app.schemas.party import PartyDetailOut, PartyOut


class DashboardCounts(BaseModel):
    #: ``open_*`` counts are ACTIVE inquiries; the names predate the two-state model.
    open_customer_inquiries: int
    open_supplier_inquiries: int
    open_transport_inquiries: int
    todays_activities: int
    overdue_activities: int
    upcoming_followups: int
    active_customers: int
    active_suppliers: int
    active_transporters: int
    active_products: int
    #: Parties met recently whose identity is not verified yet.
    prospects: int = 0


class DashboardOut(BaseModel):
    counts: DashboardCounts
    todays_activities: list[ActivityOut] = Field(default_factory=list)
    upcoming_followups: list[ActivityOut] = Field(default_factory=list)
    recent_customers: list[PartyOut] = Field(default_factory=list)
    recent_inquiries: list[InquiryListItem] = Field(default_factory=list)
    recently_closed_inquiries: list[InquiryListItem] = Field(default_factory=list)


class SearchHit(BaseModel):
    entity: str
    id: int
    label: str
    sublabel: str | None = None
    status: str | None = None


class SearchResults(BaseModel):
    query: str
    parties: list[SearchHit] = Field(default_factory=list)
    products: list[SearchHit] = Field(default_factory=list)
    materials: list[SearchHit] = Field(default_factory=list)
    grades: list[SearchHit] = Field(default_factory=list)
    manufacturers: list[SearchHit] = Field(default_factory=list)
    total: int = 0


class AuditLogOut(ORMBase):
    id: int
    user_id: int | None
    entity_type: str
    entity_id: int
    action: AuditAction
    old_value: dict | None
    new_value: dict | None
    created_at: datetime
    user: UserRef | None = None


class PartyStats(BaseModel):
    open_inquiries: int = 0
    closed_inquiries: int = 0
    activities: int = 0
    upcoming_activities: int = 0
    notes: int = 0


class Party360Out(BaseModel):
    """Everything the trader needs on one screen for a single party."""

    party: PartyDetailOut
    stats: PartyStats
    open_inquiries: list[InquiryListItem] = Field(default_factory=list)
    inquiry_history: list[InquiryListItem] = Field(default_factory=list)
    activities: list[ActivityOut] = Field(default_factory=list)
    upcoming_activities: list[ActivityOut] = Field(default_factory=list)
    notes: list[NoteOut] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    # Placeholder for the future trading module (purchases / sales / transport jobs).
    deals: list[dict] = Field(
        default_factory=list,
        description="Reserved for the future trading module - always empty today.",
    )
