"""Enquiries raised by parties themselves: what they send, and the two views out.

The party sends loose words and gets back their own list. The desk sees the
same words plus who typed them, and turns one into an inquiry by supplying the
master data the party could not: which product, which location, what rate.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import InquiryType, PortalEnquiryStatus, QuantityUnit
from app.schemas.common import ORMBase, PartyRef, ProductRef, UserRef

QUANTITY = Field(gt=0, max_digits=14, decimal_places=3)
RATE = Field(default=None, gt=0, max_digits=14, decimal_places=2)
PLACE = Field(default=None, max_length=200)


def _tidy(value: str | None) -> str | None:
    """Trim what someone typed on a phone; treat all-whitespace as nothing."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


# --- What a party sends in --------------------------------------------------
class PortalEnquiryRequest(BaseModel):
    """One enquiry, as typed into a portal link.

    Deliberately forgiving. The party is not expected to know our product
    master, so they may pick a grade from the list *or* type its name; and
    places are free text, because they do not know our locations either. What
    they are *not* allowed to do is say who they are - that comes from the code
    in the link, never from the form.
    """

    #: Chosen from the list the portal offers.
    product_id: int | None = None
    #: Or typed, when the list did not have it.
    product_text: str | None = Field(default=None, max_length=200)
    quantity: Decimal = QUANTITY
    unit: QuantityUnit = QuantityUnit.MT
    from_place: str | None = PLACE
    to_place: str | None = PLACE
    #: Per kilogram for a product, the whole freight for a load. Optional.
    rate: Decimal | None = RATE
    notes: str | None = Field(default=None, max_length=2000)

    _clean = field_validator("product_text", "from_place", "to_place", "notes")(
        lambda cls, value: _tidy(value)
    )


# --- What the party sees back -----------------------------------------------
class PortalEnquiryOut(BaseModel):
    """Their own enquiry, echoed back with where it has got to.

    ``status`` is shown because a party who sent something is owed the
    knowledge that it was read. Nothing about the inquiry it became is
    included: that is the desk's record, not theirs.
    """

    id: int
    inquiry_type: InquiryType
    status: PortalEnquiryStatus
    product_name: str | None = None
    quantity: Decimal
    unit: QuantityUnit
    from_place: str | None = None
    to_place: str | None = None
    rate: Decimal | None = None
    notes: str | None = None
    created_at: datetime


class PortalProduct(BaseModel):
    """One line in the picker a party chooses their grade from."""

    id: int
    display_name: str


# --- What the desk sees -----------------------------------------------------
class DeskEnquiryOut(ORMBase):
    """An enquiry in the desk's inbox: the party's words, and who typed them."""

    id: int
    inquiry_type: InquiryType
    status: PortalEnquiryStatus
    party: PartyRef
    #: Set when the party found their grade in the list.
    product: ProductRef | None = None
    #: Set when they typed it instead. Exactly one of the two is filled in.
    product_text: str | None = None
    quantity: Decimal
    unit: QuantityUnit
    from_place: str | None = None
    to_place: str | None = None
    rate: Decimal | None = None
    notes: str | None = None
    created_at: datetime
    #: The inquiry this became, once accepted.
    inquiry_id: int | None = None
    handled_at: datetime | None = None
    handler: UserRef | None = None


class DeskEnquiryCounts(BaseModel):
    """For the badge on the nav: how much is waiting to be read."""

    new: int = 0
    accepted: int = 0
    declined: int = 0


class EnquiryAcceptRequest(BaseModel):
    """What the desk supplies to turn an enquiry into a real inquiry.

    The party's quantity, unit and rate carry over unless the desk overrides
    them; the product and the locations have to be named here, because a text
    box cannot point at master data. A transport enquiry needs both locations,
    anything else needs the product.
    """

    product_id: int | None = None
    location_id: int | None = None
    pickup_location_id: int | None = None
    delivery_location_id: int | None = None
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3)
    unit: QuantityUnit | None = None
    rate: Decimal | None = RATE


class EnquiryLink(BaseModel):
    """The link a party uses to raise enquiries, for the desk to copy."""

    party_id: int
    #: Where they place an enquiry.
    enquiry_link: str
    #: Their permanent portal, listing their bids and their enquiries.
    portal_link: str
