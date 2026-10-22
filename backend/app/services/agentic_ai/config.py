"""Which model, reached how. The only place either question is answered.

Two ways in, both Google's, chosen by ``ai_provider``:

* ``google_ai`` - an API key from AI Studio. One setting, no project, no
  billing account to arrange. What a developer uses.
* ``vertex`` - the same models through Google Cloud, authenticated by whatever
  credentials gcloud has already set up on the machine.

The model name lives in settings and nowhere else, so the cheapest Gemini of
the month can be swapped in without touching a prompt or a line of business
logic. The default is the cheapest one that can still hold a tool call.

Nothing here is built until it is needed, and a missing credential is reported
rather than raised at import: the desk has to keep working with no AI at all.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIUnavailable(Exception):
    """No model could be reached. Never a reason to lose a message."""


def is_configured() -> bool:
    """Whether there is a model to talk to at all."""
    if not settings.ai_enabled:
        return False
    if settings.ai_provider == "google_ai":
        return bool(settings.google_api_key)
    if settings.ai_provider == "vertex":
        return bool(settings.google_cloud_project)
    return False


def why_not() -> str:
    """One line for the log, when ``is_configured`` is False."""
    if not settings.ai_enabled:
        return "AI is switched off (AI_ENABLED)."
    if settings.ai_provider == "google_ai":
        return "No GOOGLE_API_KEY is set."
    if settings.ai_provider == "vertex":
        return "No GOOGLE_CLOUD_PROJECT is set."
    return f"Unknown AI provider '{settings.ai_provider}'."


@dataclass
class _Cache:
    """The chat model is expensive to build and safe to share."""

    model: Any | None = None
    built_for: tuple[str, str, float] | None = field(default=None)


_cache = _Cache()


def reset_model() -> None:
    """Forget the built model. For tests, and after a settings change."""
    _cache.model = None
    _cache.built_for = None


def chat_model() -> Any:
    """The configured Gemini, built once.

    Raises :class:`AIUnavailable` rather than returning a half-working object,
    so a caller that forgot to check ``is_configured`` fails loudly here
    instead of quietly producing nonsense further down.
    """
    if not is_configured():
        raise AIUnavailable(why_not())

    signature = (settings.ai_provider, settings.ai_model, settings.ai_temperature)
    if _cache.model is not None and _cache.built_for == signature:
        return _cache.model

    try:
        model = _build(signature)
    except ImportError as error:  # pragma: no cover - depends on what is installed
        raise AIUnavailable(
            f"The {settings.ai_provider} provider needs a package that is not installed: {error}"
        ) from error
    except Exception as error:  # pragma: no cover - credentials, network, quota
        raise AIUnavailable(f"Could not reach {settings.ai_model}: {error}") from error

    _cache.model = model
    _cache.built_for = signature
    logger.info("agentic ai: using %s via %s", settings.ai_model, settings.ai_provider)
    return model


def _service_account():
    """Credentials from the key file named in settings, or None.

    None means "use whatever this machine already has" - the Application
    Default Credentials of a developer who has run `gcloud auth
    application-default login`, or the attached identity of a Google-hosted
    deployment. The file is only needed where neither of those exists, which
    is most hosts that are not Google's.

    Read from settings rather than the GOOGLE_APPLICATION_CREDENTIALS
    environment variable, because this application's settings come from a .env
    file that google-auth knows nothing about: a path set there would be
    silently ignored, which is a confusing way to fail.
    """
    path = settings.google_application_credentials
    if not path:
        return None
    from google.oauth2 import service_account

    return service_account.Credentials.from_service_account_file(
        path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )


def _build(signature: tuple[str, str, float]) -> Any:
    provider, model_name, temperature = signature
    if provider == "google_ai":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=settings.google_api_key,
            timeout=settings.ai_timeout_seconds,
            max_retries=settings.ai_max_retries,
        )
    if provider == "vertex":
        # Imported here because the Vertex package is heavy and most
        # deployments never load it.
        from langchain_google_vertexai import ChatVertexAI

        return ChatVertexAI(
            model_name=model_name,
            temperature=temperature,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            max_retries=settings.ai_max_retries,
            credentials=_service_account(),
        )
    raise AIUnavailable(f"Unknown AI provider '{provider}'.")
