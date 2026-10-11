"""Mixins that depend on business enums."""

from sqlalchemy.orm import Mapped, mapped_column

from app.models.enums import RecordStatus, status_enum


class StatusMixin:
    """Soft deactivation for master data (never hard-delete referenced rows)."""

    status: Mapped[RecordStatus] = mapped_column(
        status_enum,
        default=RecordStatus.ACTIVE,
        server_default=RecordStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )

    @property
    def is_active(self) -> bool:
        return self.status == RecordStatus.ACTIVE
