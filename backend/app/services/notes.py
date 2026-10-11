"""Business note services."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.pagination import PageParams, apply_sort, paginate
from app.models.enums import AuditAction, PartyType
from app.models.note import Note
from app.models.party import Party
from app.schemas.note import NoteCreate, NoteUpdate
from app.services import audit
from app.services.common import get_or_404


def list_notes(
    session: Session,
    params: PageParams,
    *,
    party_id: int | None = None,
    party_type: PartyType | None = None,
    q: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> tuple[Sequence[Note], int]:
    stmt = select(Note)
    if party_id is not None:
        stmt = stmt.where(Note.party_id == party_id)
    if party_type is not None or q:
        stmt = stmt.join(Party, Party.id == Note.party_id)
    if party_type is not None:
        stmt = stmt.where(Party.party_type == party_type)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Note.note.ilike(like), Party.name.ilike(like)))
    stmt = apply_sort(
        stmt,
        sort_by,
        sort_dir,
        {"created_at": Note.created_at, "id": Note.id},
        "created_at",
    )
    return paginate(session, stmt, params)


def create_note(session: Session, payload: NoteCreate, user_id: int) -> Note:
    party = get_or_404(session, Party, payload.party_id, "Party")
    note = Note(party_id=party.id, note=payload.note.strip(), created_by=user_id)
    session.add(note)
    session.flush()
    audit.record(
        session,
        user_id=user_id,
        entity_type="note",
        entity_id=note.id,
        action=AuditAction.CREATE,
        new_value={"party_id": party.id},
    )
    return note


def update_note(session: Session, note_id: int, payload: NoteUpdate, user_id: int) -> Note:
    note = get_or_404(session, Note, note_id, "Note")
    old = note.note
    note.note = payload.note.strip()
    audit.record(
        session,
        user_id=user_id,
        entity_type="note",
        entity_id=note.id,
        action=AuditAction.UPDATE,
        old_value={"note": old},
        new_value={"note": note.note},
    )
    return note
