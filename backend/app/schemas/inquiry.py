"""Inquiry schemas: create, patch, list rows and the detail view.

An inquiry is a recorded quotation. Supplier and customer inquiries quote a rate
in rupees per kilogram; transport inquiries quote a price in rupees.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import InquiryStatus, InquiryType, QuantityUnit
from app.schemas.common import (
    LocationRef,
    ORMBase,
    PartyRef,
    ProductRef,
    UserRef,
)

QUANTITY = Field(gt=0, max_digits=14, decimal_places=3)
RATE = Field(default=None, gt=0, max_digits=14, decimal_places=2)


# --- Create -----------------------------------------------------------------
class _Quantity(BaseModel):
    quantity: Decimal = QUANTITY
    unit: QuantityUnit = QuantityUnit.MT


class CustomerInquiryCreate(_Quantity):
    customer_id: int
    product_id: int
    #: Any Master Data location; not limited to the customer's own addresses.
    location_id: int | None = None
    #: Rupees per kilogram.
    rate: Decimal | None = RATE


class SupplierInquiryCreate(_Quantity):
    supplier_id: int
    product_id: int
    #: Any Master Data location; not limited to the supplier's own addresses.
    location_id: int | None = None
    #: Rupees per kilogram.
    rate: Decimal | None = RATE


class TransportInquiryCreate(_Quantity):
    transporter_id: int
    pickup_location_id: int
    delivery_location_id: int
    #: Quoted amount in rupees.
    price: Decimal | None = RATE

    @model_validator(mode="after")
    def _distinct_locations(self) -> TransportInquiryCreate:
        if self.pickup_location_id == self.delivery_location_id:
            raise ValueError("pickup and drop locations must be different")
        return self


class InquiryCreate(BaseModel):
    """Single POST /inquiries entry point: the type decides which detail block is used."""

    inquiry_type: InquiryType
    status: InquiryStatus = InquiryStatus.ACTIVE
    customer: CustomerInquiryCreate | None = None
    supplier: SupplierInquiryCreate | None = None
    transport: TransportInquiryCreate | None = None

    @model_validator(mode="after")
    def _detail_matches_type(self) -> InquiryCreate:
        mapping = {
            InquiryType.CUSTOMER: self.customer,
            InquiryType.SUPPLIER: self.supplier,
            InquiryType.TRANSPORT: self.transport,
        }
        if mapping[self.inquiry_type] is None:
            raise ValueError(
                f"'{self.inquiry_type.value.lower()}' detail block is required for "
                f"inquiry_type={self.inquiry_type.value}"
            )
        extra = [
            key for key, value in mapping.items() if value is not None and key != self.inquiry_type
        ]
        if extra:
            raise ValueError("only the detail block matching inquiry_type may be provided")
        return self


# --- Update -----------------------------------------------------------------
class InquiryUpdate(BaseModel):
    """Patch any field of an inquiry. Fields that do not apply to its type are refused.

    ``party_id`` is the customer, supplier or transporter, depending on the type.
    Send ``location_id: null`` to clear a location.
    """

    status: InquiryStatus | None = None
    party_id: int | None = None
    product_id: int | None = None
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3)
    unit: QuantityUnit | None = None
    location_id: int | None = None
    rate: Decimal | None = RATE
    pickup_location_id: int | None = None
    delivery_location_id: int | None = None
    price: Decimal | None = RATE


# --- Output -----------------------------------------------------------------
class CustomerInquiryDetailOut(ORMBase):
    customer_id: int
    product_id: int
    quantity: Decimal
    unit: QuantityUnit
    location_id: int | None
    rate: Decimal | None
    customer: PartyRef
    product: ProductRef
    location: LocationRef | None = None


class SupplierInquiryDetailOut(ORMBase):
    supplier_id: int
    product_id: int
    quantity: Decimal
    unit: QuantityUnit
    location_id: int | None
    rate: Decimal | None
    supplier: PartyRef
    product: ProductRef
    location: LocationRef | None = None


class TransportInquiryDetailOut(ORMBase):
    transporter_id: int
    quantity: Decimal
    unit: QuantityUnit
    pickup_location_id: int
    delivery_location_id: int
    price: Decimal | None
    transporter: PartyRef
    pickup_location: LocationRef
    delivery_location: LocationRef


class InquiryListItem(BaseModel):
    """Flat row for inquiry tables."""

    id: int
    inquiry_type: InquiryType
    status: InquiryStatus
    title: str | None = None
    party_id: int | None = None
    party_name: str | None = None
    party_stage: str | None = None
    product_id: int | None = None
    product_name: str | None = None
    quantity: Decimal | None = None
    unit: QuantityUnit | None = None
    #: Supplier / customer inquiries.
    location_name: str | None = None
    location_area: str | None = None
    location_city: str | None = None
    #: Rupees per kilogram (supplier / customer inquiries).
    rate: Decimal | None = None
    #: Transport inquiries.
    pickup_name: str | None = None
    delivery_name: str | None = None
    #: Rupees (transport inquiries).
    price: Decimal | None = None
    created_by: int
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None


class TimelineEvent(BaseModel):
    at: datetime
    kind: str
    title: str
    description: str | None = None
    actor: str | None = None
    ref_type: str | None = None
    ref_id: int | None = None


class InquiryOut(ORMBase):
    id: int
    inquiry_type: InquiryType
    status: InquiryStatus
    title: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    closed_by: int | None
    creator: UserRef | None = None
    closer: UserRef | None = None
    customer_detail: CustomerInquiryDetailOut | None = None
    supplier_detail: SupplierInquiryDetailOut | None = None
    transport_detail: TransportInquiryDetailOut | None = None


#: The detail view needs nothing beyond the inquiry itself any more.
InquiryDetailOut = InquiryOut
