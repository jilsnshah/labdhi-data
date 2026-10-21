"""Sending WhatsApp messages. That is the whole job.

This module knows nothing about bids, parties or the desk: it takes a phone
number and something to say, hands it to Meta's WhatsApp Cloud API, and reports
what happened. Whatever decides *what* to say lives elsewhere and calls in here.

Two rules it keeps:

* It never raises at the caller. A message that cannot be sent comes back as a
  refusal with a reason, because a bid must open whether or not the phone
  network cooperated.
* It never sends when it is not configured. Until the Meta credentials are in
  the environment, every call reports itself skipped and nothing goes out.

Business-initiated messages (which a bid invitation is) have to use a template
Meta has approved in advance; free text is only allowed inside a 24-hour window
opened by the customer writing first. ``send_template`` is therefore the one to
use for invitations, and ``send_text`` is for replies inside that window.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

#: Digits only, after stripping the punctuation traders type.
_NOT_DIGITS = re.compile(r"[^\d]")
#: A plain Indian mobile: ten digits starting 6-9.
_INDIAN_MOBILE = re.compile(r"^[6-9]\d{9}$")
#: What Meta will accept as a destination: country code and number, no plus.
_DIALLABLE = re.compile(r"^\d{10,15}$")


def to_e164(value: str | None) -> str | None:
    """A number Meta will accept, or None if it is not one.

    Indian numbers are written half a dozen ways - with +91, with a leading
    zero, with spaces, or as ten bare digits - and all of them mean the same
    phone. Anything that cannot be read as a dialable number is refused rather
    than guessed at, so a typo fails here instead of at Meta.
    """
    if not value:
        return None
    digits = _NOT_DIGITS.sub("", value)
    if not digits:
        return None

    # 0XXXXXXXXXX - the trunk prefix used when dialling within India.
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    # Ten bare digits: an Indian mobile, so say so.
    if _INDIAN_MOBILE.match(digits):
        digits = f"{settings.whatsapp_default_country_code}{digits}"

    return digits if _DIALLABLE.match(digits) else None


@dataclass
class SendResult:
    """What happened to one message. Never an exception."""

    ok: bool
    message_id: str | None = None
    error: str | None = None
    #: True when nothing was attempted because WhatsApp is not configured.
    skipped: bool = False


class Transport(Protocol):
    """How a payload reaches Meta. Swapped in tests."""

    def post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send one message. Raise on failure; the service turns that into a result."""


class MetaCloudTransport:
    """The real thing: one POST per message to the Cloud API."""

    def post(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = (
            f"https://graph.facebook.com/{settings.whatsapp_api_version}"
            f"/{settings.whatsapp_phone_number_id}/messages"
        )
        response = httpx.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            timeout=settings.whatsapp_timeout_seconds,
        )
        if response.status_code >= 400:
            # Meta puts the useful part in error.message; fall back to the body.
            try:
                detail = response.json().get("error", {})
                reason = detail.get("message") or response.text
                code = detail.get("code")
                raise WhatsAppError(f"{code}: {reason}" if code else str(reason))
            except ValueError:
                raise WhatsAppError(f"HTTP {response.status_code}: {response.text}") from None
        return response.json()


class WhatsAppError(Exception):
    """Meta refused the message, or could not be reached."""


@dataclass
class _State:
    transport: Transport = field(default_factory=MetaCloudTransport)


_state = _State()


def set_transport(transport: Transport) -> None:
    """Swap how messages leave. Tests use this; nothing else should."""
    _state.transport = transport


def reset_transport() -> None:
    _state.transport = MetaCloudTransport()


def is_configured() -> bool:
    """True when there are credentials to send with."""
    return bool(settings.whatsapp_access_token and settings.whatsapp_phone_number_id)


# --------------------------------------------------------------------------- #
# Payloads
# --------------------------------------------------------------------------- #
def build_text_payload(to: str, body: str) -> dict[str, Any]:
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": True, "body": body},
    }


def build_template_payload(to: str, template: str, params: list[str]) -> dict[str, Any]:
    """A template message, with its variables in the order the template expects.

    An empty component list is rejected by Meta, so a template without
    variables - its own ``hello_world``, for instance - is sent without one.
    """
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "template",
        "template": {
            "name": template,
            "language": {"code": settings.whatsapp_language},
        },
    }
    if params:
        payload["template"]["components"] = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": str(value)} for value in params],
            }
        ]
    return payload


# --------------------------------------------------------------------------- #
# Sending
# --------------------------------------------------------------------------- #
def _send(to: str | None, payload_for: Any) -> SendResult:
    """Shared path: check the number, check the credentials, then post."""
    number = to_e164(to)
    if number is None:
        return SendResult(ok=False, error=f"'{to}' is not a phone number WhatsApp can reach.")
    if not is_configured():
        return SendResult(
            ok=False,
            skipped=True,
            error="WhatsApp is not configured; no message was sent.",
        )

    payload = payload_for(number)
    try:
        response = _state.transport.post(payload)
    except WhatsAppError as error:
        logger.warning("whatsapp send failed to %s: %s", number, error)
        return SendResult(ok=False, error=str(error))
    except Exception as error:  # a network fault must not reach the caller
        logger.warning("whatsapp send failed to %s: %s", number, error)
        return SendResult(ok=False, error=f"Could not reach WhatsApp: {error}")

    messages = response.get("messages") or [{}]
    return SendResult(ok=True, message_id=messages[0].get("id", "sent"))


def send_text(to: str | None, body: str) -> SendResult:
    """Free text. Only allowed inside 24 hours of the customer writing to us."""
    return _send(to, lambda number: build_text_payload(number, body))


def send_template(to: str | None, template: str, params: list[str]) -> SendResult:
    """An approved template - what a business-initiated message has to be."""
    return _send(to, lambda number: build_template_payload(number, template, params))
