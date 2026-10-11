"""Master data schemas: material, grade, manufacturer, application, product."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.models.enums import RecordStatus
from app.schemas.common import IdName, ORMBase, TimestampsOut


def _clean(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError("must not be blank")
    return cleaned


class _NamedCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        return _clean(value)


class _NamedUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    status: RecordStatus | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        return _clean(value) if value is not None else None


# --- Material ---------------------------------------------------------------
class MaterialCreate(_NamedCreate):
    pass


class MaterialUpdate(_NamedUpdate):
    pass


class MaterialOut(TimestampsOut, ORMBase):
    id: int
    name: str
    description: str | None
    status: RecordStatus
    grade_count: int | None = None


# --- Grade ------------------------------------------------------------------
class GradeCreate(_NamedCreate):
    material_id: int


class GradeUpdate(_NamedUpdate):
    material_id: int | None = None


class GradeOut(TimestampsOut, ORMBase):
    id: int
    name: str
    material_id: int
    material: IdName
    description: str | None
    status: RecordStatus


# --- Manufacturer -----------------------------------------------------------
class ManufacturerCreate(_NamedCreate):
    code: str | None = Field(default=None, max_length=30)


class ManufacturerUpdate(_NamedUpdate):
    code: str | None = Field(default=None, max_length=30)


class ManufacturerOut(TimestampsOut, ORMBase):
    id: int
    name: str
    code: str | None
    description: str | None
    status: RecordStatus


# --- Application ------------------------------------------------------------
class ApplicationCreate(_NamedCreate):
    pass


class ApplicationUpdate(_NamedUpdate):
    pass


class ApplicationOut(TimestampsOut, ORMBase):
    id: int
    name: str
    description: str | None
    status: RecordStatus


# --- Product ----------------------------------------------------------------
class ProductCreate(BaseModel):
    material_id: int
    grade_id: int
    manufacturer_id: int
    display_name: str | None = Field(
        default=None,
        max_length=200,
        description="Auto-generated from manufacturer + material + grade when omitted.",
    )
    description: str | None = None
    application_ids: list[int] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    material_id: int | None = None
    grade_id: int | None = None
    manufacturer_id: int | None = None
    display_name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    status: RecordStatus | None = None
    application_ids: list[int] | None = None


class ProductOut(TimestampsOut, ORMBase):
    id: int
    display_name: str
    description: str | None
    status: RecordStatus
    material_id: int
    grade_id: int
    manufacturer_id: int
    material: IdName
    grade: IdName
    manufacturer: IdName
    applications: list[IdName] = Field(default_factory=list)


class ProductPartyLink(ORMBase):
    """Used by /products/{id}/suppliers and /products/{id}/customers."""

    party_id: int
    party_name: str
    party_type: str
    relationship_type: str
    phone: str | None = None
    city: str | None = None
    notes: str | None = None
