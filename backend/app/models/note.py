"""Free-form business notes about a party (kept separate from audit logs)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Note(Base, TimestampMixin):
    __tablename__ = "notes"
    __table_args__ = (Index("ix_notes_party_created_at", "party_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    party_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    note: Mapped[str] = mapped_column(Text(), nullable=False)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    party: Mapped[Party] = relationship()  # noqa: F821
    creator: Mapped[User] = relationship(lazy="joined")  # noqa: F821
