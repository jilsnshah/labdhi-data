"""What the agents are allowed to say back.

Every agent answers in one of these shapes, and nothing else gets through. A
model asked for free text will happily produce a paragraph explaining that it
is not sure; a model asked for this produces a field we can act on, or fails
validation and is treated as a failure rather than quietly misread.

Note what is absent: no row ids, anywhere. An agent never names a party, a
product or a location by id, because an id it invented would look exactly like
one it remembered. Identifiers are resolved on our side of the line.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

#: The three sides of this desk's trade. The agent picks one of these or says
#: it cannot tell; it may not invent a fourth.
Role = Literal["CUSTOMER", "SUPPLIER", "TRANSPORTER"]


class Classification(BaseModel):
    """Is this message somebody asking to trade, or is it anything else?"""

    is_enquiry: bool = Field(description="True only if this is a genuine business enquiry.")
    confidence: float = Field(
        ge=0.0, le=1.0, description="How sure you are, from 0 to 1. Be honest rather than bold."
    )
    reason: str = Field(
        default="",
        max_length=200,
        description="One short line of why, with no customer details in it.",
    )


class SenderIdentity(BaseModel):
    """Who an unknown number appears to be, read out of what they wrote.

    The role and whatever identifies them come back together because they are
    read from the same few words, and one call to the model is half the cost of
    two. Everything but the role is optional on purpose: a blank field is a
    true statement about a message that did not say, and is written down as
    nothing. Guessing a company name would be worse than leaving it empty.
    """

    role: Role | None = Field(
        default=None,
        description=(
            "CUSTOMER if they want to buy, SUPPLIER if they have material to sell, "
            "TRANSPORTER if they move goods. Null if the message does not make it clear."
        ),
    )
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(default="", max_length=200)

    name: str | None = Field(
        default=None, max_length=200, description="Their firm's name, if they gave one."
    )
    contact_person: str | None = Field(
        default=None, max_length=120, description="The person's own name, if they gave one."
    )
    city: str | None = Field(
        default=None, max_length=120, description="Where they are, if they said."
    )


class EnquiryResult(BaseModel):
    """What an enquiry agent did, in its own words. Trusted for nothing.

    The record of what happened is the inquiry row its tool created; this is
    only what the agent says about its work, kept for the log when it reports
    it could not do it.
    """

    created: bool = Field(description="True only if a tool reported creating an enquiry.")
    note: str = Field(default="", max_length=300)


class CustomerEnquiry(BaseModel):
    """A customer saying what they want to buy."""

    material: str = Field(max_length=80, description="PVC, HDPE, PP - the polymer itself.")
    grade: str = Field(max_length=80, description="The grade of it, such as K-67.")
    manufacturer: str = Field(max_length=80, description="Whose material, such as Reliance.")
    quantity: Decimal = Field(gt=0, description="How much they want.")
    unit: Literal["MT", "KG", "BAG", "LITRE", "PIECE"] = "MT"
    deliver_to: str | None = Field(
        default=None, max_length=200, description="Town or area for delivery, if they said."
    )
    rate: Decimal | None = Field(
        default=None, gt=0, description="Rupees per kilogram, only if they named one."
    )
    notes: str | None = Field(default=None, max_length=2000)


class SupplierEnquiry(BaseModel):
    """A supplier saying what they have to sell."""

    material: str = Field(max_length=80)
    grade: str = Field(max_length=80)
    manufacturer: str = Field(max_length=80)
    quantity: Decimal = Field(gt=0)
    unit: Literal["MT", "KG", "BAG", "LITRE", "PIECE"] = "MT"
    rate: Decimal | None = Field(default=None, gt=0, description="Rupees per kilogram.")
    notes: str | None = Field(default=None, max_length=2000)


class TransportEnquiry(BaseModel):
    """A transporter offering to move a load."""

    quantity: Decimal = Field(gt=0, description="The load they can take.")
    unit: Literal["MT", "KG", "BAG", "LITRE", "PIECE"] = "MT"
    pickup: str = Field(max_length=200, description="Where it is picked up.")
    delivery: str = Field(max_length=200, description="Where it goes.")
    freight: Decimal | None = Field(
        default=None, gt=0, description="Rupees for the whole load, if they named a figure."
    )
    notes: str | None = Field(default=None, max_length=2000)
