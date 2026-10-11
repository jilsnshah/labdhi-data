"""Importing this package registers every model on ``Base.metadata``."""

from app.db.base import Base
from app.models.activity import Activity
from app.models.audit import AuditLog
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
from app.models.user import User

__all__ = [
    "Base",
    "Activity",
    "Application",
    "AuditLog",
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
    "Product",
    "SupplierInquiry",
    "TransportInquiry",
    "User",
    "product_applications",
]
