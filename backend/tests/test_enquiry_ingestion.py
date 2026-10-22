"""Reading inbound WhatsApp messages, and what the desk ends up with.

No model is called here. ``agentic_ai`` exposes a backend seam, and these tests
put a scripted one behind it - the same arrangement the WhatsApp sending
service uses for its transport. What that buys is worth saying: everything
below the model is real. The scripted agent calls the real LangChain tools,
which call ``portal_enquiries.submit_for``, which resolves master data and
writes a real inquiry. The only thing faked is the sentence a model would have
produced.

So these cover the pipeline and the tools and the database, and the thing they
cannot cover - whether Gemini reads "rate kya hai" correctly - is the one thing
no test could have covered anyway.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.enums import MessageProcessing, PartySource, PartyStage, PartyType
from app.models.inquiry import Inquiry
from app.models.party import Party
from app.models.whatsapp_message import WhatsAppMessage
from app.services import agentic_ai, enquiry_ingestion
from app.services.agentic_ai.schemas import Classification, EnquiryResult, SenderIdentity


# --------------------------------------------------------------------------- #
# A backend that answers from a script, and calls the tools for real
# --------------------------------------------------------------------------- #
class ScriptedBackend:
    """Stands in for Gemini: canned answers, real tool calls.

    ``tool_call`` is the arguments a model would have passed to the recording
    tool. Leaving it None is an agent that read the message and decided it did
    not say enough - which is a thing that happens, and has to be handled.
    """

    def __init__(
        self,
        *,
        classification: Classification | None = None,
        identity: SenderIdentity | None = None,
        tool_call: dict | None = None,
        fail_on: str | None = None,
    ) -> None:
        self.classification = classification or Classification(
            is_enquiry=True, confidence=0.95, reason="Asks for a quantity and a grade."
        )
        self.identity = identity
        self.tool_call = tool_call
        self.fail_on = fail_on
        self.seen: list[str] = []

    def _check(self, agent: str) -> None:
        self.seen.append(agent)
        if self.fail_on and self.fail_on in agent:
            raise agentic_ai.AgentError(f"{agent} is pretending to be broken")

    def classify(self, agent: str, message: str) -> Classification:
        self._check(agent)
        return self.classification

    def identify(self, agent: str, message: str, profile_name: str | None) -> SenderIdentity:
        self._check(agent)
        if self.identity is None:
            raise AssertionError(f"{agent} was called but the script has no identity for it")
        return self.identity

    def extract(self, agent: str, message: str, tools) -> EnquiryResult:
        self._check(agent)
        if self.tool_call is None:
            return EnquiryResult(created=False, note="The message did not give a quantity.")
        recorder = next(tool for tool in tools if tool.name.startswith("record_"))
        said = recorder.invoke(self.tool_call)
        return EnquiryResult(created="Recorded" in said, note=said)


@pytest.fixture
def backend():
    """Install a scripted backend, and take it out again afterwards."""

    def install(**kwargs) -> ScriptedBackend:
        scripted = ScriptedBackend(**kwargs)
        agentic_ai.set_backend(scripted)
        return scripted

    yield install
    agentic_ai.reset_backend()


@pytest.fixture(autouse=True)
def _no_real_model():
    """No test may reach a real model, even one that forgets to script it."""
    yield
    agentic_ai.reset_backend()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def arrive(
    db_session,
    body: str,
    *,
    number: str = "917801833884",
    wa_id: str = "wamid.IN1",
    name: str | None = "Jay Transport",
    party_id: int | None = None,
    kind: str = "text",
) -> WhatsAppMessage:
    """A message, recorded the way the webhook records one."""
    message = WhatsAppMessage(
        wa_message_id=wa_id,
        from_number=number,
        message_type=kind,
        body=body,
        profile_name=name,
        sent_at=datetime.now(UTC),
        received_at=datetime.now(UTC),
        party_id=party_id,
        processing_status=MessageProcessing.PENDING,
    )
    db_session.add(message)
    db_session.flush()
    return message


def with_phone(client, auth, party_id: int, phone: str) -> int:
    client.patch(f"/api/v1/parties/{party_id}", json={"phone": phone}, headers=auth)
    return party_id


def inquiries_on_the_book(db_session) -> list[Inquiry]:
    return list(db_session.scalars(select(Inquiry).order_by(Inquiry.id)).all())


CUSTOMER_CALL = {
    "material": "PVC",
    "grade": "K-67",
    "manufacturer": "Reliance",
    "quantity": 20,
    "unit": "MT",
    "deliver_to": "Rajkot",
    "rate": 91.5,
    "notes": "Needs it this week.",
}

SUPPLIER_CALL = {
    "material": "PVC",
    "grade": "K-67",
    "manufacturer": "Reliance",
    "quantity": 25,
    "unit": "MT",
    "rate": 90.25,
}

TRANSPORT_CALL = {
    "quantity": 20,
    "unit": "MT",
    "pickup": "Gandhidham",
    "delivery": "Mumbai",
    "freight": 18000,
}


# --------------------------------------------------------------------------- #
# A party the desk knows
# --------------------------------------------------------------------------- #
def test_a_known_customer_asking_for_a_rate_lands_on_the_book(
    client, auth, db_session, parties, masters, backend
):
    with_phone(client, auth, parties["customer"], "9825011111")
    agent = backend(tool_call=CUSTOMER_CALL)
    message = arrive(
        db_session, "Need 20 MT Reliance K-67 for Rajkot, rate?", number="919825011111"
    )

    outcome = enquiry_ingestion.process(db_session, message)

    assert outcome.status is MessageProcessing.PROCESSED
    assert agent.seen == ["customer_classification_agent", "customer_enquiry_agent"]

    inquiry = inquiries_on_the_book(db_session)[0]
    assert inquiry.id == outcome.inquiry_id
    assert inquiry.inquiry_type.value == "CUSTOMER"
    assert inquiry.source.value == "WHATSAPP"
    assert inquiry.created_by is None, "no salesperson is behind it"
    detail = inquiry.customer_detail
    assert detail.customer_id == parties["customer"]
    assert detail.product.display_name == "Reliance PVC K-67"
    assert str(detail.quantity) == "20.000"
    assert str(detail.rate) == "91.50"
    assert detail.location.city == "Rajkot"
    assert message.inquiry_id == inquiry.id


def test_a_known_supplier_offering_material(client, auth, db_session, parties, masters, backend):
    with_phone(client, auth, parties["supplier"], "9825022222")
    agent = backend(tool_call=SUPPLIER_CALL)
    message = arrive(db_session, "We have 25 MT K-67 at 90.25", number="919825022222")

    enquiry_ingestion.process(db_session, message)

    assert agent.seen == ["supplier_classification_agent", "supplier_enquiry_agent"]
    inquiry = inquiries_on_the_book(db_session)[0]
    assert inquiry.inquiry_type.value == "SUPPLIER"
    assert inquiry.supplier_detail.supplier_id == parties["supplier"]
    assert inquiry.supplier_detail.location is None, "a supplier is not asked where from"


def test_a_known_transporter_offering_a_load(client, auth, db_session, parties, backend):
    with_phone(client, auth, parties["transporter"], "9825033333")
    agent = backend(tool_call=TRANSPORT_CALL)
    message = arrive(db_session, "20 MT truck Gandhidham to Mumbai, 18000", number="919825033333")

    enquiry_ingestion.process(db_session, message)

    assert agent.seen == ["transporter_classification_agent", "transporter_enquiry_agent"]
    inquiry = inquiries_on_the_book(db_session)[0]
    assert inquiry.inquiry_type.value == "TRANSPORT"
    detail = inquiry.transport_detail
    assert detail.transporter_id == parties["transporter"]
    assert detail.pickup_location.city == "Gandhidham"
    assert detail.delivery_location.city == "Mumbai"
    assert str(detail.price) == "18000.00"


def test_a_known_party_saying_thanks_creates_nothing(client, auth, db_session, parties, backend):
    """Most of what arrives on a trading desk's WhatsApp is not an enquiry."""
    with_phone(client, auth, parties["customer"], "9825011111")
    agent = backend(
        classification=Classification(is_enquiry=False, confidence=0.98, reason="A thank-you."),
    )
    message = arrive(db_session, "Thank you sir, received", number="919825011111")

    outcome = enquiry_ingestion.process(db_session, message)

    assert outcome.status is MessageProcessing.IGNORED
    assert "Not an enquiry" in outcome.note
    assert agent.seen == ["customer_classification_agent"], "the enquiry agent never ran"
    assert inquiries_on_the_book(db_session) == []


