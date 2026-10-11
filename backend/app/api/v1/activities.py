"""Customer activity endpoints."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query

from app.core.deps import AdminUser, SessionDep, StaffUser
from app.core.pagination import Page, PageParams, page_params
from app.models.enums import ActivityStatus, ActivityType
from app.schemas.activity import (
    ActivityAssignRequest,
    ActivityCompleteRequest,
    ActivityCompleteResponse,
    ActivityCreate,
    ActivityOut,
    ActivityUpdate,
    ActivityWithChain,
    ConflictCheckResult,
    SalespersonWorkload,
)
from app.services import activities as service

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=Page[ActivityOut])
def list_activities(
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, description="Customer name, subject, note or outcome"),
    party_id: int | None = Query(None, description="Any party: customer, supplier or transporter"),
    customer_id: int | None = Query(None, deprecated=True, description="Alias of party_id"),
    activity_type: ActivityType | None = None,
    status: list[ActivityStatus] | None = Query(None),
    scope: str | None = Query(
        None,
        pattern="^(today|upcoming|overdue|history)$",
        description="Convenience window evaluated in the business timezone",
    ),
    date_from: date | None = None,
    date_to: date | None = None,
    related_inquiry_id: int | None = None,
    assigned_salesperson_id: int | None = Query(
        None, description="Filter by the field user the activity is assigned to"
    ),
    unassigned_only: bool = Query(False, description="Only activities nobody is assigned to"),
    sort_by: str | None = Query(None, pattern="^(scheduled_at|created_at|completed_at|id)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
) -> Page[ActivityOut]:
    rows, total = service.list_activities(
        session,
        params,
        party_id=party_id or customer_id,
        activity_type=activity_type,
        statuses=status,
        scope=scope,
        date_from=date_from,
        date_to=date_to,
        related_inquiry_id=related_inquiry_id,
        assigned_salesperson_id=assigned_salesperson_id,
        unassigned_only=unassigned_only,
        q=q,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return Page.build([ActivityOut.model_validate(row) for row in rows], total, params)


@router.post("", response_model=ActivityOut, status_code=201)
def create_activity(payload: ActivityCreate, session: SessionDep, user: StaffUser) -> ActivityOut:
    return ActivityOut.model_validate(service.create_activity(session, payload, user.id))


@router.get("/salespeople/workload", response_model=list[SalespersonWorkload])
def salespeople_workload(
    session: SessionDep,
    _: StaffUser,
    include_inactive: bool = False,
) -> list[SalespersonWorkload]:
    """Per-salesperson counts for today, plus upcoming and overdue work."""
    return [
        SalespersonWorkload(**row)
        for row in service.salesperson_workload(session, include_inactive=include_inactive)
    ]


@router.get("/calendar", response_model=list[ActivityOut])
def activity_calendar(
    session: SessionDep,
    _: StaffUser,
    date_from: date,
    date_to: date,
    salesperson_id: int | None = None,
) -> list[ActivityOut]:
    """Scheduled activities in a date range, for the assignment calendar."""
    rows = service.calendar(
        session, date_from=date_from, date_to=date_to, salesperson_id=salesperson_id
    )
    return [ActivityOut.model_validate(row) for row in rows]


@router.get("/conflicts/check", response_model=ConflictCheckResult)
def check_conflicts(
    session: SessionDep,
    _: StaffUser,
    salesperson_id: int,
    scheduled_at: datetime,
    exclude_activity_id: int | None = None,
) -> ConflictCheckResult:
    """Warning only: tells the admin the field user is already booked nearby."""
    return service.find_conflicts(
        session,
        salesperson_id=salesperson_id,
        scheduled_at=scheduled_at,
        exclude_activity_id=exclude_activity_id,
    )


@router.get("/{activity_id}", response_model=ActivityWithChain)
def get_activity(activity_id: int, session: SessionDep, _: StaffUser) -> ActivityWithChain:
    return ActivityWithChain.model_validate(service.get_activity(session, activity_id))


@router.patch("/{activity_id}", response_model=ActivityOut)
def update_activity(
    activity_id: int, payload: ActivityUpdate, session: SessionDep, user: StaffUser
) -> ActivityOut:
    return ActivityOut.model_validate(
        service.update_activity(session, activity_id, payload, user.id)
    )


@router.post("/{activity_id}/assign", response_model=ActivityOut)
def assign_activity(
    activity_id: int,
    payload: ActivityAssignRequest,
    session: SessionDep,
    user: AdminUser,
) -> ActivityOut:
    """Assign or reassign the activity to a salesperson (admin only)."""
    return ActivityOut.model_validate(
        service.update_activity(
            session,
            activity_id,
            ActivityUpdate(assigned_salesperson_id=payload.assigned_salesperson_id),
            user.id,
        )
    )


@router.post("/{activity_id}/complete", response_model=ActivityCompleteResponse)
def complete_activity(
    activity_id: int,
    payload: ActivityCompleteRequest,
    session: SessionDep,
    user: StaffUser,
) -> ActivityCompleteResponse:
    """Record the outcome and optionally schedule the next follow-up in one call."""
    activity, follow_up = service.complete_activity(session, activity_id, payload, user.id)
    return ActivityCompleteResponse(
        activity=ActivityOut.model_validate(activity),
        follow_up=ActivityOut.model_validate(follow_up) if follow_up else None,
    )
