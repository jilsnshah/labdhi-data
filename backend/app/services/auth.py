"""Authentication and user management."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AuthError, ConflictError
from app.core.pagination import PageParams, apply_sort, paginate
from app.core.security import hash_password, verify_password
from app.models.enums import AuditAction, RecordStatus, UserRole
from app.models.user import User
from app.schemas.auth import UserCreate, UserUpdate
from app.services import audit
from app.services.common import apply_patch, get_or_404


def authenticate(session: Session, email: str, password: str) -> User:
    user = session.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("Incorrect email or password.")
    if user.status != RecordStatus.ACTIVE:
        raise AuthError("This account is inactive.")
    return user


def create_user(session: Session, payload: UserCreate, actor_id: int | None = None) -> User:
    existing = session.scalar(
        select(User.id).where(func.lower(User.email) == payload.email.lower())
    )
    if existing is not None:
        raise ConflictError(f"A user with email '{payload.email}' already exists.")
    user = User(
        name=payload.name,
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        phone=payload.phone,
    )
    session.add(user)
    session.flush()
    audit.record(
        session,
        user_id=actor_id,
        entity_type="user",
        entity_id=user.id,
        action=AuditAction.CREATE,
        new_value={"email": user.email, "role": user.role.value},
    )
    return user


def update_user(session: Session, user_id: int, payload: UserUpdate, actor_id: int) -> User:
    user = get_or_404(session, User, user_id, "User")
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    changes = apply_patch(user, data, {"name", "role", "status", "phone"})
    if password:
        user.password_hash = hash_password(password)
        changes["password_hash"] = ["***", "***"]
    audit.record_changes(
        session,
        user_id=actor_id,
        entity_type="user",
        entity_id=user.id,
        changes=changes,
    )
    return user


def list_users(
    session: Session,
    params: PageParams,
    *,
    q: str | None = None,
    status: RecordStatus | None = None,
    role: UserRole | None = None,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> tuple[Sequence[User], int]:
    stmt = select(User)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.name.ilike(like), User.email.ilike(like)))
    if status:
        stmt = stmt.where(User.status == status)
    if role:
        stmt = stmt.where(User.role == role)
    stmt = apply_sort(
        stmt,
        sort_by,
        sort_dir,
        {"name": User.name, "email": User.email, "created_at": User.created_at, "id": User.id},
        "name",
    )
    return paginate(session, stmt, params)
