"""Business enums.

Stored as VARCHAR + CHECK constraint (``native_enum=False``) rather than native
PostgreSQL ENUM types: the database still rejects invalid values, but adding a
new value later is a cheap migration instead of an ALTER TYPE dance.
"""

from enum import Enum

from sqlalchemy import Enum as SAEnum


class _Str(str, Enum):
    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.value


class RecordStatus(_Str):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class UserRole(_Str):
    ADMIN = "ADMIN"
    USER = "USER"
    #: Field user: executes assigned activities only, no CRM access.
    SALESPERSON = "SALESPERSON"


#: Roles allowed to use the back-office CRM (everything except SALESPERSON).
STAFF_ROLES = frozenset({UserRole.ADMIN, UserRole.USER})


class PartyType(_Str):
    CUSTOMER = "CUSTOMER"
    SUPPLIER = "SUPPLIER"
    TRANSPORTER = "TRANSPORTER"


class PartyStage(_Str):
    """How well we know a party - orthogonal to ``status``.

    ``status`` answers "may this be used for new business"; ``stage`` answers
    "is this a verified relationship or a lead we just met".
    """

    #: Created in one step from an inquiry or activity form; identity unverified.
    PROSPECT = "PROSPECT"
    #: A known, verified party.
    ACTIVE = "ACTIVE"
    #: Folded into another party by a merge; kept for history and old links.
    MERGED = "MERGED"


class PartySource(_Str):
    DESK = "DESK"
    QUICK_CREATE = "QUICK_CREATE"
    IMPORT = "IMPORT"
    FIELD = "FIELD"


class LocationType(_Str):
    HEAD_OFFICE = "HEAD_OFFICE"
    FACTORY = "FACTORY"
    WAREHOUSE = "WAREHOUSE"
    DELIVERY_LOCATION = "DELIVERY_LOCATION"
    OTHER = "OTHER"


class PartyProductRelationship(_Str):
    SUPPLIES = "SUPPLIES"
    PURCHASES = "PURCHASES"
    INTERESTED_IN = "INTERESTED_IN"


class InquiryType(_Str):
    CUSTOMER = "CUSTOMER"
    SUPPLIER = "SUPPLIER"
    TRANSPORT = "TRANSPORT"


class InquirySource(_Str):
    """Who put this inquiry on the book."""

    #: Keyed in by the desk or a salesperson.
    DESK = "DESK"
    #: Sent in by the party themselves, through their portal link.
    PORTAL = "PORTAL"


class InquiryStatus(_Str):
    """An inquiry is either still being worked, or it is done.

    The earlier OPEN / IN_PROGRESS / WAITING / QUOTED / CANCELLED ladder tracked
    the back-and-forth of asking for a quote. Quotes are now recorded directly
    on the inquiry, so only the two states the desk actually acts on remain.
    """

    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class BidType(_Str):
    """Who is being asked to quote."""

    #: We are selling: customers bid, the highest price wins.
    CUSTOMER = "CUSTOMER"
    #: We are buying material: suppliers bid, the lowest price wins.
    SUPPLIER = "SUPPLIER"
    #: We are buying a movement: transporters bid, the lowest price wins.
    TRANSPORT = "TRANSPORT"


class BidStatus(_Str):
    """Three states, and no way back: a bid is written, run, then settled."""

    #: Written but not yet visible to anyone outside the desk.
    DRAFT = "DRAFT"
    #: Live: the invited participants can quote and re-quote.
    OPEN = "OPEN"
    #: Settled. Quotations are frozen; a winner may be chosen afterwards.
    CLOSED = "CLOSED"


class QuantityUnit(_Str):
    MT = "MT"
    KG = "KG"
    BAG = "BAG"
    LITRE = "LITRE"
    PIECE = "PIECE"


class ActivityType(_Str):
    CALL = "CALL"
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"
    VISIT = "VISIT"
    EMAIL = "EMAIL"
    MEETING = "MEETING"


class ActivityStatus(_Str):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ActivityOutcome(_Str):
    """Structured result captured when an activity is completed."""

    COMPLETED = "COMPLETED"
    CUSTOMER_INTERESTED = "CUSTOMER_INTERESTED"
    CUSTOMER_NOT_INTERESTED = "CUSTOMER_NOT_INTERESTED"
    FOLLOW_UP_REQUIRED = "FOLLOW_UP_REQUIRED"
    NO_RESPONSE = "NO_RESPONSE"
    RESCHEDULED = "RESCHEDULED"
    OTHER = "OTHER"


class MessageDeliveryStatus(_Str):
    """How an outbound WhatsApp message fared."""

    PENDING = "PENDING"
    #: Nothing was attempted: no number on file, or WhatsApp not configured.
    SKIPPED = "SKIPPED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"


class AuditAction(_Str):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    STATUS_CHANGE = "STATUS_CHANGE"
    CLOSE = "CLOSE"
    COMPLETE = "COMPLETE"
    ASSIGN = "ASSIGN"
    MERGE = "MERGE"
    PUBLISH = "PUBLISH"
    QUOTE = "QUOTE"
    AWARD = "AWARD"
    PROMOTE = "PROMOTE"


def _enum(enum_cls: type[Enum], name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=32,
        validate_strings=True,
        values_callable=lambda e: [member.value for member in e],
    )


status_enum = _enum(RecordStatus, "record_status")
user_role_enum = _enum(UserRole, "user_role")
party_type_enum = _enum(PartyType, "party_type")
party_stage_enum = _enum(PartyStage, "party_stage")
party_source_enum = _enum(PartySource, "party_source")
location_type_enum = _enum(LocationType, "location_type")
party_product_rel_enum = _enum(PartyProductRelationship, "party_product_relationship")
inquiry_type_enum = _enum(InquiryType, "inquiry_type")
inquiry_status_enum = _enum(InquiryStatus, "inquiry_status")
inquiry_source_enum = _enum(InquirySource, "inquiry_source")
quantity_unit_enum = _enum(QuantityUnit, "quantity_unit")
bid_type_enum = _enum(BidType, "bid_type")
bid_status_enum = _enum(BidStatus, "bid_status")
activity_type_enum = _enum(ActivityType, "activity_type")
activity_status_enum = _enum(ActivityStatus, "activity_status")
activity_outcome_enum = _enum(ActivityOutcome, "activity_outcome")
message_delivery_status_enum = _enum(MessageDeliveryStatus, "message_delivery_status")
audit_action_enum = _enum(AuditAction, "audit_action")
