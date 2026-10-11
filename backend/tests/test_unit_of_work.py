"""The request transaction must be committed before the response is sent.

A `yield` dependency's exit code runs after FastAPI has sent the response, so
committing there let a client read `201 Created` and then be told the new record
did not exist. `UnitOfWorkMiddleware` closes that window.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.db.session import STATE_KEY, UnitOfWorkMiddleware


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def _request(session: FakeSession | None) -> SimpleNamespace:
    return SimpleNamespace(state=SimpleNamespace(**{STATE_KEY: session}))


def test_successful_response_commits():
    session = FakeSession()
    UnitOfWorkMiddleware._finish(_request(session), commit=True)
    assert session.committed is True
    assert session.rolled_back is False


def test_error_response_rolls_back():
    session = FakeSession()
    UnitOfWorkMiddleware._finish(_request(session), commit=False)
    assert session.rolled_back is True
    assert session.committed is False


def test_request_without_a_session_is_a_no_op():
    UnitOfWorkMiddleware._finish(_request(None), commit=True)  # must not raise


def test_commit_failure_rolls_back_and_propagates():
    class Failing(FakeSession):
        def commit(self) -> None:
            raise RuntimeError("constraint violated at commit")

    session = Failing()
    with pytest.raises(RuntimeError):
        UnitOfWorkMiddleware._finish(_request(session), commit=True)
    assert session.rolled_back is True


def test_middleware_is_installed_on_the_app():
    from app.main import app

    assert any(middleware.cls is UnitOfWorkMiddleware for middleware in app.user_middleware), (
        "the unit-of-work middleware must be registered"
    )
