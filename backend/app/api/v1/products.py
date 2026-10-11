"""Product endpoints, including 'who supplies / who wants this product'."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import SessionDep, StaffUser
from app.core.pagination import Page, PageParams, page_params
from app.models.enums import PartyProductRelationship, PartyType, RecordStatus
from app.schemas.masters import (
    ProductCreate,
    ProductOut,
    ProductPartyLink,
    ProductUpdate,
)
from app.services import masters as service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=Page[ProductOut])
def list_products(
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, description="Searches product, material, grade, manufacturer"),
    material_id: int | None = None,
    grade_id: int | None = None,
    manufacturer_id: int | None = None,
    application_id: int | None = None,
    status: RecordStatus | None = None,
    sort_by: str | None = Query(None, pattern="^(display_name|created_at|id)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
) -> Page[ProductOut]:
    rows, total = service.list_products(
        session,
        params,
        q=q,
        material_id=material_id,
        grade_id=grade_id,
        manufacturer_id=manufacturer_id,
        application_id=application_id,
        status=status,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return Page.build([ProductOut.model_validate(row) for row in rows], total, params)


@router.post("", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreate, session: SessionDep, user: StaffUser) -> ProductOut:
    return ProductOut.model_validate(service.create_product(session, payload, user.id))


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, session: SessionDep, _: StaffUser) -> ProductOut:
    return ProductOut.model_validate(service.get_product(session, product_id))


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int, payload: ProductUpdate, session: SessionDep, user: StaffUser
) -> ProductOut:
    return ProductOut.model_validate(service.update_product(session, product_id, payload, user.id))


@router.get("/{product_id}/suppliers", response_model=list[ProductPartyLink])
def product_suppliers(
    product_id: int,
    session: SessionDep,
    _: StaffUser,
    only_active: bool = True,
) -> list[ProductPartyLink]:
    """Which suppliers can provide this product?"""
    rows = service.parties_for_product(
        session,
        product_id,
        party_type=PartyType.SUPPLIER,
        relationship_types=[PartyProductRelationship.SUPPLIES],
        only_active=only_active,
    )
    return [ProductPartyLink(**row) for row in rows]


@router.get("/{product_id}/customers", response_model=list[ProductPartyLink])
def product_customers(
    product_id: int,
    session: SessionDep,
    _: StaffUser,
    only_active: bool = True,
) -> list[ProductPartyLink]:
    """Which customers buy or are interested in this product?"""
    rows = service.parties_for_product(
        session,
        product_id,
        party_type=PartyType.CUSTOMER,
        relationship_types=[
            PartyProductRelationship.PURCHASES,
            PartyProductRelationship.INTERESTED_IN,
        ],
        only_active=only_active,
    )
    return [ProductPartyLink(**row) for row in rows]
