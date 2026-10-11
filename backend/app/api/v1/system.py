"""Dashboard, global search, enum metadata and audit log endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import AdminUser, SessionDep, StaffUser
from app.core.pagination import Page, PageParams, page_params
from app.models import enums
from app.schemas.dashboard import AuditLogOut, DashboardOut, SearchResults
from app.services import audit as audit_service
from app.services import dashboard as service
from app.services.activities import ACTIVITY_TRANSITIONS
from app.services.parties import ALLOWED_RELATIONSHIPS

router = APIRouter(tags=["system"])


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(session: SessionDep, _: StaffUser) -> DashboardOut:
    return service.dashboard(session)


@router.get("/search", response_model=SearchResults)
def search(
    session: SessionDep,
    _: StaffUser,
    q: str = Query(..., min_length=1, description="Free text across parties and product masters"),
    limit: int = Query(8, ge=1, le=25),
) -> SearchResults:
    return service.search(session, q, limit=limit)


@router.get("/meta/enums")
def meta_enums(_: StaffUser) -> dict:
    """Every enum and state-machine rule the UI needs, so it never hardcodes them."""
    return {
        "record_status": [e.value for e in enums.RecordStatus],
        "user_role": [e.value for e in enums.UserRole],
        "party_type": [e.value for e in enums.PartyType],
        "location_type": [e.value for e in enums.LocationType],
        "party_product_relationship": [e.value for e in enums.PartyProductRelationship],
        "inquiry_type": [e.value for e in enums.InquiryType],
        "inquiry_status": [e.value for e in enums.InquiryStatus],
        "quantity_unit": [e.value for e in enums.QuantityUnit],
        "activity_type": [e.value for e in enums.ActivityType],
        "activity_status": [e.value for e in enums.ActivityStatus],
        "rules": {
            "activity_transitions": {
                status.value: sorted(target.value for target in targets)
                for status, targets in ACTIVITY_TRANSITIONS.items()
            },
            "party_product_relationships": {
                party_type.value: sorted(rel.value for rel in rels)
                for party_type, rels in ALLOWED_RELATIONSHIPS.items()
            },
        },
    }


@router.get("/audit-logs", response_model=Page[AuditLogOut], tags=["audit"])
def list_audit_logs(
    session: SessionDep,
    _: AdminUser,
    params: PageParams = Depends(page_params),
    entity_type: str | None = None,
    entity_id: int | None = None,
    user_id: int | None = None,
    sort_by: str | None = Query(None, pattern="^(created_at|id)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
) -> Page[AuditLogOut]:
    rows, total = audit_service.list_logs(
        session,
        params,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return Page.build([AuditLogOut.model_validate(row) for row in rows], total, params)
