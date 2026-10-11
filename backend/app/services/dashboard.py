"""Dashboard metrics, global search and the 360-degree party view."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.enums import (
    InquiryStatus,
    InquiryType,
    PartyStage,
    PartyType,
    RecordStatus,
)
from app.models.inquiry import Inquiry
from app.models.masters import Grade, Manufacturer, Material, Product
from app.models.note import Note
from app.models.party import Party
from app.schemas.dashboard import (
    DashboardCounts,
    DashboardOut,
    Party360Out,
    PartyStats,
    SearchHit,
    SearchResults,
)
from app.schemas.inquiry import TimelineEvent
from app.services import activities as activity_service
from app.services import inquiry_queries
from app.services.inquiries import DETAIL_LOADERS
from app.services.parties import get_party


def _count_open(session: Session, inquiry_type: InquiryType) -> int:
    return (
        session.scalar(
            select(func.count(Inquiry.id)).where(
                Inquiry.inquiry_type == inquiry_type, Inquiry.status == InquiryStatus.ACTIVE
            )
        )
        or 0
    )


def _count_active(session: Session, party_type: PartyType) -> int:
    return (
        session.scalar(
            select(func.count(Party.id)).where(
                Party.party_type == party_type, Party.status == RecordStatus.ACTIVE
            )
        )
        or 0
    )


def dashboard(session: Session) -> DashboardOut:
    today = activity_service.business_today()
    day_start, day_end = activity_service.day_bounds(today)
    week_end = day_start + timedelta(days=8)
    open_activity = Activity.status.in_(activity_service.OPEN_ACTIVITY_STATUSES)

    todays = (
        session.execute(
            select(Activity)
            .where(
                open_activity, Activity.scheduled_at >= day_start, Activity.scheduled_at < day_end
            )
            .order_by(Activity.scheduled_at)
            .limit(25)
        )
        .scalars()
        .all()
    )

    upcoming = (
        session.execute(
            select(Activity)
            .where(
                open_activity, Activity.scheduled_at >= day_end, Activity.scheduled_at < week_end
            )
            .order_by(Activity.scheduled_at)
            .limit(15)
        )
        .scalars()
        .all()
    )

    overdue = (
        session.scalar(
            select(func.count(Activity.id)).where(open_activity, Activity.scheduled_at < day_start)
        )
        or 0
    )

    recent_customers = (
        session.execute(
            select(Party)
            .where(Party.party_type == PartyType.CUSTOMER)
            .order_by(Party.created_at.desc())
            .limit(6)
        )
        .scalars()
        .all()
    )

    recent_inquiries = (
        session.execute(
            select(Inquiry).options(*DETAIL_LOADERS).order_by(Inquiry.created_at.desc()).limit(8)
        )
        .scalars()
        .all()
    )

    recently_closed = (
        session.execute(
            select(Inquiry)
            .options(*DETAIL_LOADERS)
            .where(Inquiry.status == InquiryStatus.CLOSED)
            .order_by(Inquiry.closed_at.desc())
            .limit(8)
        )
        .scalars()
        .all()
    )

    counts = DashboardCounts(
        open_customer_inquiries=_count_open(session, InquiryType.CUSTOMER),
        open_supplier_inquiries=_count_open(session, InquiryType.SUPPLIER),
        open_transport_inquiries=_count_open(session, InquiryType.TRANSPORT),
        todays_activities=len(todays),
        overdue_activities=overdue,
        upcoming_followups=len(upcoming),
        active_customers=_count_active(session, PartyType.CUSTOMER),
        active_suppliers=_count_active(session, PartyType.SUPPLIER),
        active_transporters=_count_active(session, PartyType.TRANSPORTER),
        active_products=session.scalar(
            select(func.count(Product.id)).where(Product.status == RecordStatus.ACTIVE)
        )
        or 0,
        prospects=session.scalar(
            select(func.count(Party.id)).where(Party.stage == PartyStage.PROSPECT)
        )
        or 0,
    )

    return DashboardOut(
        counts=counts,
        todays_activities=list(todays),
        upcoming_followups=list(upcoming),
        recent_customers=list(recent_customers),
        recent_inquiries=inquiry_queries.build_list_items(session, recent_inquiries),
        recently_closed_inquiries=inquiry_queries.build_list_items(session, recently_closed),
    )


# --------------------------------------------------------------------------- #
# Global search
# --------------------------------------------------------------------------- #
def search(session: Session, q: str, *, limit: int = 8) -> SearchResults:
    term = q.strip()
    if not term:
        return SearchResults(query=q)
    like = f"%{term}%"

    parties = (
        session.execute(
            select(Party)
            .where(
                or_(
                    Party.name.ilike(like),
                    Party.phone.ilike(like),
                    Party.gst_number.ilike(like),
                    Party.contact_person.ilike(like),
                )
            )
            .order_by(Party.status, Party.name)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    products = (
        session.execute(
            select(Product)
            .join(Material, Material.id == Product.material_id)
            .join(Grade, Grade.id == Product.grade_id)
            .join(Manufacturer, Manufacturer.id == Product.manufacturer_id)
            .where(
                or_(
                    Product.display_name.ilike(like),
                    Material.name.ilike(like),
                    Grade.name.ilike(like),
                    Manufacturer.name.ilike(like),
                )
            )
            .order_by(Product.status, Product.display_name)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    materials = (
        session.execute(
            select(Material).where(Material.name.ilike(like)).order_by(Material.name).limit(limit)
        )
        .scalars()
        .all()
    )
    grades = (
        session.execute(
            select(Grade).where(Grade.name.ilike(like)).order_by(Grade.name).limit(limit)
        )
        .scalars()
        .all()
    )
    manufacturers = (
        session.execute(
            select(Manufacturer)
            .where(or_(Manufacturer.name.ilike(like), Manufacturer.code.ilike(like)))
            .order_by(Manufacturer.name)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    results = SearchResults(
        query=term,
        parties=[
            SearchHit(
                entity="party",
                id=party.id,
                label=party.name,
                sublabel=party.party_type.value.title(),
                status=party.status.value,
            )
            for party in parties
        ],
        products=[
            SearchHit(
                entity="product",
                id=product.id,
                label=product.display_name,
                sublabel=(
                    f"{product.material.name} / {product.grade.name} / {product.manufacturer.name}"
                ),
                status=product.status.value,
            )
            for product in products
        ],
        materials=[
            SearchHit(entity="material", id=m.id, label=m.name, status=m.status.value)
            for m in materials
        ],
        grades=[
            SearchHit(
                entity="grade",
                id=g.id,
                label=g.name,
                sublabel=g.material.name,
                status=g.status.value,
            )
            for g in grades
        ],
        manufacturers=[
            SearchHit(
                entity="manufacturer",
                id=m.id,
                label=m.name,
                sublabel=m.code,
                status=m.status.value,
            )
            for m in manufacturers
        ],
    )
    results.total = sum(
        len(group)
        for group in (
            results.parties,
            results.products,
            results.materials,
            results.grades,
            results.manufacturers,
        )
    )
    return results


# --------------------------------------------------------------------------- #
# Party 360
# --------------------------------------------------------------------------- #
def _party_timeline(
    session: Session,
    party: Party,
    inquiry_items: Sequence,
    activities: Sequence[Activity],
    notes: Sequence[Note],
) -> list[TimelineEvent]:
    events: list[TimelineEvent] = [
        TimelineEvent(
            at=party.created_at,
            kind="party_created",
            title=f"{party.party_type.value.title()} added",
            description=party.name,
            ref_type="party",
            ref_id=party.id,
        )
    ]
    for item in inquiry_items:
        events.append(
            TimelineEvent(
                at=item.created_at,
                kind="inquiry",
                title=f"{item.inquiry_type.value.title()} inquiry #{item.id}",
                description=(
                    f"{item.quantity} {item.unit.value if item.unit else ''} "
                    f"{item.product_name or ''}".strip()
                ),
                actor=item.created_by_name,
                ref_type="inquiry",
                ref_id=item.id,
            )
        )
        if item.closed_at:
            events.append(
                TimelineEvent(
                    at=item.closed_at,
                    kind="inquiry_closed",
                    title=f"Inquiry #{item.id} closed",
                    ref_type="inquiry",
                    ref_id=item.id,
                )
            )
    for activity in activities:
        at = activity.completed_at or activity.scheduled_at or activity.created_at
        events.append(
            TimelineEvent(
                at=at,
                kind="activity",
                title=f"{activity.activity_type.value.title()} ({activity.status.value})",
                description=activity.outcome or activity.note or activity.subject,
                actor=activity.creator.name if activity.creator else None,
                ref_type="activity",
                ref_id=activity.id,
            )
        )
    for note in notes:
        events.append(
            TimelineEvent(
                at=note.created_at,
                kind="note",
                title="Note added",
                description=note.note,
                actor=note.creator.name if note.creator else None,
                ref_type="note",
                ref_id=note.id,
            )
        )
    events.sort(key=lambda event: event.at, reverse=True)
    return events


def party_360(
    session: Session, party_id: int, *, expected_type: PartyType | None = None
) -> Party360Out:
    party = get_party(session, party_id, expected_type=expected_type)

    open_inquiries = inquiry_queries.inquiries_for_party(
        session, party.id, status=InquiryStatus.ACTIVE
    )
    history = inquiry_queries.inquiries_for_party(session, party.id, status=InquiryStatus.CLOSED)

    # Activities now hang off any party: a cold supplier call belongs on the
    # supplier's page, where the trader will look for it.
    activities: Sequence[Activity] = (
        session.execute(
            select(Activity)
            .where(Activity.party_id == party.id)
            .order_by(
                func.coalesce(Activity.completed_at, Activity.scheduled_at).desc(),
                Activity.id.desc(),
            )
            .limit(40)
        )
        .scalars()
        .all()
    )
    upcoming = [
        activity
        for activity in activities
        if activity.status in activity_service.OPEN_ACTIVITY_STATUSES
    ]
    upcoming.sort(key=lambda a: (a.scheduled_at is None, a.scheduled_at))

    notes = (
        session.execute(
            select(Note).where(Note.party_id == party.id).order_by(Note.created_at.desc()).limit(50)
        )
        .scalars()
        .all()
    )

    stats = PartyStats(
        open_inquiries=len(open_inquiries),
        closed_inquiries=len(history),
        activities=len(activities),
        upcoming_activities=len(upcoming),
        notes=len(notes),
    )

    return Party360Out(
        party=party,
        stats=stats,
        open_inquiries=open_inquiries,
        inquiry_history=history,
        activities=list(activities),
        upcoming_activities=list(upcoming),
        notes=list(notes),
        timeline=_party_timeline(session, party, open_inquiries + history, activities, notes),
    )
