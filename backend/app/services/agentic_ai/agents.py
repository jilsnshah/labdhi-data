"""The agents. Eight of them, each with one job and no opinion about the rest.

Three classifiers for parties the desk knows, one for strangers, one that works
out which side of the trade a stranger is on, and three that read an enquiry
and record it. Nothing here orchestrates anything - which agent runs when is
``enquiry_ingestion``'s business, and keeping that out of here is what lets a
ninth agent be added without reading the pipeline.

Everything goes through :class:`Backend`, which is the seam the tests use. The
real one talks to Gemini through LangChain; a test substitutes its own and the
whole pipeline runs - tools, database, transactions and all - without a network
call or an API key. ``set_backend`` is the same arrangement the WhatsApp
sending service uses for its transport, for the same reason.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import settings
from app.models.enums import PartyType
from app.services.agentic_ai import prompts
from app.services.agentic_ai.config import AIUnavailable, chat_model, is_configured
from app.services.agentic_ai.schemas import Classification, EnquiryResult, SenderIdentity

logger = logging.getLogger(__name__)

#: Every agent this service answers for, by the name the pipeline asks for.
CLASSIFIER_FOR = {
    PartyType.CUSTOMER: "customer_classification_agent",
    PartyType.SUPPLIER: "supplier_classification_agent",
    PartyType.TRANSPORTER: "transporter_classification_agent",
}

ENQUIRY_AGENT_FOR = {
    PartyType.CUSTOMER: "customer_enquiry_agent",
    PartyType.SUPPLIER: "supplier_enquiry_agent",
    PartyType.TRANSPORTER: "transporter_enquiry_agent",
}

UNKNOWN_CLASSIFIER = "unknown_classifier"
UNKNOWN_ROLE_CLASSIFIER = "unknown_role_classifier"

_PROMPT_FOR = {
    "customer_classification_agent": prompts.CUSTOMER_CLASSIFICATION,
    "supplier_classification_agent": prompts.SUPPLIER_CLASSIFICATION,
    "transporter_classification_agent": prompts.TRANSPORTER_CLASSIFICATION,
    UNKNOWN_CLASSIFIER: prompts.UNKNOWN_CLASSIFICATION,
    UNKNOWN_ROLE_CLASSIFIER: prompts.UNKNOWN_ROLE,
    "customer_enquiry_agent": prompts.CUSTOMER_ENQUIRY,
    "supplier_enquiry_agent": prompts.SUPPLIER_ENQUIRY,
    "transporter_enquiry_agent": prompts.TRANSPORT_ENQUIRY,
}

#: Every agent named in the design, for anything that wants to check one exists.
AGENT_NAMES = tuple(_PROMPT_FOR)


def _runtime():
    """LangChain's agent runtime, loaded at the last moment.

    See ``tools._structured_tool``: the AI packages are optional, and a
    deployment without them runs everything else untouched.
    """
    try:
        from langchain.agents import create_agent
    except ImportError as error:  # pragma: no cover - depends on what is installed
        raise AIUnavailable(f"LangChain is not installed: {error}") from error
    return create_agent


def _answer_as(schema):
    """Ask for the answer as a tool call rather than as native JSON.

    Gemini's own structured-output mode returns an empty body often enough to
    be unusable here - a parse failure where there should have been a verdict.
    Asking the model to "call" a one-off tool shaped like the schema is the
    same question by a route every provider implements properly, and the
    answer comes back validated either way.
    """
    try:
        from langchain.agents.structured_output import ToolStrategy
    except ImportError as error:  # pragma: no cover - depends on what is installed
        raise AIUnavailable(f"LangChain is not installed: {error}") from error
    return ToolStrategy(schema)


class AgentError(Exception):
    """An agent could not answer. Distinct from an agent answering 'no'."""


class Backend(Protocol):
    """How the agents are actually run. Swapped in tests."""

    def classify(self, agent: str, message: str) -> Classification:
        """Is this an enquiry? For the four classifying agents."""

    def identify(self, agent: str, message: str, profile_name: str | None) -> SenderIdentity:
        """Which side of the trade is this stranger on, and who are they?"""

    def extract(self, agent: str, message: str, tools: list) -> EnquiryResult:
        """Read an enquiry and record it, using the tools given."""


class LangChainBackend:
    """The real one: Gemini, through LangChain's agent runtime.

    The classifying agents are given no tools at all - they have nothing to do
    but answer, and a tool they cannot use is a way to go wrong. The enquiry
    agents are given exactly the tools their side of the trade needs, already
    bound to the party and the session, so the only thing the model contributes
    is what the message said.
    """

    def _answer(self, agent: str, message: str, schema, extra: str = ""):
        create_agent = _runtime()

        prompt = _PROMPT_FOR[agent]
        try:
            runner = create_agent(
                model=chat_model(),
                tools=[],
                system_prompt=prompt,
                response_format=_answer_as(schema),
                name=agent,
            )
            result = runner.invoke({"messages": [("user", _as_input(message, extra))]})
        except AIUnavailable:
            raise
        except Exception as error:
            raise AgentError(f"{agent} could not answer: {error}") from error

        structured = result.get("structured_response") if isinstance(result, dict) else None
        if not isinstance(structured, schema):
            raise AgentError(f"{agent} did not answer in the expected shape.")
        return structured

    def classify(self, agent: str, message: str) -> Classification:
        return self._answer(agent, message, Classification)

    def identify(self, agent: str, message: str, profile_name: str | None) -> SenderIdentity:
        extra = f"The name on their WhatsApp account is: {profile_name}" if profile_name else ""
        return self._answer(agent, message, SenderIdentity, extra)

    def extract(self, agent: str, message: str, tools: list) -> EnquiryResult:
        create_agent = _runtime()

        try:
            runner = create_agent(
                model=chat_model(),
                tools=tools,
                system_prompt=_PROMPT_FOR[agent],
                response_format=_answer_as(EnquiryResult),
                name=agent,
            )
            result = runner.invoke(
                {"messages": [("user", _as_input(message))]},
                {"recursion_limit": settings.ai_max_tool_calls * 2},
            )
        except AIUnavailable:
            raise
        except Exception as error:
            if "recursion" in str(error).lower():
                # The agent went round its tools without settling. Usually it
                # was told the message lacks something required and kept trying
                # anyway. Nothing was created, so this is a message to leave for
                # a person rather than a fault to raise an alarm about.
                logger.info("agentic ai: %s went round in circles", agent)
                return EnquiryResult(
                    created=False, note="The agent could not settle on an answer."
                )
            raise AgentError(f"{agent} could not answer: {error}") from error

        structured = result.get("structured_response") if isinstance(result, dict) else None
        if isinstance(structured, EnquiryResult):
            return structured
        # The agent used its tool and then said nothing in the shape we asked
        # for. Whether anything was created is read off the tool's own record,
        # not off this, so an unusable summary is not a failure.
        return EnquiryResult(created=False, note="The agent gave no summary of its work.")


def _as_input(message: str, extra: str = "") -> str:
    body = f"The message is:\n\n{message.strip()}"
    return f"{body}\n\n{extra}".strip()


@dataclass
class _State:
    backend: Backend | None = None


_state = _State()


def set_backend(backend: Backend) -> None:
    """Swap how agents run. Tests use this; nothing else should."""
    _state.backend = backend


def reset_backend() -> None:
    _state.backend = None


def backend() -> Backend:
    """The backend in force, building the real one on first use."""
    if _state.backend is None:
        _state.backend = LangChainBackend()
    return _state.backend


# --------------------------------------------------------------------------- #
# What the pipeline calls
# --------------------------------------------------------------------------- #
def available() -> bool:
    """True when there is something to run the agents on."""
    return is_configured() or _state.backend is not None


def classify_known(party_type: PartyType, message: str) -> Classification:
    """Is a message from a party we know an enquiry?"""
    agent = CLASSIFIER_FOR[party_type]
    answer = backend().classify(agent, message)
    logger.info(
        "agentic ai: %s -> is_enquiry=%s confidence=%.2f",
        agent,
        answer.is_enquiry,
        answer.confidence,
    )
    return answer


def classify_unknown(message: str) -> Classification:
    """Is a message from a stranger an enquiry? A harder question."""
    answer = backend().classify(UNKNOWN_CLASSIFIER, message)
    logger.info(
        "agentic ai: %s -> is_enquiry=%s confidence=%.2f",
        UNKNOWN_CLASSIFIER,
        answer.is_enquiry,
        answer.confidence,
    )
    return answer


def identify_sender(message: str, profile_name: str | None = None) -> SenderIdentity:
    """Which side of the trade a stranger is on, and anything they said about themselves."""
    answer = backend().identify(UNKNOWN_ROLE_CLASSIFIER, message, profile_name)
    logger.info(
        "agentic ai: %s -> role=%s confidence=%.2f",
        UNKNOWN_ROLE_CLASSIFIER,
        answer.role,
        answer.confidence,
    )
    return answer


def record_enquiry(party_type: PartyType, message: str, tools: list) -> EnquiryResult:
    """Read an enquiry out of a message and record it through the tools given."""
    agent = ENQUIRY_AGENT_FOR[party_type]
    answer = backend().extract(agent, message, tools)
    logger.info("agentic ai: %s -> created=%s", agent, answer.created)
    return answer


def describe() -> dict[str, Any]:
    """What is configured, for a health check or a startup line."""
    return {
        "enabled": settings.ai_enabled,
        "provider": settings.ai_provider,
        "model": settings.ai_model,
        "configured": is_configured(),
        "agents": list(AGENT_NAMES),
    }
