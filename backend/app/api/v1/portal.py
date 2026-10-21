"""The participants' side of a bid: public, unauthenticated, deliberately thin.

These are the only endpoints reachable without signing in. Everything is keyed
on an opaque portal code that stands in for the party, so a bid link carries no
row id and cannot be guessed by counting. Access is checked server-side on
every call: holding a code proves nothing beyond "this party was invited to
this bid".

Nothing here exposes the CRM. A caller sees their own name, the bids they were
invited to, their own quotation and the single best price standing - never
another party's name, another party's number, or anything else the desk holds.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Path, Request

from app.core.config import settings
from app.core.deps import SessionDep
from app.core.errors import RateLimitError
from app.schemas.bid import PortalBid, PortalHome, PortalQuoteRequest
from app.services import bids as service

router = APIRouter(prefix="/portal", tags=["portal"])

#: A portal code is 22 characters of url-safe base64.
CODE = Path(min_length=16, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")

#: Crude in-process throttle. The portal is the one public surface, so guessing
#: codes must be slow even though a code has 128 bits of entropy behind it.
_WINDOW_SECONDS = 60
_hits: dict[str, list[float]] = defaultdict(list)


def reset_throttle() -> None:
    """Forget every caller. For tests, and for a process that has been idle."""
    _hits.clear()


def _throttle(request: Request) -> None:
    caller = request.client.host if request.client else "unknown"
    now = time.monotonic()
    recent = [stamp for stamp in _hits[caller] if now - stamp < _WINDOW_SECONDS]
    recent.append(now)
    _hits[caller] = recent
    if len(recent) > settings.portal_rate_limit_per_minute:
        raise RateLimitError("Too many requests. Please wait a moment and try again.")


@router.get("/{code}", response_model=PortalHome)
def portal_home(request: Request, session: SessionDep, code: str = CODE) -> PortalHome:
    """Everything this party has been invited to, open first."""
    _throttle(request)
    return service.portal_home(session, code)


@router.get("/{code}/bids/{bid_id}", response_model=PortalBid)
def portal_bid(request: Request, session: SessionDep, bid_id: int, code: str = CODE) -> PortalBid:
    _throttle(request)
    return service.portal_bid(session, code, bid_id)


@router.post("/{code}/bids/{bid_id}/quote", response_model=PortalBid)
def submit_quote(
    request: Request,
    payload: PortalQuoteRequest,
    session: SessionDep,
    bid_id: int,
    code: str = CODE,
) -> PortalBid:
    """Place or replace this party's offer, while the bid is open."""
    _throttle(request)
    return service.submit_quote(session, code, bid_id, payload)
