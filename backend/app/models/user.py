"""Application users. Every created_by/closed_by field points here."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import UserRole, user_role_enum
from app.models.mixins import StatusMixin


class User(Base, TimestampMixin, StatusMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[UserRole] = mapped_column(
        user_role_enum,
        default=UserRole.USER,
        server_default=UserRole.USER.value,
        nullable=False,
        index=True,
    )

    @property
    def is_salesperson(self) -> bool:
        return self.role == UserRole.SALESPERSON

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.id} {self.email}>"
