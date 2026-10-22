"""Meta's webhook: where WhatsApp tells us somebody has written in.

Two endpoints, both public, because Meta cannot sign in. What stands in for
authentication is a signature over the raw body, checked on every POST - this
writes to the database, so an unsigned call is refused rather than trusted.

The other rule here is that Meta must get a 200, quickly. It retries a webhook
until it does, and then disables it; so a payload we cannot read is logged and
acknowledged, never 500'd back at them. The only answer that is not 200 is the
one that says "this did not come from you".

Reading a message is therefore not done here. It is recorded, Meta is answered,
and ``enquiry_ingestion`` picks it up afterwards in a session of its own -
because deciding what a message means can take several seconds of a language
model's time, and Meta will not wait for that.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, BackgroundTasks, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse

from app.core.deps import SessionDep
from app.core.errors import PermissionError_
from app.services import enquiry_ingestion
from app.services import whatsapp_inbox as service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp webhook"])


@router.get("", response_class=PlainTextResponse, include_in_schema=False)
def verify(
    mode: str | None = Query(None, alias="hub.mode"),
    token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str | None = Query(None, alias="hub.challenge"),
) -> Response:
    """Meta's subscribe handshake, once, when the URL is saved in their dashboard.

    The challenge has to come back as bare text - a JSON string with quotes
    round it is not the same thing, and Meta rejects it.
    """
    echo = service.verification_challenge(mode, token, challenge)
    if echo is None:
        logger.warning("whatsapp webhook: verification refused")
        return PlainTextResponse("Verification failed.", status_code=403)
    return PlainTextResponse(echo)


@router.post("", include_in_schema=False)
async def receive(
    request: Request, session: SessionDep, background: BackgroundTasks
) -> dict[str, int]:
    """Record whatever came in, and tell Meta we have it.

    Async only so the raw bytes can be read for the signature - the body as
    FastAPI would parse it is not what Meta signed. The database work then goes
    to a worker thread, because everything below it is ordinary blocking
    SQLAlchemy and the event loop should not be sitting on it.
    """
    raw = await request.body()
    if not service.verify_signature(raw, request.headers.get(service.SIGNATURE_HEADER)):
        if service.signature_required():
            logger.warning("whatsapp webhook: refused a payload with no valid signature")
            raise PermissionError_("This request was not signed by WhatsApp.")
        logger.warning("whatsapp webhook: accepting an unsigned payload (no app secret set)")

    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        logger.warning("whatsapp webhook: body was not JSON, ignored")
        return {"received": 0, "stored": 0, "duplicates": 0}

    if not isinstance(payload, dict):
        logger.warning("whatsapp webhook: body was not an object, ignored")
        return {"received": 0, "stored": 0, "duplicates": 0}

    recorded = await run_in_threadpool(service.receive, session, payload)
    if recorded["stored"]:
        # After the response, in its own session: this one is committed and
        # closed by the time the task runs.
        background.add_task(enquiry_ingestion.run_pending_in_background)
    return recorded
