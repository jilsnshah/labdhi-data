"""Staying signed in.

A trading desk is opened every morning and a field phone lives in a pocket all
week. Being asked for a password each day is the kind of friction that stops
people recording anything at all, so a session lasts a month and renews itself
whenever the app is used - while still proving who the caller is every time.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings


def test_a_session_lasts_long_enough_to_stop_asking(client, admin):
    """Twelve hours meant signing in again every single day."""
    token = client.post(
        "/api/v1/auth/login", json={"email": admin.email, "password": "admin123"}
    ).json()["token"]
    assert token["expires_in_minutes"] >= 60 * 24 * 7


def test_a_valid_token_renews_itself(client, auth, admin):
    """The clients call this on launch, so an app in daily use never lapses."""
    response = client.post("/api/v1/auth/refresh", headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == admin.id

    # The new token works on its own.
    fresh = {"Authorization": f"Bearer {body['token']['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=fresh).json()["id"] == admin.id


def test_renewing_proves_nothing_new(client):
    """An expired, forged or absent token cannot mint a working one."""
    assert client.post("/api/v1/auth/refresh").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/refresh", headers={"Authorization": "Bearer not.a.token"}
        ).status_code
        == 401
    )


def test_an_expired_token_cannot_renew(client, admin):
    stale = jwt.encode(
        {
            "sub": str(admin.id),
            "iat": datetime.now(UTC) - timedelta(days=2),
            "exp": datetime.now(UTC) - timedelta(days=1),
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {stale}"})
    assert response.status_code == 401
    assert "expired" in response.json()["error"]["message"].lower()
