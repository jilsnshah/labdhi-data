"""FastAPI dependencies: database session, authenticated user, role gates.

Authorization is enforced here (and in the salesperson service layer), never by
hiding things in the frontend. Three gates exist:

* ``CurrentUser``      - any authenticated, active account.
* ``StaffUser``        - ADMIN or USER: the back-office CRM. Salespeople are rejected.
* ``AdminUser``        - ADMIN only: user administration, audit logs, assignment.
* ``SalespersonUser``  - SALESPERSON only: the field app.
"""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthError, PermissionError_
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.enums import STAFF_ROLES, RecordStatus, UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthError("Authentication required.")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Session expired, please sign in again.") from exc
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid authentication token.") from exc

    user_id = payload.get("sub")
    user = session.get(User, int(user_id)) if user_id else None
    if user is None:
        raise AuthError("User account no longer exists.")
    if user.status != RecordStatus.ACTIVE:
        raise AuthError("This account is inactive.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_staff(user: CurrentUser) -> User:
    """Back-office access. A salesperson may never read general CRM data."""
    if user.role not in STAFF_ROLES:
        raise PermissionError_(
            "Field accounts cannot access CRM data. Use the salesperson app "
            "(/api/v1/salesperson/...) which only exposes your assigned activities."
        )
    return user


def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise PermissionError_("This action requires an administrator account.")
    return user


def require_salesperson(user: CurrentUser) -> User:
    if user.role != UserRole.SALESPERSON:
        raise PermissionError_("This endpoint is only for salesperson accounts.")
    return user


StaffUser = Annotated[User, Depends(require_staff)]
AdminUser = Annotated[User, Depends(require_admin)]
SalespersonUser = Annotated[User, Depends(require_salesperson)]
