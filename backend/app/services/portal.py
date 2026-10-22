"""A party's public identity: the opaque code their portal links are built on.

One code per party, used by every public link they are ever sent - the bids
they are invited to and the enquiries they raise themselves. It stands in for
the row id so that nothing public can be guessed by counting, and holding one
proves only "I am the party this code belongs to".

This lives apart from both bids and enquiries because it belongs to neither.
"""

from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.enums import RecordStatus
from app.models.party import Party


def portal_code(session: Session, party: Party) -> str:
    """The party's permanent, unguessable key for the portal.

    Issued on first use rather than for all 1,000 parties up front, so a party
    that has never been given a link has no public surface at all.
    """
    if party.portal_code:
        return party.portal_code
    while True:
        candidate = secrets.token_urlsafe(16)
        taken = session.scalar(select(Party.id).where(Party.portal_code == candidate))
        if not taken:
            break
    party.portal_code = candidate
    session.flush()
    return candidate


def party_by_code(session: Session, code: str) -> Party:
    """Resolve a portal code. Anything unrecognised is simply 'not found'.

    No distinction is made between a wrong code, a merged party and an inactive
    one: a stranger probing the portal learns nothing either way.
    """
    party = (
        session.scalar(
            select(Party).where(
                Party.portal_code == code,
                Party.status == RecordStatus.ACTIVE,
                Party.merged_into_id.is_(None),
            )
        )
        if code
        else None
    )
    if party is None:
        raise NotFoundError("This link is not valid.")
    return party