def test_an_unsure_classification_is_treated_as_a_no(client, auth, db_session, parties, backend):
    """A wrong row on the book costs more than a missed follow-up."""
    with_phone(client, auth, parties["customer"], "9825011111")
    backend(
        classification=Classification(is_enquiry=True, confidence=0.30, reason="Could be."),
        tool_call=CUSTOMER_CALL,
    )
    message = arrive(db_session, "k67?", number="919825011111")

    outcome = enquiry_ingestion.process(db_session, message)

    assert outcome.status is MessageProcessing.IGNORED
    assert "not certain" in outcome.note
    assert inquiries_on_the_book(db_session) == []


# --------------------------------------------------------------------------- #
# A number nobody has introduced
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("role", "party_type", "call", "kind"),
    [
        ("CUSTOMER", PartyType.CUSTOMER, CUSTOMER_CALL, "CUSTOMER"),
        ("SUPPLIER", PartyType.SUPPLIER, SUPPLIER_CALL, "SUPPLIER"),
        ("TRANSPORTER", PartyType.TRANSPORTER, TRANSPORT_CALL, "TRANSPORT"),
    ],
)
def test_a_stranger_becomes_a_prospect_and_an_enquiry(
    db_session, masters, backend, role, party_type, call, kind
):
    agent = backend(
        identity=SenderIdentity(
            role=role,
            confidence=0.9,
            reason="They say so.",
            name="Shreeji Polymers",
            contact_person="Mehul",
            city="Surat",
        ),
        tool_call=call,
    )
    message = arrive(db_session, "Need 20 MT K-67", number="919000000001", name="Mehul")

    outcome = enquiry_ingestion.process(db_session, message)

    assert outcome.status is MessageProcessing.PROCESSED
    assert agent.seen[:2] == ["unknown_classifier", "unknown_role_classifier"]

    party = db_session.get(Party, outcome.party_id)
    assert party.name == "Shreeji Polymers"
    assert party.party_type is party_type
    assert party.stage is PartyStage.PROSPECT, "a stranger is a prospect, not a customer"
    assert party.source is PartySource.WHATSAPP
    assert party.phone == "919000000001"
    assert party.contact_person == "Mehul"

    inquiry = inquiries_on_the_book(db_session)[0]
    assert inquiry.inquiry_type.value == kind
    assert inquiry.source.value == "WHATSAPP"
    assert message.party_id == party.id


