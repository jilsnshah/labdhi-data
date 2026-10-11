"""Engine, session factory and the request-scoped unit of work.

A `yield` dependency's exit code runs *after* FastAPI has sent the response
(FastAPI >= 0.106), so committing there is observably racy: a client could read
`201 Created`, immediately GET the new record and be told it does not exist,
because the commit had not landed yet. The commit therefore happens in
`UnitOfWorkMiddleware`, which runs before the response leaves the server.
"""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

#: Where the request's session is parked so the middleware can finish it.
STATE_KEY = "db_session"


def get_session(request: Request) -> Iterator[Session]:
    """Request-scoped session.

    Commit/rollback is owned by :class:`UnitOfWorkMiddleware`; this only has to
    make sure the connection is always returned to the pool.
    """
    session = SessionLocal()
    setattr(request.state, STATE_KEY, session)
    try:
        yield session
    finally:
        setattr(request.state, STATE_KEY, None)
        session.close()


class UnitOfWorkMiddleware(BaseHTTPMiddleware):
    """One transaction per request, committed before the response is sent.

    * 2xx/3xx - commit, so the write is visible to the client's next request.
    * 4xx/5xx - roll back, so a rejected request leaves nothing behind.
    * unhandled exception - roll back and re-raise.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        try:
            response = await call_next(request)
        except Exception:
            self._finish(request, commit=False)
            raise

        self._finish(request, commit=response.status_code < 400)
        return response

    @staticmethod
    def _finish(request: Request, *, commit: bool) -> None:
        session: Session | None = getattr(request.state, STATE_KEY, None)
        if session is None:
            return
        try:
            if commit:
                session.commit()
            else:
                session.rollback()
        except Exception:
            session.rollback()
            raise
