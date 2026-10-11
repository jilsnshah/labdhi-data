"""Business note schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase, PartyRef, UserRef


class NoteCreate(BaseModel):
    party_id: int
    note: str = Field(min_length=1, max_length=8000)


class NoteUpdate(BaseModel):
    note: str = Field(min_length=1, max_length=8000)


class NoteOut(ORMBase):
    id: int
    party_id: int
    note: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    creator: UserRef | None = None
    party: PartyRef | None = None
