"""Location master endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import SessionDep, StaffUser
from app.core.pagination import Page, PageParams, page_params
from app.models.enums import RecordStatus
from app.models.party import Location
from app.schemas.party import LocationCreate, LocationOut, LocationUpdate
from app.services import parties as service
from app.services.common import get_or_404

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=Page[LocationOut])
def list_locations(
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, description="Label, city, state, address or pincode"),
    city: str | None = None,
    state: str | None = None,
    party_id: int | None = None,
    status: RecordStatus | None = None,
    sort_by: str | None = Query(None, pattern="^(city|label|created_at|id)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
) -> Page[LocationOut]:
    rows, total = service.list_locations(
        session,
        params,
        q=q,
        city=city,
        state=state,
        party_id=party_id,
        status=status,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return Page.build([LocationOut.model_validate(row) for row in rows], total, params)


@router.post("", response_model=LocationOut, status_code=201)
def create_location(payload: LocationCreate, session: SessionDep, user: StaffUser) -> LocationOut:
    return LocationOut.model_validate(service.create_location(session, payload, user.id))


@router.get("/{location_id}", response_model=LocationOut)
def get_location(location_id: int, session: SessionDep, _: StaffUser) -> LocationOut:
    return LocationOut.model_validate(get_or_404(session, Location, location_id, "Location"))


@router.patch("/{location_id}", response_model=LocationOut)
def update_location(
    location_id: int, payload: LocationUpdate, session: SessionDep, user: StaffUser
) -> LocationOut:
    return LocationOut.model_validate(
        service.update_location(session, location_id, payload, user.id)
    )