def test_a_stranger_selling_something_else_is_ignored(db_session, backend):
    """Nothing is created - not a prospect, not a note. The message is the record."""
    agent = backend(
        classification=Classification(
            is_enquiry=False, confidence=0.97, reason="Marketing for a loan."
        )
    )
    message = arrive(db_session, "Get a business loan at 9% interest!", number="919000000002")

    outcome = enquiry_ingestion.process(db_session, message)

    assert outcome.status is MessageProcessing.IGNORED
    assert agent.seen == ["unknown_classifier"], "nothing else was asked"
    assert db_session.scalar(select(Party).where(Party.phone == "919000000002")) is None
    assert inquiries_on_the_book(db_session) == []


def test_a_stranger_whose_side_is_unclear_creates_nothing(db_session, backend):
    """A party filed under the wrong side is worse than one nobody filed."""
    backend(
        identity=SenderIdentity(role=None, confidence=0.2, reason="Names no side of the trade."),
        tool_call=CUSTOMER_CALL,
    )
    message = arrive(db_session, "K-67 20 MT", number="919000000003")

    outcome = enquiry_ingestion.process(db_session, message)

    assert outcome.status is MessageProcessing.IGNORED
    assert "which side of the trade is unclear" in outcome.note
    assert db_session.scalar(select(Party).where(Party.phone == "919000000003")) is None
    assert inquiries_on_the_book(db_session) == []


def test_a_confident_role_on_a_doubtful_reading_is_still_refused(db_session, backend):
    backend(
        identity=SenderIdentity(role="CUSTOMER", confidence=0.4, reason="Leaning that way."),
        tool_call=CUSTOMER_CALL,
    )
    message = arrive(db_session, "K-67 20 MT", number="919000000004")

    assert enquiry_ingestion.process(db_session, message).status is MessageProcessing.IGNORED
    assert inquiries_on_the_book(db_session) == []


