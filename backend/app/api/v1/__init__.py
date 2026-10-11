"""API v1 router aggregation."""

from fastapi import APIRouter, Depends

from app.api.v1 import (
    activities,
    auth,
    inquiries,
    locations,
    masters,
    notes,
    parties,
    products,
    salesperson,
    system,
)
from app.core.deps import require_staff

api_router = APIRouter()

# Auth is open to every role (the field app logs in here too).
api_router.include_router(auth.router)

# Back-office CRM: staff only. The router-level dependency means a newly added
# endpoint is closed to field accounts by default, on top of the per-route gates.
staff_only = [Depends(require_staff)]
for crm_router in (
    masters.router,
    products.router,
    locations.router,
    parties.router,
    inquiries.router,
    activities.router,
    notes.router,
    system.router,
):
    api_router.include_router(crm_router, dependencies=staff_only)

# Field app: salesperson accounts only, always scoped to the caller.
api_router.include_router(salesperson.router)

__all__ = ["api_router"]
