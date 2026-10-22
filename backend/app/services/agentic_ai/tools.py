"""The only things an agent is allowed to do to the database.

Every tool here is a thin wrapper over a function the desk already uses. None
of them writes SQL, none of them touches a table directly, and none of them
knows a business rule the portal does not already enforce - an enquiry arriving
by WhatsApp goes through exactly the path an enquiry typed into the portal form
goes through, so the two cannot drift apart.

Two things the agent never supplies, because it could invent either:

* **Who the enquiry is for.** The party is bound into the tool before the agent
  ever sees it, resolved from the phone number the message came from.
* **Any row id at all.** Materials, grades, manufacturers and towns are passed
  by name and resolved on our side. An id from a model is a number that looks
  right, which is the worst kind of wrong.

Tools return a sentence, because that is what the model reads back. What the
caller acts on is :class:`ToolOutcome`, recorded on the side.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import InquirySource, PartyType, QuantityUnit, RecordStatus
from app.models.masters import Material, Product
from app.models.party import Party
from app.schemas.portal_enquiry import PortalEnquiryRequest
from app.services import portal_enquiries
from app.services.agentic_ai.config import AIUnavailable
from app.services.agentic_ai.schemas import (
    CustomerEnquiry,
    SupplierEnquiry,
    TransportEnquiry,
)

logger = logging.getLogger(__name__)

#: How many names the lookup tool will show. Enough to recognise, short enough
#: that it does not become most of the prompt.
LOOKUP_LIMIT = 40


def _structured_tool():
    """LangChain, loaded only when an agent is actually about to run.

    The desk is a trading application that happens to have agents in it, not
    the other way round: a deployment that has not installed the AI packages
    serves every other screen exactly as before, and reports the agents
    unavailable rather than failing to start.
    """
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as error:  # pragma: no cover - depends on what is installed
        raise AIUnavailable(f"LangChain is not installed: {error}") from error
    return StructuredTool


@dataclass
class ToolOutcome:
    """What the tools actually did, kept out of the model's reach."""

    inquiry_id: int | None = None
    enquiry_id: int | None = None
    errors: list[str] = field(default_factory=list)
    calls: int = 0

    @property
    def created(self) -> bool:
        return self.inquiry_id is not None


def _catalogue(session: Session) -> str:
    """What the desk carries, as a line the model can match against.

    Shown so the agent writes "PVC" where the desk says PVC rather than
    "pvc granules", which would otherwise become a second material. It is a
    hint, not a constraint: a grade we have never traded is still allowed
    through, because the portal creates it either way.
    """
    materials = session.scalars(
        Material.__table__.select()
        .with_only_columns(Material.name)
        .where(Material.status == RecordStatus.ACTIVE)
        .order_by(Material.name)
        .limit(LOOKUP_LIMIT)
    ).all()
    products = session.scalars(
        Product.__table__.select()
        .with_only_columns(Product.display_name)
        .where(Product.status == RecordStatus.ACTIVE)
        .order_by(Product.display_name)
        .limit(LOOKUP_LIMIT)
    ).all()
    if not materials and not products:
        return "The desk has no products on record yet."
    return (
        f"Materials the desk carries: {', '.join(materials) or 'none'}.\n"
        f"Grades traded recently: {', '.join(products) or 'none'}.\n"
        "Use these spellings when the message means one of them. Anything else "
        "is still allowed - say what the message said."
    )


def _submit(
    session: Session,
    party: Party,
    outcome: ToolOutcome,
    payload: PortalEnquiryRequest,
) -> str:
    """Hand a filled-in enquiry to the portal's own creation path.

    This is the single place the agents reach the database, and it goes through
    ``portal_enquiries.submit_for`` - the function the portal form calls - so
    the validation, the master-data resolution and the inquiry itself are the
    same work, done once.
    """
    outcome.calls += 1
    if outcome.created:
        # The agent has already recorded this message. Saying so plainly is
        # what stops it trying again in a loop.
        return (
            f"An enquiry was already created for this message "
            f"(inquiry #{outcome.inquiry_id}). Nothing more to do."
        )
    try:
        enquiry = portal_enquiries.submit_for(session, party, payload, InquirySource.WHATSAPP)
    except AppError as error:
        # A rule the desk already enforces said no. The agent is told why, in
        # case the message holds something better.
        outcome.errors.append(str(error))
        logger.info("agentic ai: enquiry refused for party %s: %s", party.id, error)
        return f"That was refused: {error}"
    except Exception as error:  # pragma: no cover - a real database fault
        outcome.errors.append(str(error))
        logger.exception("agentic ai: enquiry failed for party %s", party.id)
        return f"That could not be saved: {error}"

    outcome.inquiry_id = enquiry.inquiry_id
    outcome.enquiry_id = enquiry.id
    logger.info(
        "agentic ai: created inquiry %s for party %s from whatsapp",
        enquiry.inquiry_id,
        party.id,
    )
    return f"Recorded. The desk now has inquiry #{enquiry.inquiry_id}."


