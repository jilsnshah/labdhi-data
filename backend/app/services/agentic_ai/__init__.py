"""Agentic AI: the desk's agents, their prompts, their tools, and one model.

Everything to do with running a language model lives behind this package, so
that no other service has to know which model, which provider, or how a tool
call is managed. A service that wants an agent asks for an answer and gets a
validated object back.

* ``config``  - which model, reached how. The only place either is decided.
* ``schemas`` - what an agent is allowed to say. Nothing else gets through.
* ``prompts`` - what each agent is told before it reads anything.
* ``tools``   - the only things an agent may do to the database, each one a
  wrapper over a function the desk already uses.
* ``agents``  - the eight agents, and the seam that lets tests replace the
  model entirely.

Nothing here decides *when* an agent runs. That is the pipeline's job, and
keeping it out of here is what lets another agent be added without reading it.
"""

from app.services.agentic_ai.agents import (
    AGENT_NAMES,
    AgentError,
    Backend,
    available,
    backend,
    classify_known,
    classify_unknown,
    describe,
    identify_sender,
    record_enquiry,
    reset_backend,
    set_backend,
)
from app.services.agentic_ai.config import AIUnavailable, is_configured, reset_model, why_not
from app.services.agentic_ai.schemas import (
    Classification,
    CustomerEnquiry,
    EnquiryResult,
    Role,
    SenderIdentity,
    SupplierEnquiry,
    TransportEnquiry,
)
from app.services.agentic_ai.tools import ToolOutcome, tools_for

__all__ = [
    "AGENT_NAMES",
    "AIUnavailable",
    "AgentError",
    "Backend",
    "Classification",
    "CustomerEnquiry",
    "EnquiryResult",
    "Role",
    "SenderIdentity",
    "SupplierEnquiry",
    "ToolOutcome",
    "TransportEnquiry",
    "available",
    "backend",
    "classify_known",
    "classify_unknown",
    "describe",
    "identify_sender",
    "is_configured",
    "record_enquiry",
    "reset_backend",
    "reset_model",
    "set_backend",
    "tools_for",
    "why_not",
]