def test_a_stranger_the_desk_already_knows_is_not_written_down_twice(
    client, auth, db_session, parties, masters, backend
):
    """The lookup is on the number, never on what the model called them."""
    with_phone(client, auth, parties["customer"], "9825011111")
    backend(
        identity=SenderIdentity(role="CUSTOMER", confidence=0.9, reason="Buying.", name="A Nother"),
        tool_call=CUSTOMER_CALL,
    )
    # Arrives with no party matched, as a webhook with a stale match would.
    message = arrive(db_session, "Need 20 MT K-67", number="919825011111", party_id=None)

    outcome = enquiry_ingestion.process(db_session, message)

    assert outcome.party_id == parties["customer"]
    assert db_session.scalar(select(Party).where(Party.name == "A Nother")) is None


def test_a_stranger_who_gave_no_name_is_still_recognisable(db_session, masters, backend):
    backend(
        identity=SenderIdentity(role="CUSTOMER", confidence=0.9, reason="Buying."),
        tool_call=CUSTOMER_CALL,
    )
    message = arrive(db_session, "Need 20 MT K-67", number="919000000005", name=None)

    outcome = enquiry_ingestion.process(db_session, message)

    party = db_session.get(Party, outcome.party_id)
    assert party.name == "+919000000005", "the number itself, rather than nothing"


# --------------------------------------------------------------------------- #
# Reading the same thing twice
# --------------------------------------------------------------------------- #
def test_a_message_is_read_once(client, auth, db_session, parties, masters, backend):
    """Meta can deliver the same webhook all day."""
    with_phone(client, auth, parties["customer"], "9825011111")
    backend(tool_call=CUSTOMER_CALL)
    message = arrive(db_session, "Need 20 MT K-67", number="919825011111")

    first = enquiry_ingestion.process(db_session, message)
    second = enquiry_ingestion.process(db_session, message)

    assert first.status is MessageProcessing.PROCESSED
    assert second.note == "Already read."
    assert len(inquiries_on_the_book(db_session)) == 1


def test_a_batch_reads_only_what_is_waiting(client, auth, db_session, parties, masters, backend):
    with_phone(client, auth, parties["customer"], "9825011111")
    backend(tool_call=CUSTOMER_CALL)
    arrive(db_session, "Need 20 MT K-67", number="919825011111", wa_id="wamid.A")
    arrive(db_session, "Need 20 MT K-67", number="919825011111", wa_id="wamid.B")

    first = enquiry_ingestion.process_pending(db_session)
    second = enquiry_ingestion.process_pending(db_session)

    assert first["processed"] == 2
    assert second == {key: 0 for key in second}, "nothing is left to read"
    assert len(inquiries_on_the_book(db_session)) == 2


def test_the_agent_is_told_when_its_tool_has_already_done_the_job(
    client, auth, db_session, parties, masters, backend
):
    """A model that calls its tool twice must not produce two inquiries."""
    with_phone(client, auth, parties["customer"], "9825011111")
    outcome = agentic_ai.ToolOutcome()
    party = db_session.get(Party, parties["customer"])
    tools = agentic_ai.tools_for(db_session, party, outcome)
    recorder = next(tool for tool in tools if tool.name.startswith("record_"))

    first = recorder.invoke(CUSTOMER_CALL)
    second = recorder.invoke(CUSTOMER_CALL)

    assert "Recorded" in first
    assert "already created" in second
    assert len(inquiries_on_the_book(db_session)) == 1
    assert outcome.calls == 2


# --------------------------------------------------------------------------- #
# When things go wrong
# --------------------------------------------------------------------------- #
def test_an_agent_that_fails_leaves_the_message_to_retry(
    client, auth, db_session, parties, backend
):
    with_phone(client, auth, parties["customer"], "9825011111")
    backend(fail_on="classification")
    message = arrive(db_session, "Need 20 MT K-67", number="919825011111")

    outcome = enquiry_ingestion.process(db_session, message)

    assert outcome.status is MessageProcessing.FAILED
    assert "pretending to be broken" in outcome.note
    assert message.processing_note is not None
    assert inquiries_on_the_book(db_session) == []


def test_an_enquiry_agent_that_fails_is_recorded_as_a_failure(
    client, auth, db_session, parties, backend
):
    with_phone(client, auth, parties["customer"], "9825011111")
    backend(fail_on="enquiry_agent", tool_call=CUSTOMER_CALL)
    message = arrive(db_session, "Need 20 MT K-67", number="919825011111")

    assert enquiry_ingestion.process(db_session, message).status is MessageProcessing.FAILED
    assert inquiries_on_the_book(db_session) == []


