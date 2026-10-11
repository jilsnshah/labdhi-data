"""Customer activity services: scheduling, completion and follow-up chains."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta, timezone

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.pagination import PageParams, apply_sort, paginate
from app.models.activity import Activity
from app.models.enums import (
    ActivityOutcome,
    ActivityStatus,
    ActivityType,
    AuditAction,
    InquiryType,
    PartyStage,
    PartyType,
    RecordStatus,
    UserRole,
)
from app.models.inquiry import Inquiry
from app.models.party import Location, Party
from app.models.user import User
from app.schemas.activity import (
    LOCATION_REQUIRED_TYPES,
    ActivityCompleteRequest,
    ActivityCreate,
    ActivityUpdate,
    ConflictCheckResult,
    ScheduleConflict,
)
from app.services import audit
from app.services import parties as party_service
from app.services.common import apply_patch, get_or_404, require_active

ACTIVITY_TRANSITIONS: dict[ActivityStatus, set[ActivityStatus]] = {
    ActivityStatus.SCHEDULED: {
        ActivityStatus.IN_PROGRESS,
        ActivityStatus.COMPLETED,
        ActivityStatus.CANCELLED,
    },
    ActivityStatus.IN_PROGRESS: {ActivityStatus.COMPLETED, ActivityStatus.CANCELLED},
    ActivityStatus.COMPLETED: set(),
    ActivityStatus.CANCELLED: set(),
}

OPEN_ACTIVITY_STATUSES = [ActivityStatus.SCHEDULED, ActivityStatus.IN_PROGRESS]


def business_tz() -> timezone:
    return timezone(timedelta(minutes=settings.display_timezone_offset_minutes))


def business_today() -> date:
    return datetime.now(business_tz()).date()


def day_bounds(day: date) -> tuple[datetime, datetime]:
    """UTC-aware [start, end) of a business day."""
    tz = business_tz()
    start = datetime.combine(day, datetime.min.time(), tzinfo=tz)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


def _party(session: Session, party_id: int, *, for_new: bool) -> Party:
    """Any party can have activities: customers mostly, but also a supplier you
    need to call or a transporter you need to meet."""
    party = get_or_404(session, Party, party_id, "Party")
    if party.stage == PartyStage.MERGED:
        raise ValidationError(
            f"Party '{party.name}' was merged into #{party.merged_into_id}; "
            "use that party instead.",
            field="party_id",
        )
    if for_new:
        require_active(party, party.party_type.value.capitalize())
    return party


def resolve_salesperson(session: Session, user_id: int) -> User:
    """Only an active SALESPERSON account can be assigned work."""
    user = session.get(User, user_id)
    if user is None:
        raise ValidationError(f"User #{user_id} was not found.", field="assigned_salesperson_id")
    if user.role != UserRole.SALESPERSON:
        raise ValidationError(
            f"'{user.name}' is a {user.role.value} account; only SALESPERSON accounts can be "
            "assigned activities.",
            field="assigned_salesperson_id",
        )
    if user.status != RecordStatus.ACTIVE:
        raise ValidationError(
            f"Salesperson '{user.name}' is inactive.", field="assigned_salesperson_id"
        )
    return user


def _resolve_location(session: Session, location_id: int) -> Location:
    location = session.get(Location, location_id)
    if location is None:
        raise ValidationError(f"Location #{location_id} was not found.", field="location_id")
    require_active(location, "Location")
    return location


def location_snapshot(location: Location) -> dict:
    """Freeze the address at creation time so history stays accurate."""
    return {
        "location_id": location.id,
        "label": location.label,
        "address_line_1": location.address_line_1,
        "address_line_2": location.address_line_2,
        "city": location.city,
        "state": location.state,
        "country": location.country,
        "pincode": location.pincode,
        "latitude": str(location.latitude) if location.latitude is not None else None,
        "longitude": str(location.longitude) if location.longitude is not None else None,
    }


def default_party_location(session: Session, party_id: int) -> Location | None:
    """Primary location of the party, used to pre-fill a visit."""
    from app.models.party import PartyLocation

    row = session.execute(
        select(Location)
        .join(PartyLocation, PartyLocation.location_id == Location.id)
        .where(PartyLocation.party_id == party_id)
        .order_by(PartyLocation.is_primary.desc(), PartyLocation.id)
        .limit(1)
    ).scalar_one_or_none()
    return row


def _validate_related_inquiry(session: Session, inquiry_id: int | None, party: Party) -> None:
    if inquiry_id is None:
        return
    inquiry = session.get(Inquiry, inquiry_id)
    if inquiry is None:
        raise ValidationError(f"Inquiry #{inquiry_id} was not found.", field="related_inquiry_id")
    if (
        party.party_type == PartyType.CUSTOMER
        and inquiry.inquiry_type == InquiryType.CUSTOMER
        and inquiry.customer_detail is not None
        and inquiry.customer_detail.customer_id != party.id
    ):
        raise ValidationError(
            f"Inquiry #{inquiry_id} belongs to another customer.",
            field="related_inquiry_id",
        )


def create_activity(session: Session, payload: ActivityCreate, user_id: int) -> Activity:
    # The party either exists or is created here as a PROSPECT in the same
    # transaction - a cold call should not need a detour through the party form.
    if payload.new_party is not None:
        party = party_service.quick_create_party(
            session,
            payload.new_party,
            party_type=payload.new_party.party_type or PartyType.CUSTOMER,
            user_id=user_id,
        )
    else:
        party = _party(session, payload.party_id, for_new=True)
    _validate_related_inquiry(session, payload.related_inquiry_id, party)

    salesperson = (
        resolve_salesperson(session, payload.assigned_salesperson_id)
        if payload.assigned_salesperson_id is not None
        else None
    )

    location: Location | None = None
    snapshot: dict | None = None
    if payload.location_id is not None:
        location = _resolve_location(session, payload.location_id)
    elif payload.new_location is not None:
        location = party_service.create_location(session, payload.new_location, user_id)
    elif payload.location_text:
        # Address we only know as text ("his shop, Gondal Road"). No location row,
        # but the snapshot still drives display and the maps fallback.
        snapshot = {"label": payload.location_text, "city": None}
    elif payload.activity_type in LOCATION_REQUIRED_TYPES:
        location = default_party_location(session, party.id)
        if location is None:
            raise ValidationError(
                f"{payload.activity_type.value} activities need a location, and "
                f"'{party.name}' has none on record yet. Add an address, pick a "
                "location, or type where to go.",
                field="location_id",
            )

    parent: Activity | None = None
    if payload.parent_activity_id is not None:
        parent = get_or_404(session, Activity, payload.parent_activity_id, "Activity")
        if parent.party_id != party.id:
            raise ValidationError(
                "A follow-up must belong to the same party as its parent activity.",
                field="parent_activity_id",
            )

    activity = Activity(
        party_id=party.id,
        activity_type=payload.activity_type,
        status=payload.status,
        subject=payload.subject,
        scheduled_at=payload.scheduled_at,
        completed_at=payload.completed_at,
        outcome=payload.outcome,
        note=payload.note,
        parent_activity_id=parent.id if parent else None,
        related_inquiry_id=payload.related_inquiry_id,
        created_by=user_id,
        assigned_salesperson_id=salesperson.id if salesperson else None,
        completed_by=user_id if payload.status == ActivityStatus.COMPLETED else None,
        location_id=location.id if location else None,
        location_snapshot=location_snapshot(location) if location else snapshot,
    )
    session.add(activity)
    session.flush()
    audit.record(
        session,
        user_id=user_id,
        entity_type="activity",
        entity_id=activity.id,
        action=AuditAction.CREATE,
        new_value={
            "party_id": party.id,
            "party_type": party.party_type.value,
            "activity_type": activity.activity_type.value,
            "status": activity.status.value,
            "scheduled_at": activity.scheduled_at.isoformat() if activity.scheduled_at else None,
            "parent_activity_id": activity.parent_activity_id,
            "assigned_salesperson_id": activity.assigned_salesperson_id,
            "location_id": activity.location_id,
        },
    )
    return activity


def update_activity(
    session: Session, activity_id: int, payload: ActivityUpdate, user_id: int
) -> Activity:
    activity = get_or_404(session, Activity, activity_id, "Activity")
    data = payload.model_dump(exclude_unset=True)

    if activity.status in (ActivityStatus.COMPLETED, ActivityStatus.CANCELLED):
        raise ConflictError(
            f"Activity #{activity.id} is {activity.status.value} and can no longer be edited."
        )

    new_status = data.get("status")
    if new_status is not None and new_status != activity.status:
        if new_status not in ACTIVITY_TRANSITIONS[activity.status]:
            allowed = ", ".join(sorted(s.value for s in ACTIVITY_TRANSITIONS[activity.status]))
            raise ValidationError(
                f"Activity #{activity.id} cannot move from {activity.status.value} to "
                f"{new_status.value}. Allowed: {allowed or 'none'}.",
                field="status",
            )
        if new_status == ActivityStatus.COMPLETED:
            raise ValidationError(
                "Use POST /activities/{id}/complete so that an outcome is recorded.",
                field="status",
            )
        if new_status == ActivityStatus.IN_PROGRESS and activity.started_at is None:
            activity.started_at = datetime.now(UTC)

    if "related_inquiry_id" in data:
        _validate_related_inquiry(session, data["related_inquiry_id"], activity.party)

    if "assigned_salesperson_id" in data and data["assigned_salesperson_id"] is not None:
        resolve_salesperson(session, data["assigned_salesperson_id"])

    if data.get("location_id") is not None:
        location = _resolve_location(session, data["location_id"])
        activity.location_snapshot = location_snapshot(location)

    target_type = data.get("activity_type", activity.activity_type)
    target_location = data.get("location_id", activity.location_id)
    if target_type in LOCATION_REQUIRED_TYPES and target_location is None:
        raise ValidationError(
            f"{target_type.value} activities require a location.", field="location_id"
        )

    changes = apply_patch(
        activity,
        data,
        {
            "activity_type",
            "subject",
            "scheduled_at",
            "started_at",
            "note",
            "outcome",
            "status",
            "related_inquiry_id",
            "assigned_salesperson_id",
            "location_id",
        },
    )
    action = AuditAction.UPDATE
    if "status" in changes:
        action = AuditAction.STATUS_CHANGE
    elif "assigned_salesperson_id" in changes:
        action = AuditAction.ASSIGN
    audit.record_changes(
        session,
        user_id=user_id,
        entity_type="activity",
        entity_id=activity.id,
        changes=changes,
        action=action,
    )
    return activity


def complete_activity(
    session: Session,
    activity_id: int,
    payload: ActivityCompleteRequest,
    user_id: int,
    *,
    activity: Activity | None = None,
) -> tuple[Activity, Activity | None]:
    """Record the outcome. ``activity`` may be passed in by the salesperson
    service, which has already verified ownership."""
    activity = activity or get_or_404(session, Activity, activity_id, "Activity")
    if activity.status == ActivityStatus.COMPLETED:
        raise ConflictError(f"Activity #{activity.id} is already completed.")
    if activity.status == ActivityStatus.CANCELLED:
        raise ConflictError(f"Activity #{activity.id} was cancelled and cannot be completed.")

    old_status = activity.status
    activity.status = ActivityStatus.COMPLETED
    activity.completed_at = payload.completed_at or datetime.now(UTC)
    activity.outcome = payload.outcome
    activity.outcome_code = payload.outcome_code or ActivityOutcome.COMPLETED
    activity.completed_by = user_id
    if activity.started_at is None:
        activity.started_at = activity.scheduled_at or activity.completed_at
    session.flush()

    audit.record(
        session,
        user_id=user_id,
        entity_type="activity",
        entity_id=activity.id,
        action=AuditAction.COMPLETE,
        old_value={"status": old_status.value},
        new_value={
            "status": activity.status.value,
            "completed_at": activity.completed_at.isoformat(),
            "outcome_code": activity.outcome_code.value,
            "outcome": payload.outcome,
            "completed_by": user_id,
        },
    )

    follow_up: Activity | None = None
    if payload.follow_up is not None:
        follow_up = create_activity(
            session,
            ActivityCreate(
                party_id=activity.party_id,
                activity_type=payload.follow_up.activity_type,
                subject=payload.follow_up.subject,
                scheduled_at=payload.follow_up.scheduled_at,
                note=payload.follow_up.note,
                parent_activity_id=activity.id,
                related_inquiry_id=activity.related_inquiry_id,
                status=ActivityStatus.SCHEDULED,
                # A follow-up stays with the same field user by default.
                assigned_salesperson_id=activity.assigned_salesperson_id,
                location_id=(
                    activity.location_id
                    if payload.follow_up.activity_type in LOCATION_REQUIRED_TYPES
                    else None
                ),
            ),
            user_id,
        )
    return activity, follow_up


def _scope_filter(stmt: Select, scope: str | None) -> Select:
    if not scope:
        return stmt
    today = business_today()
    start, end = day_bounds(today)
    if scope == "today":
        return stmt.where(
            Activity.status.in_(OPEN_ACTIVITY_STATUSES),
            Activity.scheduled_at >= start,
            Activity.scheduled_at < end,
        )
    if scope == "upcoming":
        return stmt.where(
            Activity.status.in_(OPEN_ACTIVITY_STATUSES), Activity.scheduled_at >= start
        )
    if scope == "overdue":
        return stmt.where(
            Activity.status.in_(OPEN_ACTIVITY_STATUSES), Activity.scheduled_at < start
        )
    if scope == "history":
        return stmt.where(Activity.status.in_([ActivityStatus.COMPLETED, ActivityStatus.CANCELLED]))
    raise ValidationError("scope must be one of: today, upcoming, overdue, history.", field="scope")


def list_activities(
    session: Session,
    params: PageParams,
    *,
    party_id: int | None = None,
    activity_type: ActivityType | None = None,
    statuses: Sequence[ActivityStatus] | None = None,
    assigned_salesperson_id: int | None = None,
    unassigned_only: bool = False,
    scope: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    related_inquiry_id: int | None = None,
    q: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> tuple[Sequence[Activity], int]:
    stmt = select(Activity)
    if party_id is not None:
        stmt = stmt.where(Activity.party_id == party_id)
    if activity_type is not None:
        stmt = stmt.where(Activity.activity_type == activity_type)
    if statuses:
        stmt = stmt.where(Activity.status.in_(list(statuses)))
    if related_inquiry_id is not None:
        stmt = stmt.where(Activity.related_inquiry_id == related_inquiry_id)
    if assigned_salesperson_id is not None:
        stmt = stmt.where(Activity.assigned_salesperson_id == assigned_salesperson_id)
    if unassigned_only:
        stmt = stmt.where(Activity.assigned_salesperson_id.is_(None))
    stmt = _scope_filter(stmt, scope)
    if date_from:
        start, _ = day_bounds(date_from)
        stmt = stmt.where(
            or_(
                Activity.scheduled_at >= start,
                Activity.completed_at >= start,
            )
        )
    if date_to:
        _, end = day_bounds(date_to)
        stmt = stmt.where(
            or_(
                Activity.scheduled_at < end,
                Activity.completed_at < end,
            )
        )
    if q:
        like = f"%{q}%"
        stmt = stmt.join(Party, Party.id == Activity.party_id).where(
            or_(
                Party.name.ilike(like),
                Activity.subject.ilike(like),
                Activity.note.ilike(like),
                Activity.outcome.ilike(like),
            )
        )
    stmt = apply_sort(
        stmt,
        sort_by,
        sort_dir,
        {
            "scheduled_at": Activity.scheduled_at,
            "created_at": Activity.created_at,
            "completed_at": Activity.completed_at,
            "id": Activity.id,
        },
        "scheduled_at" if scope in {"today", "upcoming", "overdue"} else "created_at",
    )
    if scope in {"today", "upcoming", "overdue"} and not sort_by:
        stmt = stmt.order_by(None).order_by(Activity.scheduled_at.asc())
    return paginate(session, stmt, params)


def get_activity(session: Session, activity_id: int) -> Activity:
    activity = session.get(Activity, activity_id, options=[selectinload(Activity.follow_ups)])
    if activity is None:
        raise NotFoundError(f"Activity #{activity_id} was not found.")
    return activity


# --------------------------------------------------------------------------- #
# Scheduling conflicts, workload and calendar (admin side)
# --------------------------------------------------------------------------- #
def find_conflicts(
    session: Session,
    *,
    salesperson_id: int,
    scheduled_at: datetime,
    exclude_activity_id: int | None = None,
) -> ConflictCheckResult:
    """Warn (never block) when a field user is double booked."""
    window = timedelta(minutes=settings.schedule_conflict_window_minutes)
    stmt = (
        select(Activity)
        .where(
            Activity.assigned_salesperson_id == salesperson_id,
            Activity.status.in_(OPEN_ACTIVITY_STATUSES),
            Activity.scheduled_at.is_not(None),
            Activity.scheduled_at > scheduled_at - window,
            Activity.scheduled_at < scheduled_at + window,
        )
        .order_by(Activity.scheduled_at)
    )
    if exclude_activity_id is not None:
        stmt = stmt.where(Activity.id != exclude_activity_id)

    conflicts = [
        ScheduleConflict(
            activity_id=row.id,
            scheduled_at=row.scheduled_at,
            activity_type=row.activity_type,
            customer_name=row.party.name,
            minutes_apart=int(abs((row.scheduled_at - scheduled_at).total_seconds()) // 60),
        )
        for row in session.execute(stmt).scalars().all()
    ]
    return ConflictCheckResult(has_conflict=bool(conflicts), conflicts=conflicts)


def salesperson_workload(session: Session, *, include_inactive: bool = False) -> list[dict]:
    """Per-salesperson counts for the admin's 'Salespeople' screen."""
    today = business_today()
    day_start, day_end = day_bounds(today)

    stmt = select(User).where(User.role == UserRole.SALESPERSON).order_by(User.name)
    if not include_inactive:
        stmt = stmt.where(User.status == RecordStatus.ACTIVE)
    people = session.execute(stmt).scalars().all()
    if not people:
        return []

    ids = [person.id for person in people]
    rows = session.execute(
        select(
            Activity.assigned_salesperson_id,
            Activity.status,
            Activity.scheduled_at,
        ).where(Activity.assigned_salesperson_id.in_(ids))
    ).all()

    summary = {
        person.id: {
            "today_total": 0,
            "today_completed": 0,
            "today_pending": 0,
            "upcoming": 0,
            "overdue": 0,
        }
        for person in people
    }
    for salesperson_id, status, scheduled_at in rows:
        bucket = summary[salesperson_id]
        is_today = scheduled_at is not None and day_start <= scheduled_at < day_end
        is_open = status in OPEN_ACTIVITY_STATUSES
        if is_today:
            bucket["today_total"] += 1
            if status == ActivityStatus.COMPLETED:
                bucket["today_completed"] += 1
            elif is_open:
                bucket["today_pending"] += 1
        elif is_open and scheduled_at is not None:
            if scheduled_at >= day_end:
                bucket["upcoming"] += 1
            else:
                bucket["overdue"] += 1

    return [
        {
            "id": person.id,
            "name": person.name,
            "email": person.email,
            "phone": person.phone,
            "status": person.status.value,
            **summary[person.id],
        }
        for person in people
    ]


def calendar(
    session: Session,
    *,
    date_from: date,
    date_to: date,
    salesperson_id: int | None = None,
) -> Sequence[Activity]:
    """Scheduled activities in a date range, for the admin assignment calendar."""
    start, _ = day_bounds(date_from)
    _, end = day_bounds(date_to)
    stmt = (
        select(Activity)
        .where(Activity.scheduled_at >= start, Activity.scheduled_at < end)
        .order_by(Activity.scheduled_at)
    )
    if salesperson_id is not None:
        stmt = stmt.where(Activity.assigned_salesperson_id == salesperson_id)
    return session.execute(stmt).scalars().all()
