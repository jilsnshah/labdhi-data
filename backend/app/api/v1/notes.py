"""Business note endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import SessionDep, StaffUser
from app.core.pagination import Page, PageParams, page_params
from app.models.enums import PartyType
from app.schemas.note import NoteCreate, NoteOut, NoteUpdate
from app.services import notes as service

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=Page[NoteOut])
def list_notes(
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, description="Note text or party name"),
    party_id: int | None = None,
    party_type: PartyType | None = None,
    sort_by: str | None = Query(None, pattern="^(created_at|id)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
) -> Page[NoteOut]:
    rows, total = service.list_notes(
        session,
        params,
        party_id=party_id,
        party_type=party_type,
        q=q,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return Page.build([NoteOut.model_validate(row) for row in rows], total, params)


@router.post("", response_model=NoteOut, status_code=201)
def create_note(payload: NoteCreate, session: SessionDep, user: StaffUser) -> NoteOut:
    return NoteOut.model_validate(service.create_note(session, payload, user.id))


@router.patch("/{note_id}", response_model=NoteOut)
def update_note(note_id: int, payload: NoteUpdate, session: SessionDep, user: StaffUser) -> NoteOut:
    return NoteOut.model_validate(service.update_note(session, note_id, payload, user.id))
