"""Test fixtures: an isolated PostgreSQL test database per session, rolled back per test."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models import Party, User
from app.models.enums import PartyType, UserRole


def _ensure_database(url: str) -> None:
    target = make_url(url)
    admin_url = target.set(database="postgres")
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": target.database},
        ).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{target.database}"'))
    engine.dispose()


@pytest.fixture(scope="session")
def engine():
    _ensure_database(settings.test_database_url)
    engine = create_engine(settings.test_database_url, future=True)
    with engine.begin() as connection:
        # Start from an empty schema rather than metadata.drop_all(): tables or
        # foreign keys the models no longer describe would otherwise survive and
        # block the drop.
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        # Migration 0003 installs this; the test schema is built from the models.
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine) -> Iterator[Session]:
    """Each test runs inside a transaction that is rolled back afterwards."""
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = factory()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def admin(db_session: Session) -> User:
    user = User(
        name="Test Admin",
        email="admin@test.in",
        password_hash=hash_password("admin123"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def plain_user(db_session: Session) -> User:
    user = User(
        name="Desk User",
        email="desk@test.in",
        password_hash=hash_password("desk123"),
        role=UserRole.USER,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def salesperson(db_session: Session) -> User:
    user = User(
        name="Rahul Field",
        email="rahul@test.in",
        password_hash=hash_password("rahul123"),
        role=UserRole.SALESPERSON,
        phone="+91 90000 00001",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def other_salesperson(db_session: Session) -> User:
    user = User(
        name="Amit Field",
        email="amit@test.in",
        password_hash=hash_password("amit123"),
        role=UserRole.SALESPERSON,
        phone="+91 90000 00002",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture(autouse=True)
def _fresh_portal_throttle():
    """The portal's rate limiter is process-wide; one test must not spend
    another's allowance."""
    from app.api.v1.portal import reset_throttle

    reset_throttle()
    yield
    reset_throttle()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def override() -> Iterator[Session]:
        """One SAVEPOINT per request: mirrors commit/rollback without ending the
        outer test transaction (which the ``db_session`` fixture rolls back)."""
        savepoint = db_session.begin_nested()
        try:
            yield db_session
            db_session.flush()
            savepoint.commit()
        except Exception:
            if savepoint.is_active:
                savepoint.rollback()
            raise

    app.dependency_overrides[get_session] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client: TestClient, admin: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"email": admin.email, "password": "admin123"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']['access_token']}"}


@pytest.fixture
def desk_auth(client: TestClient, plain_user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"email": plain_user.email, "password": "desk123"}
    )
    return {"Authorization": f"Bearer {response.json()['token']['access_token']}"}


@pytest.fixture
def sales_auth(client: TestClient, salesperson: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"email": salesperson.email, "password": "rahul123"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']['access_token']}"}


@pytest.fixture
def other_sales_auth(client: TestClient, other_salesperson: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"email": other_salesperson.email, "password": "amit123"}
    )
    return {"Authorization": f"Bearer {response.json()['token']['access_token']}"}


@pytest.fixture
def masters(client: TestClient, auth: dict[str, str]) -> dict[str, int]:
    """A minimal but valid master-data set: PVC / K-67 / Reliance / product."""
    material = client.post("/api/v1/materials", json={"name": "PVC"}, headers=auth).json()
    other_material = client.post("/api/v1/materials", json={"name": "HDPE"}, headers=auth).json()
    grade = client.post(
        "/api/v1/grades", json={"material_id": material["id"], "name": "K-67"}, headers=auth
    ).json()
    other_grade = client.post(
        "/api/v1/grades",
        json={"material_id": other_material["id"], "name": "MFI 0.3"},
        headers=auth,
    ).json()
    manufacturer = client.post(
        "/api/v1/manufacturers", json={"name": "Reliance", "code": "RIL"}, headers=auth
    ).json()
    application = client.post(
        "/api/v1/applications", json={"name": "PVC Pipes"}, headers=auth
    ).json()
    product = client.post(
        "/api/v1/products",
        json={
            "material_id": material["id"],
            "grade_id": grade["id"],
            "manufacturer_id": manufacturer["id"],
            "application_ids": [application["id"]],
        },
        headers=auth,
    ).json()
    return {
        "material_id": material["id"],
        "other_material_id": other_material["id"],
        "grade_id": grade["id"],
        "other_grade_id": other_grade["id"],
        "manufacturer_id": manufacturer["id"],
        "application_id": application["id"],
        "product_id": product["id"],
    }


@pytest.fixture
def parties(db_session: Session) -> dict[str, int]:
    rows = {
        "customer": Party(name="ABC Pipes", party_type=PartyType.CUSTOMER),
        "other_customer": Party(name="XYZ Polymers", party_type=PartyType.CUSTOMER),
        "supplier": Party(name="Mahavir Polymers", party_type=PartyType.SUPPLIER),
        "transporter": Party(name="Jay Transport", party_type=PartyType.TRANSPORTER),
    }
    db_session.add_all(rows.values())
    db_session.flush()
    return {key: party.id for key, party in rows.items()}


@pytest.fixture
def locations(client: TestClient, auth: dict[str, str]) -> dict[str, int]:
    pickup = client.post(
        "/api/v1/locations",
        json={"label": "Ahmedabad Warehouse", "city": "Ahmedabad", "state": "Gujarat"},
        headers=auth,
    ).json()
    delivery = client.post(
        "/api/v1/locations",
        json={"label": "Rajkot Factory", "city": "Rajkot", "state": "Gujarat"},
        headers=auth,
    ).json()
    return {"pickup_id": pickup["id"], "delivery_id": delivery["id"]}