def _as_decimal(value) -> Decimal | None:
    """Models hand back numbers as numbers, strings, or not at all."""
    if value is None or value == "":
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _unit(value: str | None) -> QuantityUnit:
    try:
        return QuantityUnit(value) if value else QuantityUnit.MT
    except ValueError:
        return QuantityUnit.MT


def _lookup_tool(session: Session):
    return _structured_tool().from_function(
        func=lambda: _catalogue(session),
        name="list_known_products",
        description=(
            "List the materials and grades the desk already carries. Call this "
            "before recording an enquiry, so you use the desk's own spelling."
        ),
    )


def customer_tools(session: Session, party: Party, outcome: ToolOutcome) -> list:
    """What a customer enquiry agent may do: look things up, and record one."""

    def record(
        material: str,
        grade: str,
        manufacturer: str,
        quantity: float,
        unit: str = "MT",
        deliver_to: str | None = None,
        rate: float | None = None,
        notes: str | None = None,
    ) -> str:
        draft = CustomerEnquiry(
            material=material,
            grade=grade,
            manufacturer=manufacturer,
            quantity=_as_decimal(quantity),
            unit=_unit(unit),
            deliver_to=deliver_to,
            rate=_as_decimal(rate),
            notes=notes,
        )
        return _submit(
            session,
            party,
            outcome,
            PortalEnquiryRequest(
                material_text=draft.material,
                grade_text=draft.grade,
                manufacturer_text=draft.manufacturer,
                quantity=draft.quantity,
                unit=draft.unit,
                to_place=draft.deliver_to,
                rate=draft.rate,
                notes=draft.notes,
            ),
        )

    return [
        _lookup_tool(session),
        _structured_tool().from_function(
            func=record,
            name="record_customer_enquiry",
            description=(
                "Record what this customer wants to buy. Material, grade, "
                "manufacturer and quantity are required; delivery town, rate "
                "in rupees per kilogram and notes only if the message says so."
            ),
            args_schema=CustomerEnquiry,
        ),
    ]


def supplier_tools(session: Session, party: Party, outcome: ToolOutcome) -> list:
    """What a supplier enquiry agent may do. No place: the desk does not ask."""

    def record(
        material: str,
        grade: str,
        manufacturer: str,
        quantity: float,
        unit: str = "MT",
        rate: float | None = None,
        notes: str | None = None,
    ) -> str:
        draft = SupplierEnquiry(
            material=material,
            grade=grade,
            manufacturer=manufacturer,
            quantity=_as_decimal(quantity),
            unit=_unit(unit),
            rate=_as_decimal(rate),
            notes=notes,
        )
        return _submit(
            session,
            party,
            outcome,
            PortalEnquiryRequest(
                material_text=draft.material,
                grade_text=draft.grade,
                manufacturer_text=draft.manufacturer,
                quantity=draft.quantity,
                unit=draft.unit,
                rate=draft.rate,
                notes=draft.notes,
            ),
        )

    return [
        _lookup_tool(session),
        _structured_tool().from_function(
            func=record,
            name="record_supplier_enquiry",
            description=(
                "Record what this supplier is offering. Material, grade, "
                "manufacturer and quantity are required; rate in rupees per "
                "kilogram and notes only if the message says so."
            ),
            args_schema=SupplierEnquiry,
        ),
    ]


def transport_tools(session: Session, party: Party, outcome: ToolOutcome) -> list:
    """What a transport enquiry agent may do. A load has no product in it."""

    def record(
        quantity: float,
        pickup: str,
        delivery: str,
        unit: str = "MT",
        freight: float | None = None,
        notes: str | None = None,
    ) -> str:
        draft = TransportEnquiry(
            quantity=_as_decimal(quantity),
            unit=_unit(unit),
            pickup=pickup,
            delivery=delivery,
            freight=_as_decimal(freight),
            notes=notes,
        )
        return _submit(
            session,
            party,
            outcome,
            PortalEnquiryRequest(
                quantity=draft.quantity,
                unit=draft.unit,
                from_place=draft.pickup,
                to_place=draft.delivery,
                rate=draft.freight,
                notes=draft.notes,
            ),
        )

    return [
        _structured_tool().from_function(
            func=record,
            name="record_transport_enquiry",
            description=(
                "Record the load this transporter can take. Quantity, pickup "
                "and delivery are required; freight for the whole load in "
                "rupees and notes only if the message says so."
            ),
            args_schema=TransportEnquiry,
        )
    ]


#: Which set of tools belongs to which side of the trade.
TOOLS_FOR = {
    PartyType.CUSTOMER: customer_tools,
    PartyType.SUPPLIER: supplier_tools,
    PartyType.TRANSPORTER: transport_tools,
}


def tools_for(session: Session, party: Party, outcome: ToolOutcome) -> list:
    """The tools this party's enquiry agent gets, and only those."""
    return TOOLS_FOR[party.party_type](session, party, outcome)
