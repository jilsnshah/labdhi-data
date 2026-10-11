"""Small helpers shared by the service layer."""

from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.base import Base
from app.models.enums import RecordStatus

T = TypeVar("T", bound=Base)


def get_or_404(session: Session, model: type[T], entity_id: int, label: str | None = None) -> T:
    obj = session.get(model, entity_id)
    if obj is None:
        name = label or model.__name__
        raise NotFoundError(f"{name} #{entity_id} was not found.")
    return obj


def require_active(obj: Any, label: str) -> None:
    """Inactive master data must not be used for new business records."""
    status = getattr(obj, "status", None)
    if status == RecordStatus.INACTIVE:
        name = getattr(obj, "display_name", None) or getattr(obj, "name", obj.id)
        raise ValidationError(f"{label} '{name}' is inactive and cannot be used for new records.")


def ensure_unique(
    session: Session,
    model: type[T],
    *,
    message: str,
    exclude_id: int | None = None,
    case_insensitive_field: str | None = None,
    **filters: Any,
) -> None:
    stmt = select(model.id)
    for field, value in filters.items():
        column = getattr(model, field)
        if case_insensitive_field == field and isinstance(value, str):
            stmt = stmt.where(func.lower(column) == value.lower())
        else:
            stmt = stmt.where(column == value)
    if exclude_id is not None:
        stmt = stmt.where(model.id != exclude_id)
    if session.scalar(stmt.limit(1)) is not None:
        raise ConflictError(message)


def apply_patch(obj: Any, data: dict[str, Any], fields: set[str]) -> dict[str, Any]:
    """Apply the given subset of ``data`` to ``obj``; return {field: [old, new]}."""
    changes: dict[str, Any] = {}
    for field in fields:
        if field not in data:
            continue
        new = data[field]
        old = getattr(obj, field)
        if old != new:
            setattr(obj, field, new)
            changes[field] = [_jsonable(old), _jsonable(new)]
    return changes


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