def test_a_tool_the_desk_refuses_is_a_failure_not_a_silent_drop(
    client, auth, db_session, parties, backend
):
    """The desk's own rules still apply - a load cannot start and end in one town."""
    with_phone(client, auth, parties["transporter"], "9825033333")
    backend(
        tool_call={**TRANSPORT_CALL, "pickup": "Rajkot", "delivery": "rajkot"},
    )
    message = arrive(db_session, "Rajkot to Rajkot 20 MT", number="919825033333")

    outcome = enquiry_ingestion.process(db_session, message)

    assert outcome.status is MessageProcessing.FAILED
    assert "refused" in outcome.note.lower()
    assert inquiries_on_the_book(db_session) == []


def test_an_enquiry_that_did_not_say_enough_is_left_for_a_person(
    client, auth, db_session, parties, backend
):
    """The agent read it, could not fill the required fields, and said so."""
    with_phone(client, auth, parties["customer"], "9825011111")
    backend(tool_call=None)
    message = arrive(db_session, "Need some K-67", number="919825011111")

    outcome = enquiry_ingestion.process(db_session, message)

    assert outcome.status is MessageProcessing.IGNORED
    assert "did not give a quantity" in outcome.note
    assert inquiries_on_the_book(db_session) == []


def test_a_message_with_no_words_is_not_sent_to_a_model(db_session, backend):
    agent = backend()
    message = arrive(db_session, "", kind="image", number="919000000006")

    outcome = enquiry_ingestion.process(db_session, message)

    assert outcome.status is MessageProcessing.IGNORED
    assert "image" in outcome.note
    assert agent.seen == [], "nothing was asked of the model"


def test_without_a_model_nothing_is_read_and_nothing_is_lost(db_session):
    """How the desk runs before any of this is switched on."""
    agentic_ai.reset_backend()
    message = arrive(db_session, "Need 20 MT K-67", number="919000000007")

    outcome = enquiry_ingestion.process(db_session, message)

    assert outcome.status is MessageProcessing.SKIPPED
    assert "switched off" in outcome.note
    assert message.processing_status is MessageProcessing.SKIPPED


# --------------------------------------------------------------------------- #
# The agents themselves
# --------------------------------------------------------------------------- #
def test_every_agent_in_the_design_exists_and_has_a_prompt():
    from app.services.agentic_ai import prompts
    from app.services.agentic_ai.agents import _PROMPT_FOR

    expected = {
        "customer_classification_agent",
        "supplier_classification_agent",
        "transporter_classification_agent",
        "customer_enquiry_agent",
        "supplier_enquiry_agent",
        "transporter_enquiry_agent",
        "unknown_classifier",
        "unknown_role_classifier",
    }
    assert set(agentic_ai.AGENT_NAMES) == expected
    assert all(_PROMPT_FOR[name].strip() for name in expected)
    assert prompts.DESK in _PROMPT_FOR["customer_classification_agent"]


def test_each_side_of_the_trade_gets_only_its_own_tools(db_session, parties):
    """A transporter's agent has no way to record a product enquiry."""
    outcome = agentic_ai.ToolOutcome()
    names = {
        kind: {
            tool.name
            for tool in agentic_ai.tools_for(
                db_session, db_session.get(Party, parties[kind]), outcome
            )
        }
        for kind in ("customer", "supplier", "transporter")
    }

    assert names["customer"] == {"list_known_products", "record_customer_enquiry"}
    assert names["supplier"] == {"list_known_products", "record_supplier_enquiry"}
    assert names["transporter"] == {"record_transport_enquiry"}


def test_the_lookup_tool_shows_the_desks_own_names(db_session, parties, masters):
    outcome = agentic_ai.ToolOutcome()
    tools = agentic_ai.tools_for(db_session, db_session.get(Party, parties["customer"]), outcome)
    catalogue = next(tool for tool in tools if tool.name == "list_known_products").invoke({})

    assert "PVC" in catalogue
    assert "Reliance PVC K-67" in catalogue


def test_nothing_is_configured_until_it_is_configured():
    """The desk has to keep working with no model at all."""
    agentic_ai.reset_backend()
    assert agentic_ai.is_configured() is False
    assert "switched off" in agentic_ai.why_not()
    assert agentic_ai.available() is False
