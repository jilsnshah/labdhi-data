"""Shared pagination / sorting primitives."""

from __future__ import annotations

from collections.abc import Sequence
from math import ceil
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.core.errors import ValidationError

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=200)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(cls, items: Sequence[T], total: int, params: PageParams) -> Page[T]:
        return cls(
            items=list(items),
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=max(1, ceil(total / params.page_size)) if total else 0,
        )


def apply_sort(
    stmt: Select,
    sort_by: str | None,
    sort_dir: str,
    allowed: dict[str, InstrumentedAttribute],
    default: str,
) -> Select:
    key = sort_by or default
    column = allowed.get(key)
    if column is None:
        raise ValidationError(
            f"Cannot sort by '{key}'. Allowed: {', '.join(sorted(allowed))}.",
            field="sort_by",
        )
    return stmt.order_by(column.desc() if sort_dir.lower() == "desc" else column.asc())


def paginate(session: Session, stmt: Select, params: PageParams) -> tuple[Sequence, int]:
    total = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = session.execute(stmt.limit(params.page_size).offset(params.offset)).scalars().all()
    return rows, total
