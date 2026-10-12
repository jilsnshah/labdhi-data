"""Field app endpoints.

Every route is gated by ``SalespersonUser`` and scoped to the authenticated
account. No CRM listing endpoint is reachable from here, and no request body or
query parameter can widen the scope - the salesperson id always comes from the
token.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import SalespersonUser, SessionDep
from app.schemas.common import Message
from app.schemas.salesperson import (
    ChangePasswordRequest,
    CompleteActivityRequest,
    CompleteActivityResponse,
    FieldContact,
    FieldStats,
    FollowUpRequest,
    FollowUpResponse,
    LocationFixRequest,
    LogActivityRequest,
    LogActivityResponse,
    SalespersonActivity,
    SalespersonDashboard,
    SalespersonProfile,
)
from app.services import salesperson as service

router = APIRouter(prefix="/salesperson", tags=["salesperson"])


@router.get("/me", response_model=SalespersonProfile)
def me(user: SalespersonUser) -> SalespersonProfile:
    return service.profile(user)


@router.get("/dashboard", response_model=SalespersonDashboard)
def dashboard(session: SessionDep, user: SalespersonUser) -> SalespersonDashboard:
    """Everything the home screen needs in one request (good for flaky networks)."""
    return service.dashboard(session, user)


@router.get("/activities/today", response_model=list[SalespersonActivity])
def today(session: SessionDep, user: SalespersonUser) -> list[SalespersonActivity]:
    return service.views(service.today_activities(session, user))


@router.get("/activities/overdue", response_model=list[SalespersonActivity])
def overdue(session: SessionDep, user: SalespersonUser) -> list[SalespersonActivity]:
    return service.views(service.overdue_activities(session, user))


@router.get("/activities/upcoming", response_model=list[SalespersonActivity])
def upcoming(
    session: SessionDep, user: SalespersonUser, days: int = 30
) -> list[SalespersonActivity]:
    return service.views(service.upcoming_activities(session, user, days=min(days, 90)))


@router.get("/activities/history", response_model=list[SalespersonActivity])
def history(
    session: SessionDep, user: SalespersonUser, limit: int = 100
) -> list[SalespersonActivity]:
    return service.views(service.history(session, user, limit=min(limit, 200)))


@router.get("/visits/today", response_model=list[SalespersonActivity])
def todays_visits(session: SessionDep, user: SalespersonUser) -> list[SalespersonActivity]:
    """Chronological visit list with a ready-made Google Maps link per stop."""
    return service.views(service.today_activities(session, user, visits_only=True))


@router.get("/contacts", response_model=list[FieldContact])
def my_contacts(
    session: SessionDep,
    user: SalespersonUser,
    q: str | None = Query(None, max_length=100, description="Name, contact person or phone"),
) -> list[FieldContact]:
    """People this salesperson has already worked with - never the whole party book."""
    return service.contacts(session, user, q=q)


@router.post("/activities", response_model=LogActivityResponse, status_code=201)
def log_activity(
    payload: LogActivityRequest, session: SessionDep, user: SalespersonUser
) -> LogActivityResponse:
    """Log a cold call or visit the salesperson did - or plans - on their own.

    Always assigned to the signed-in salesperson. A repeated ``client_token``
    returns the activity it already created instead of logging it twice.
    """
    activity, duplicate, new_contact = service.log_activity(session, user, payload)
    return LogActivityResponse(
        activity=service.to_view(activity),
        duplicate=duplicate,
        new_contact_created=new_contact,
    )


@router.get("/stats", response_model=FieldStats)
def my_stats(session: SessionDep, user: SalespersonUser) -> FieldStats:
    """The salesperson's own last seven days."""
    return service.stats(session, user)


@router.get("/activities/{activity_id}", response_model=SalespersonActivity)
def activity_detail(
    activity_id: int, session: SessionDep, user: SalespersonUser
) -> SalespersonActivity:
    return service.to_view(service.get_own_activity(session, user, activity_id))


@router.post("/activities/{activity_id}/start", response_model=SalespersonActivity)
def start_activity(
    activity_id: int, session: SessionDep, user: SalespersonUser
) -> SalespersonActivity:
    """'I am on it' - the only status change a field user can make themselves."""
    return service.to_view(service.start(session, user, activity_id))


@router.post("/activities/{activity_id}/location-fix", response_model=SalespersonActivity)
def fix_activity_location(
    activity_id: int,
    payload: LocationFixRequest,
    session: SessionDep,
    user: SalespersonUser,
) -> SalespersonActivity:
    """Pin where the customer actually is - this is how address data gets good."""
    activity = service.fix_location(session, user, activity_id, payload.latitude, payload.longitude)
    return service.to_view(activity)


@router.post("/change-password", response_model=Message)
def change_password(
    payload: ChangePasswordRequest, session: SessionDep, user: SalespersonUser
) -> Message:
    service.change_password(session, user, payload.current_password, payload.new_password)
    return Message(message="Password updated.")


@router.post("/activities/{activity_id}/complete", response_model=CompleteActivityResponse)
def complete_activity(
    activity_id: int,
    payload: CompleteActivityRequest,
    session: SessionDep,
    user: SalespersonUser,
) -> CompleteActivityResponse:
    activity, already = service.complete(session, user, activity_id, payload)
    return CompleteActivityResponse(activity=service.to_view(activity), already_completed=already)


@router.post(
    "/activities/{activity_id}/follow-up", response_model=FollowUpResponse, status_code=201
)
def schedule_follow_up(
    activity_id: int,
    payload: FollowUpRequest,
    session: SessionDep,
    user: SalespersonUser,
) -> FollowUpResponse:
    """The new activity inherits the customer, the assignee (always self) and the parent."""
    follow_up = service.schedule_follow_up(session, user, activity_id, payload)
    return FollowUpResponse(activity=service.to_view(follow_up))
