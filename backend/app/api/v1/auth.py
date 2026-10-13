"""Authentication and user administration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.config import settings
from app.core.deps import AdminUser, CurrentUser, SessionDep, StaffUser
from app.core.pagination import Page, PageParams, page_params
from app.core.security import create_access_token
from app.models.enums import RecordStatus, UserRole
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    Token,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services import auth as auth_service

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: SessionDep) -> LoginResponse:
    user = auth_service.authenticate(session, str(payload.email), payload.password)
    token = create_access_token(user.id, {"role": user.role.value, "name": user.name})
    return LoginResponse(
        token=Token(
            access_token=token,
            expires_in_minutes=settings.access_token_expire_minutes,
        ),
        user=UserOut.model_validate(user),
    )


@router.post("/auth/refresh", response_model=LoginResponse)
def refresh(user: CurrentUser) -> LoginResponse:
    """Hand back a fresh token to a caller who still has a valid one.

    The clients call this when they start, so anyone who keeps using the app
    stays signed in indefinitely while an abandoned session still lapses. It
    proves nothing new - an expired or forged token cannot renew itself.
    """
    token = create_access_token(user.id, {"role": user.role.value, "name": user.name})
    return LoginResponse(
        token=Token(
            access_token=token,
            expires_in_minutes=settings.access_token_expire_minutes,
        ),
        user=UserOut.model_validate(user),
    )


@router.get("/auth/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/users", response_model=Page[UserOut], tags=["users"])
def list_users(
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, description="Search name or email"),
    status: RecordStatus | None = None,
    role: UserRole | None = Query(None, description="e.g. SALESPERSON for assignment pickers"),
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> Page[UserOut]:
    rows, total = auth_service.list_users(
        session, params, q=q, status=status, role=role, sort_by=sort_by, sort_dir=sort_dir
    )
    return Page.build([UserOut.model_validate(row) for row in rows], total, params)


@router.post("/users", response_model=UserOut, status_code=201, tags=["users"])
def create_user(payload: UserCreate, session: SessionDep, admin: AdminUser) -> UserOut:
    user = auth_service.create_user(session, payload, actor_id=admin.id)
    return UserOut.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserOut, tags=["users"])
def update_user(
    user_id: int, payload: UserUpdate, session: SessionDep, admin: AdminUser
) -> UserOut:
    user = auth_service.update_user(session, user_id, payload, actor_id=admin.id)
    return UserOut.model_validate(user)
