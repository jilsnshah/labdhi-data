"""Importing this package registers every model on ``Base.metadata``."""

from app.db.base import Base
from app.models.activity import Activity
from app.models.audit import AuditLog
from app.models.bid import Bid, BidParticipant, BidQuote
from app.models.inquiry import (
    CustomerInquiry,
    Inquiry,
    SupplierInquiry,
    TransportInquiry,
)
from app.models.masters import (
    Application,
    Grade,
    Manufacturer,
    Material,
    Product,
    product_applications,
)
from app.models.note import Note
from app.models.party import (
    Location,
    Party,
    PartyApplication,
    PartyLocation,
    PartyProduct,
)
from app.models.portal_enquiry import PortalEnquiry
from app.models.user import User

__all__ = [
    "Base",
    "Activity",
    "Application",
    "AuditLog",
    "Bid",
    "BidParticipant",
    "BidQuote",
    "CustomerInquiry",
    "Grade",
    "Inquiry",
    "Location",
    "Manufacturer",
    "Material",
    "Note",
    "Party",
    "PartyLocation",
    "PartyApplication",
    "PartyProduct",
    "PortalEnquiry",
    "Product",
    "SupplierInquiry",
    "TransportInquiry",
    "User",
    "product_applications",
]
