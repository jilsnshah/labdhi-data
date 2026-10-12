"""Party, location, party-location and party-product schemas."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import (
    LocationType,
    PartyProductRelationship,
    PartySource,
    PartyStage,
    PartyType,
    RecordStatus,
)
from app.schemas.common import ApplicationRef, ORMBase, ProductRef, TimestampsOut


# --- Location ---------------------------------------------------------------
def _clean_area(value: str | None) -> str | None:
    """One spelling per area: trim and collapse spaces, blank means none."""
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


class LocationCreate(BaseModel):
    label: str | None = Field(default=None, max_length=120)
    address_line_1: str | None = Field(default=None, max_length=200)
    address_line_2: str | None = Field(default=None, max_length=200)
    #: Locality within the city, e.g. "Shapar" or "GIDC Vapi".
    area: str | None = Field(default=None, max_length=120)
    city: str = Field(min_length=1, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    country: str = Field(default="India", max_length=120)
    pincode: str | None = Field(default=None, max_length=12)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)

    _area = field_validator("area")(_clean_area)


class LocationUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=120)
    address_line_1: str | None = None
    address_line_2: str | None = None
    area: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    state: str | None = None
    country: str | None = None
    pincode: str | None = Field(default=None, max_length=12)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    status: RecordStatus | None = None

    _area = field_validator("area")(_clean_area)


class LocationOut(TimestampsOut, ORMBase):
    id: int
    label: str | None
    address_line_1: str | None
    address_line_2: str | None
    area: str | None
    city: str
    state: str | None
    country: str
    pincode: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    status: RecordStatus
    display_name: str


# --- Party location link ----------------------------------------------------
class PartyLocationCreate(BaseModel):
    """Either attach an existing location (``location_id``) or create one inline."""

    location_id: int | None = None
    location: LocationCreate | None = None
    location_type: LocationType = LocationType.OTHER
    is_primary: bool = False

    @field_validator("location")
    @classmethod
    def _one_of(cls, value: LocationCreate | None, info) -> LocationCreate | None:
        if value is None and not info.data.get("location_id"):
            raise ValueError("provide either location_id or an inline location")
        return value


class PartyLocationUpdate(BaseModel):
    location_type: LocationType | None = None
    is_primary: bool | None = None


class PartyLocationOut(ORMBase):
    id: int
    party_id: int
    location_id: int
    location_type: LocationType
    is_primary: bool
    location: LocationOut


# --- Party product link -----------------------------------------------------
class PartyProductCreate(BaseModel):
    product_id: int
    relationship_type: PartyProductRelationship | None = Field(
        default=None,
        description="Defaults to SUPPLIES for suppliers and PURCHASES for customers.",
    )
    notes: str | None = None
    active: bool = True


class PartyProductUpdate(BaseModel):
    relationship_type: PartyProductRelationship | None = None
    notes: str | None = None
    active: bool | None = None


class PartyProductOut(ORMBase):
    id: int
    party_id: int
    product_id: int
    relationship_type: PartyProductRelationship
    notes: str | None
    active: bool
    product: ProductRef


class PartyApplicationCreate(BaseModel):
    application_id: int
    notes: str | None = None
    active: bool = True


class PartyApplicationUpdate(BaseModel):
    notes: str | None = None
    active: bool | None = None


class PartyApplicationOut(ORMBase):
    id: int
    party_id: int
    application_id: int
    notes: str | None
    active: bool
    application: ApplicationRef


# --- Quick create (unknown party) -------------------------------------------
class PartyProspectCreate(BaseModel):
    """A party nobody has on file yet: a name and a phone number, nothing more."""

    party_type: PartyType
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=1, max_length=30)

    @field_validator("name", "phone")
    @classmethod
    def _clean(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class PartyQuickCreate(BaseModel):
    """Minimum viable party, created inline from an inquiry or activity form.

    At least one of ``name`` / ``phone`` is required - with neither there is
    nothing to follow up on. The record lands as ``stage=PROSPECT``.
    """

    name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    contact_person: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    gst_number: str | None = Field(default=None, max_length=20)
    #: Convenience: creates a primary location with just this city.
    city: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    #: Set by the calling flow (customer inquiry -> CUSTOMER, and so on).
    party_type: PartyType | None = None

    @field_validator("name", "phone", "contact_person", "city")
    @classmethod
    def _clean(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @field_validator("gst_number")
    @classmethod
    def _upper_gst(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None

    @model_validator(mode="after")
    def _needs_an_identifier(self) -> PartyQuickCreate:
        if not self.name and not self.phone:
            raise ValueError("a new party needs at least a name or a phone number")
        return self

    @property
    def display_name(self) -> str:
        """Phone-only walk-ins are displayed by their number until named."""
        return self.name or (self.phone or "Unknown")


class DuplicateCandidate(ORMBase):
    id: int
    name: str
    party_type: PartyType
    stage: PartyStage
    status: RecordStatus
    phone: str | None = None
    gst_number: str | None = None
    city: str | None = None
    #: exact_gst | exact_phone | similar_name
    match_reason: str
    #: 0..1, highest first
    score: float


class DuplicateCheckResult(BaseModel):
    candidates: list[DuplicateCandidate] = Field(default_factory=list)
    #: True when an identifier matched exactly (GST or phone) - worth blocking on in the UI.
    has_exact_match: bool = False


class PartyMergeRequest(BaseModel):
    """Fold ``loser_id`` into the party in the path, keeping all history."""

    loser_id: int
    note: str | None = Field(default=None, max_length=1000)


class PartyMergeResult(BaseModel):
    survivor_id: int
    merged_party_id: int
    moved: dict[str, int]
    message: str


# --- Party ------------------------------------------------------------------
class PartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    party_type: PartyType
    #: Desk-created parties are verified by default; quick-create sets PROSPECT.
    stage: PartyStage = PartyStage.ACTIVE
    contact_person: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    gst_number: str | None = Field(default=None, max_length=20)
    notes: str | None = None
    locations: list[PartyLocationCreate] = Field(default_factory=list)
    products: list[PartyProductCreate] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("gst_number")
    @classmethod
    def _upper_gst(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class PartyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    contact_person: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    gst_number: str | None = Field(default=None, max_length=20)
    notes: str | None = None
    status: RecordStatus | None = None

    @field_validator("gst_number")
    @classmethod
    def _upper_gst(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class PartyOut(TimestampsOut, ORMBase):
    id: int
    name: str
    party_type: PartyType
    contact_person: str | None
    phone: str | None
    email: str | None
    gst_number: str | None
    notes: str | None
    status: RecordStatus
    stage: PartyStage
    source: PartySource
    merged_into_id: int | None = None


class PartyDetailOut(PartyOut):
    locations: list[PartyLocationOut] = Field(default_factory=list)
    products: list[PartyProductOut] = Field(default_factory=list)
    applications: list[PartyApplicationOut] = Field(default_factory=list)


class PartyListItem(PartyOut):
    primary_city: str | None = None
    product_count: int = 0
    open_inquiry_count: int = 0
