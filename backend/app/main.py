"""FastAPI application factory, error handling and router wiring."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import AppError
from app.db.session import UnitOfWorkMiddleware

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger("trader_crm")

DESCRIPTION = """
Trader CRM + Inquiry Management System.

* **Master data** - materials, grades, manufacturers, applications, products, locations
* **Parties** - customers, suppliers and transporters with locations and product links
* **Inquiries** - customer requirements, supplier sourcing, transport, responses and closure
* **Activities** - customer calls, WhatsApp, SMS and visits with follow-up chains
* **360 views** - `/parties/{id}/overview` returns one party's full business picture

Authenticate with `POST /api/v1/auth/login` and send `Authorization: Bearer <token>`.
"""


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=DESCRIPTION,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Outermost of the two: commits the request's transaction before the response
    # is sent, so a client never reads its own write as missing.
    app.add_middleware(UnitOfWorkMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.to_payload()})

    @app.exception_handler(RequestValidationError)
    def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {
                "field": ".".join(str(part) for part in error["loc"][1:]) or "body",
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
        first = fields[0] if fields else {"field": "body", "message": "Invalid request"}
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": f"{first['field']}: {first['message']}",
                    "field": first["field"],
                    "details": {"fields": fields},
                }
            },
        )

    @app.exception_handler(IntegrityError)
    def handle_integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Database constraint violation: %s", exc.orig)
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "conflict",
                    "message": (
                        "This change conflicts with a database constraint "
                        "(duplicate or invalid reference)."
                    ),
                }
            },
        )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
