"""Auth + user schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import RecordStatus, UserRole
from app.schemas.common import ORMBase, TimestampsOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.USER
    phone: str | None = Field(default=None, max_length=30)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: UserRole | None = None
    status: RecordStatus | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    phone: str | None = Field(default=None, max_length=30)


class UserOut(TimestampsOut, ORMBase):
    id: int
    name: str
    email: EmailStr
    phone: str | None = None
    role: UserRole
    status: RecordStatus


class LoginResponse(BaseModel):
    token: Token
    user: UserOut
