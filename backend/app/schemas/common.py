"""Shared schema building blocks."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import PartyStage, PartyType, RecordStatus


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampsOut(ORMBase):
    created_at: datetime
    updated_at: datetime


class IdName(ORMBase):
    """Minimal reference used for display inside bigger payloads."""

    id: int
    name: str


class PartyRef(ORMBase):
    id: int
    name: str
    party_type: PartyType
    status: RecordStatus
    #: Needed wherever we might message them; null when none is on file.
    phone: str | None = None
    #: PROSPECT means "met just now, identity unverified" - the UI badges it.
    stage: PartyStage = PartyStage.ACTIVE


class UserRef(ORMBase):
    id: int
    name: str


class ProductRef(ORMBase):
    id: int
    display_name: str
    status: RecordStatus


class ApplicationRef(ORMBase):
    id: int
    name: str
    status: RecordStatus


class LocationRef(ORMBase):
    id: int
    label: str | None = None
    area: str | None = None
    city: str
    state: str | None = None


class StatusUpdate(BaseModel):
    status: RecordStatus


class Message(BaseModel):
    message: str
