"""Bid schemas: what the desk sends, and the two very different views out.

The desk sees everything. A participant sees their own bid, their own quote and
one number telling them what they are up against - never another party's name,
and never another party's quotation.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import BidStatus, BidType, QuantityUnit
from app.schemas.common import LocationRef, ORMBase, PartyRef, ProductRef, UserRef

QUANTITY = Field(gt=0, max_digits=14, decimal_places=3)
PRICE = Field(gt=0, max_digits=14, decimal_places=2)


# --- Create / update --------------------------------------------------------
class BidCreate(BaseModel):
    """One lot, and the parties asked to quote on it.

    ``product_id`` for customer and supplier bids; the two locations for
    transport. The participants must all be of the type the bid is addressed to.
    """

    bid_type: BidType
    quantity: Decimal = QUANTITY
    unit: QuantityUnit = QuantityUnit.MT
    product_id: int | None = None
    pickup_location_id: int | None = None
    delivery_location_id: int | None = None
    title: str | None = Field(default=None, max_length=200)
    specifications: str | None = None
    closes_at: datetime | None = None
    #: Parties invited to quote. May be empty on a draft and filled in later.
    party_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _detail_matches_type(self) -> BidCreate:
        if self.bid_type == BidType.TRANSPORT:
            if self.pickup_location_id is None or self.delivery_location_id is None:
                raise ValueError("a transport bid needs a pickup and a delivery location")
            if self.pickup_location_id == self.delivery_location_id:
                raise ValueError("pickup and delivery locations must be different")
            if self.product_id is not None:
                raise ValueError("a transport bid does not carry a product")
        elif self.product_id is None:
            raise ValueError(f"a {self.bid_type.value.lower()} bid needs a product")
        return self


class BidUpdate(BaseModel):
    """Editable while the bid is a draft; afterwards only the closing time."""

    title: str | None = Field(default=None, max_length=200)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3)
    unit: QuantityUnit | None = None
    product_id: int | None = None
    pickup_location_id: int | None = None
    delivery_location_id: int | None = None
    specifications: str | None = None
    closes_at: datetime | None = None


class BidParticipantsRequest(BaseModel):
    party_ids: list[int] = Field(min_length=1)


class BidAwardRequest(BaseModel):
    quote_id: int


# --- Desk views -------------------------------------------------------------
class BidQuoteOut(ORMBase):
    """A quotation as the desk sees it, with the party attached."""

    id: int
    participant_id: int
    price: Decimal
    quantity: Decimal | None
    notes: str | None
    submitted_at: datetime
    revision: int
    party: PartyRef
    #: True for the quote the desk awarded.
    is_winner: bool = False


class BidParticipantOut(ORMBase):
    id: int
    party: PartyRef
    first_opened_at: datetime | None = None
    last_opened_at: datetime | None = None
    quote: BidQuoteOut | None = None
    #: Ready-to-copy link for this party's view of this bid.
    bid_link: str
    #: Their permanent portal, listing every bid they are in.
    portal_link: str


class BidListItem(BaseModel):
    """Flat row for the bids table."""

    id: int
    bid_type: BidType
    status: BidStatus
    title: str | None = None
    product_id: int | None = None
    product_name: str | None = None
    quantity: Decimal
    unit: QuantityUnit
    pickup_name: str | None = None
    delivery_name: str | None = None
    closes_at: datetime | None = None
    participant_count: int = 0
    quote_count: int = 0
    #: Best price standing: the highest on a customer bid, the lowest otherwise.
    best_price: Decimal | None = None
    winner_party_name: str | None = None
    no_winner: bool = False
    created_by: int
    created_by_name: str | None = None
    created_at: datetime
    published_at: datetime | None = None
    closed_at: datetime | None = None


class BidOut(ORMBase):
    id: int
    bid_type: BidType
    status: BidStatus
    title: str | None
    quantity: Decimal
    unit: QuantityUnit
    specifications: str | None
    closes_at: datetime | None
    product: ProductRef | None = None
    pickup_location: LocationRef | None = None
    delivery_location: LocationRef | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    closed_at: datetime | None
    no_winner: bool
    awarded_at: datetime | None
    creator: UserRef | None = None
    closer: UserRef | None = None


class BidDetailOut(BidOut):
    participants: list[BidParticipantOut] = Field(default_factory=list)
    quotes: list[BidQuoteOut] = Field(default_factory=list)
    winner: BidQuoteOut | None = None
    best_price: Decimal | None = None


class BidEvent(BaseModel):
    at: datetime
    action: str
    summary: str
    actor: str | None = None


# --- Participant views ------------------------------------------------------
class PortalQuote(BaseModel):
    """The participant's own quotation, echoed back to them."""

    price: Decimal
    quantity: Decimal | None = None
    notes: str | None = None
    submitted_at: datetime
    revision: int


class PortalBid(BaseModel):
    """One bid as the invited party sees it.

    What is deliberately absent: who else was invited, how many of them have
    quoted what, and any name attached to the standing best price.
    """

    id: int
    bid_type: BidType
    status: BidStatus
    title: str
    product_name: str | None = None
    quantity: Decimal
    unit: QuantityUnit
    pickup_name: str | None = None
    delivery_name: str | None = None
    specifications: str | None = None
    closes_at: datetime | None = None
    #: "Higher wins" when selling to customers, "lower wins" when buying.
    best_is_highest: bool
    #: The price to beat, from anyone including themselves. None until someone bids.
    best_price: Decimal | None = None
    #: How many parties have quoted - a sense of the room, with no identities.
    bidders: int = 0
    #: True when this participant currently holds the best price.
    leading: bool = False
    my_quote: PortalQuote | None = None
    can_quote: bool = False


class PortalHome(BaseModel):
    """Everything the permanent portal link shows: who they are, and their bids."""

    participant_name: str
    party_type: str
    open_bids: list[PortalBid] = Field(default_factory=list)
    closed_bids: list[PortalBid] = Field(default_factory=list)


class PortalQuoteRequest(BaseModel):
    price: Decimal = PRICE
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3)
    notes: str | None = Field(default=None, max_length=2000)
