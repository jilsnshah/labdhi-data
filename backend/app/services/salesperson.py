"""Field-app services.

Every query here is scoped by ``assigned_salesperson_id == current_user.id``.
The salesperson id is always taken from the authenticated token - never from the
request - and an activity belonging to somebody else is reported as *not found*
so the API cannot be used to discover other people's work.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import quote_plus

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import salesperson_followup_types, settings
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password, verify_password
from app.models.activity import Activity
from app.models.enums import ActivityStatus, ActivityType, AuditAction
from app.models.party import Location
from app.models.user import User
from app.schemas.activity import LOCATION_REQUIRED_TYPES, ActivityCompleteRequest
from app.schemas.salesperson import (
    ActivityCustomerView,
    ActivityLocationView,
    CompleteActivityRequest,
    FollowUpRequest,
    SalespersonActivity,
    SalespersonDashboard,
    SalespersonDayCounts,
    SalespersonProfile,
)
from app.services import activities as activity_service
from app.services import audit

MAPS_DIRECTIONS = "https://www.google.com/maps/dir/?api=1&travelmode=driving&destination="

OPEN_STATUSES = [ActivityStatus.SCHEDULED, ActivityStatus.IN_PROGRESS]
CLOSED_STATUSES = [ActivityStatus.COMPLETED, ActivityStatus.CANCELLED]


# --------------------------------------------------------------------------- #
# View models
# --------------------------------------------------------------------------- #
def _address_parts(data: dict) -> list[str]:
    keys = ("label", "address_line_1", "address_line_2", "city", "state", "pincode")
    return [str(data[key]) for key in keys if data.get(key)]


def _coordinate(value: object) -> str | None:
    """Trim stored NUMERIC(9,6) padding so maps links stay readable."""
    if value in (None, ""):
        return None
    try:
        return format(Decimal(str(value)).normalize(), "f")
    except (InvalidOperation, ValueError):
        return None


def _location_view(activity: Activity) -> ActivityLocationView | None:
    """Prefer the snapshot taken when the activity was created."""
    data: dict | None = activity.location_snapshot
    if data is None and activity.location is not None:
        data = activity_service.location_snapshot(activity.location)
    if not data:
        return None

    formatted = ", ".join(_address_parts(data)) or "Location"
    latitude = _coordinate(data.get("latitude"))
    longitude = _coordinate(data.get("longitude"))
    if latitude and longitude:
        destination = f"{latitude},{longitude}"
    else:
        destination = quote_plus(formatted)
    return ActivityLocationView(
        label=data.get("label"),
        address_line_1=data.get("address_line_1"),
        address_line_2=data.get("address_line_2"),
        city=data.get("city"),
        state=data.get("state"),
        pincode=data.get("pincode"),
        latitude=latitude,
        longitude=longitude,
        formatted=formatted,
        maps_url=f"{MAPS_DIRECTIONS}{destination}",
    )


def to_view(activity: Activity) -> SalespersonActivity:
    customer = activity.party
    return SalespersonActivity(
        id=activity.id,
        activity_type=activity.activity_type,
        status=activity.status,
        subject=activity.subject,
        scheduled_at=activity.scheduled_at,
        started_at=activity.started_at,
        completed_at=activity.completed_at,
        purpose=activity.note,
        completion_note=activity.outcome,
        outcome_code=activity.outcome_code,
        parent_activity_id=activity.parent_activity_id,
        is_visit=activity.activity_type == ActivityType.VISIT,
        can_complete=activity.status in OPEN_STATUSES,
        customer=ActivityCustomerView(
            name=customer.name,
            contact_person=customer.contact_person,
            phone=customer.phone,
        ),
        location=_location_view(activity),
    )


def profile(user: User) -> SalespersonProfile:
    return SalespersonProfile(
        id=user.id, name=user.name, email=user.email, phone=user.phone, role=user.role.value
    )


# --------------------------------------------------------------------------- #
# Scoped reads
# --------------------------------------------------------------------------- #
def _own(user: User):
    return Activity.assigned_salesperson_id == user.id


def get_own_activity(session: Session, user: User, activity_id: int) -> Activity:
    activity = session.scalar(select(Activity).where(Activity.id == activity_id, _own(user)))
    if activity is None:
        # Deliberately indistinguishable from a non-existent activity.
        raise NotFoundError(f"Activity #{activity_id} was not found.")
    return activity


def _day_window(day: date) -> tuple[datetime, datetime]:
    return activity_service.day_bounds(day)


def today_activities(session: Session, user: User, *, visits_only: bool = False) -> list[Activity]:
    start, end = _day_window(activity_service.business_today())
    stmt = (
        select(Activity)
        .where(_own(user), Activity.scheduled_at >= start, Activity.scheduled_at < end)
        .order_by(Activity.scheduled_at)
    )
    if visits_only:
        stmt = stmt.where(Activity.activity_type == ActivityType.VISIT)
    return list(session.execute(stmt).scalars().all())


def overdue_activities(session: Session, user: User) -> list[Activity]:
    start, _ = _day_window(activity_service.business_today())
    stmt = (
        select(Activity)
        .where(
            _own(user),
            Activity.status.in_(OPEN_STATUSES),
            Activity.scheduled_at.is_not(None),
            Activity.scheduled_at < start,
        )
        .order_by(Activity.scheduled_at)
    )
    return list(session.execute(stmt).scalars().all())


def upcoming_activities(session: Session, user: User, *, days: int = 30) -> list[Activity]:
    _, end = _day_window(activity_service.business_today())
    horizon = end + timedelta(days=days)
    stmt = (
        select(Activity)
        .where(
            _own(user),
            Activity.status.in_(OPEN_STATUSES),
            Activity.scheduled_at >= end,
            Activity.scheduled_at < horizon,
        )
        .order_by(Activity.scheduled_at)
    )
    return list(session.execute(stmt).scalars().all())


def history(session: Session, user: User, *, limit: int = 100) -> list[Activity]:
    stmt = (
        select(Activity)
        .where(_own(user), Activity.status.in_(CLOSED_STATUSES))
        .order_by(Activity.completed_at.desc().nullslast(), Activity.id.desc())
        .limit(limit)
    )
    return list(session.execute(stmt).scalars().all())


def dashboard(session: Session, user: User) -> SalespersonDashboard:
    today = today_activities(session, user)
    overdue = overdue_activities(session, user)
    upcoming = upcoming_activities(session, user)

    pending = [item for item in today if item.status in OPEN_STATUSES]
    counts = SalespersonDayCounts(
        today_total=len(today),
        today_pending=len(pending),
        today_completed=len([i for i in today if i.status == ActivityStatus.COMPLETED]),
        today_visits=len([i for i in today if i.activity_type == ActivityType.VISIT]),
        overdue=len(overdue),
        upcoming=len(upcoming),
    )
    next_up = pending[0] if pending else (overdue[0] if overdue else None)
    return SalespersonDashboard(
        profile=profile(user),
        counts=counts,
        today=[to_view(item) for item in today],
        overdue=[to_view(item) for item in overdue],
        next_activity=to_view(next_up) if next_up else None,
    )


def views(activities: Sequence[Activity]) -> list[SalespersonActivity]:
    return [to_view(activity) for activity in activities]


# --------------------------------------------------------------------------- #
# Scoped writes
# --------------------------------------------------------------------------- #
def complete(
    session: Session, user: User, activity_id: int, payload: CompleteActivityRequest
) -> tuple[Activity, bool]:
    """Idempotent completion: a retried submission returns the same activity."""
    activity = get_own_activity(session, user, activity_id)

    if activity.status == ActivityStatus.COMPLETED:
        if activity.completed_by == user.id:
            return activity, True
        raise ConflictError(f"Activity #{activity.id} is already completed.")
    if activity.status == ActivityStatus.CANCELLED:
        raise ConflictError(
            f"Activity #{activity.id} was cancelled by the office and cannot be completed."
        )

    updated, _ = activity_service.complete_activity(
        session,
        activity.id,
        ActivityCompleteRequest(
            outcome=payload.completion_note,
            outcome_code=payload.outcome_code,
            completed_at=payload.completed_at,
            follow_up=None,
        ),
        user.id,
        activity=activity,
    )
    return updated, False


def start(session: Session, user: User, activity_id: int) -> Activity:
    """Mark an assigned activity as in progress (the only status move allowed)."""
    activity = get_own_activity(session, user, activity_id)
    if activity.status in (ActivityStatus.COMPLETED, ActivityStatus.CANCELLED):
        raise ConflictError(
            f"Activity #{activity.id} is {activity.status.value} and cannot be started."
        )
    if activity.status == ActivityStatus.IN_PROGRESS:
        return activity

    activity.status = ActivityStatus.IN_PROGRESS
    activity.started_at = datetime.now(UTC)
    audit.record(
        session,
        user_id=user.id,
        entity_type="activity",
        entity_id=activity.id,
        action=AuditAction.STATUS_CHANGE,
        old_value={"status": ActivityStatus.SCHEDULED.value},
        new_value={"status": activity.status.value, "source": "salesperson_app"},
    )
    return activity


def fix_location(session: Session, user: User, activity_id: int, latitude, longitude) -> Activity:
    """Let the field user pin the place they actually found.

    Missing coordinates on the location master get filled in. Existing ones are
    never overwritten from the field - the correction lands on this activity's
    snapshot and in the audit log for the desk to review.
    """
    activity = get_own_activity(session, user, activity_id)
    if activity.activity_type != ActivityType.VISIT:
        raise ValidationError("Only visits carry a location.", field="activity_id")

    snapshot = dict(activity.location_snapshot or {})
    old = {"latitude": snapshot.get("latitude"), "longitude": snapshot.get("longitude")}
    snapshot["latitude"] = str(latitude)
    snapshot["longitude"] = str(longitude)
    activity.location_snapshot = snapshot

    master_updated = False
    if activity.location_id is not None:
        location = session.get(Location, activity.location_id)
        if location is not None and (location.latitude is None or location.longitude is None):
            location.latitude = latitude
            location.longitude = longitude
            master_updated = True

    audit.record(
        session,
        user_id=user.id,
        entity_type="activity",
        entity_id=activity.id,
        action=AuditAction.UPDATE,
        old_value=old,
        new_value={
            "latitude": str(latitude),
            "longitude": str(longitude),
            "location_master_updated": master_updated,
            "source": "salesperson_app",
        },
    )
    return activity


def change_password(session: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise ValidationError("Current password is incorrect.", field="current_password")
    user.password_hash = hash_password(new_password)
    audit.record(
        session,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        action=AuditAction.UPDATE,
        new_value={"password_changed": True, "source": "salesperson_app"},
    )


def schedule_follow_up(
    session: Session, user: User, activity_id: int, payload: FollowUpRequest
) -> Activity:
    """Customer, assignee and parent are derived from the completed activity."""
    parent = get_own_activity(session, user, activity_id)

    allowed = salesperson_followup_types()
    if payload.activity_type.value not in allowed:
        raise ValidationError(
            f"You can only schedule: {', '.join(sorted(allowed))}.",
            field="activity_type",
        )
    if payload.scheduled_at < datetime.now(UTC) - timedelta(minutes=5):
        raise ValidationError("A follow-up must be scheduled in the future.", field="scheduled_at")
    if payload.scheduled_at > datetime.now(UTC) + timedelta(days=365):
        raise ValidationError("That date is too far ahead.", field="scheduled_at")

    location_id = parent.location_id if payload.activity_type in LOCATION_REQUIRED_TYPES else None
    if payload.activity_type in LOCATION_REQUIRED_TYPES and location_id is None:
        location = activity_service.default_party_location(session, parent.party_id)
        if location is None:
            raise ValidationError(
                "This customer has no address on record, so a visit cannot be scheduled "
                "from the app. Ask the office to add one.",
                field="activity_type",
            )
        location_id = location.id

    follow_up = Activity(
        party_id=parent.party_id,
        activity_type=payload.activity_type,
        status=ActivityStatus.SCHEDULED,
        subject=parent.subject,
        scheduled_at=payload.scheduled_at,
        note=payload.note,
        parent_activity_id=parent.id,
        related_inquiry_id=parent.related_inquiry_id,
        created_by=user.id,
        assigned_salesperson_id=user.id,
        location_id=location_id,
    )
    if location_id is not None:
        location = session.get(Location, location_id)
        if location is not None:
            follow_up.location_snapshot = activity_service.location_snapshot(location)
    session.add(follow_up)
    session.flush()

    audit.record(
        session,
        user_id=user.id,
        entity_type="activity",
        entity_id=follow_up.id,
        action=AuditAction.CREATE,
        new_value={
            "source": "salesperson_app",
            "party_id": follow_up.party_id,
            "activity_type": follow_up.activity_type.value,
            "scheduled_at": follow_up.scheduled_at.isoformat(),
            "parent_activity_id": parent.id,
            "assigned_salesperson_id": user.id,
        },
    )
    return follow_up


def timezone_offset_minutes() -> int:
    return settings.display_timezone_offset_minutes
