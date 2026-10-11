"""Audit trail writer. Business notes stay in ``notes``; this is system history."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.pagination import PageParams, apply_sort, paginate
from app.models.audit import AuditLog
from app.models.enums import AuditAction


def record(
    session: Session,
    *,
    user_id: int | None,
    entity_type: str,
    entity_id: int,
    action: AuditAction,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
) -> AuditLog | None:
    """Write one audit row. ``UPDATE`` rows with no real change are skipped."""
    if action == AuditAction.UPDATE and not old_value and not new_value:
        return None
    entry = AuditLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
    )
    session.add(entry)
    return entry


def record_changes(
    session: Session,
    *,
    user_id: int | None,
    entity_type: str,
    entity_id: int,
    changes: dict[str, Any],
    action: AuditAction = AuditAction.UPDATE,
) -> AuditLog | None:
    if not changes:
        return None
    old = {field: pair[0] for field, pair in changes.items()}
    new = {field: pair[1] for field, pair in changes.items()}
    return record(
        session,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old,
        new_value=new,
    )


def list_logs(
    session: Session,
    params: PageParams,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    user_id: int | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
):
    stmt = select(AuditLog)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    stmt = apply_sort(
        stmt,
        sort_by,
        sort_dir,
        {"created_at": AuditLog.created_at, "id": AuditLog.id},
        "created_at",
    )
    return paginate(session, stmt, params)
