"""Enquiries raised by parties themselves: what they send, and the two views out.

The party sends loose words and gets back their own list. The desk sees the
same words plus who typed them, and the inquiry each one became - which exists
already, because an enquiry is written onto the book as it arrives.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import InquiryType, QuantityUnit
from app.schemas.common import ORMBase, PartyRef, ProductRef

QUANTITY = Field(gt=0, max_digits=14, decimal_places=3)
RATE = Field(default=None, gt=0, max_digits=14, decimal_places=2)
PLACE = Field(default=None, max_length=200)
#: A name they may be creating in our master data, so it is kept short.
NAME = Field(default=None, max_length=80)


def _tidy(value: str | None) -> str | None:
    """Trim what someone typed on a phone; treat all-whitespace as nothing."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


# --- What a party sends in --------------------------------------------------
class PortalEnquiryRequest(BaseModel):
    """One enquiry, as typed into a portal link.

    The grade is asked for the way a trader thinks of it: the material, then a
    grade of that material, then whose it is. Each may be picked from our list
    or typed; anything typed that we do not have is created, so a party is
    never turned away because our master list is short of a name.

    What they are *not* allowed to do is say who they are - that comes from the
    code in the link, never from the form.
    """

    #: Chosen from the list the portal offers...
    material_id: int | None = None
    #: ...or typed, when the list did not have it.
    material_text: str | None = NAME
    grade_id: int | None = None
    grade_text: str | None = NAME
    manufacturer_id: int | None = None
    manufacturer_text: str | None = NAME
    quantity: Decimal = QUANTITY
    unit: QuantityUnit = QuantityUnit.MT
    from_place: str | None = PLACE
    to_place: str | None = PLACE
    #: Per kilogram for a product, the whole freight for a load. Optional.
    rate: Decimal | None = RATE
    notes: str | None = Field(default=None, max_length=2000)

    _clean = field_validator(
        "material_text",
        "grade_text",
        "manufacturer_text",
        "from_place",
        "to_place",
        "notes",
    )(lambda cls, value: _tidy(value))


# --- What the party sees back -----------------------------------------------
class PortalEnquiryOut(BaseModel):
    """Their own enquiry, echoed back.

    Nothing about the inquiry it became is included: that it reached us is
    theirs to know, what we do with it is the desk's.
    """

    id: int
    inquiry_type: InquiryType
    product_name: str | None = None
    quantity: Decimal
    unit: QuantityUnit
    from_place: str | None = None
    to_place: str | None = None
    rate: Decimal | None = None
    notes: str | None = None
    created_at: datetime


class PortalOption(BaseModel):
    """One line in a picker: a material, a grade or a manufacturer."""

    id: int
    name: str


# --- What the desk sees -----------------------------------------------------
class DeskEnquiryOut(ORMBase):
    """What a party sent, and the inquiry it became.

    Worth its own screen because an inquiry cannot hold all of it: their note
    is theirs, and the places are the words they used rather than the rows we
    matched them to.
    """

    id: int
    inquiry_type: InquiryType
    party: PartyRef
    #: Null only for a load, which carries no product.
    product: ProductRef | None = None
    quantity: Decimal
    unit: QuantityUnit
    from_place: str | None = None
    to_place: str | None = None
    rate: Decimal | None = None
    notes: str | None = None
    created_at: datetime
    #: The inquiry this became. Always set - it is written as the enquiry lands.
    inquiry_id: int


class EnquiryLink(BaseModel):
    """The link a party uses to raise enquiries, for the desk to copy."""

    party_id: int
    #: Where they place an enquiry.
    enquiry_link: str
    #: Their permanent portal, listing their bids and their enquiries.
    portal_link: str
