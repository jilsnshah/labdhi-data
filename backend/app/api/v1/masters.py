"""Material, grade, manufacturer and application endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import SessionDep, StaffUser
from app.core.pagination import Page, PageParams, page_params
from app.models.enums import RecordStatus
from app.schemas.masters import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
    GradeCreate,
    GradeOut,
    GradeUpdate,
    ManufacturerCreate,
    ManufacturerOut,
    ManufacturerUpdate,
    MaterialCreate,
    MaterialOut,
    MaterialUpdate,
)
from app.services import masters as service
from app.services.common import get_or_404

router = APIRouter()


# --------------------------------------------------------------------------- #
# Materials
# --------------------------------------------------------------------------- #
@router.get("/materials", response_model=Page[MaterialOut], tags=["materials"])
def list_materials(
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, description="Case-insensitive name search"),
    status: RecordStatus | None = None,
    sort_by: str | None = Query(None, pattern="^(name|created_at|id)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
) -> Page[MaterialOut]:
    rows, total = service.list_materials(
        session, params, q=q, status=status, sort_by=sort_by, sort_dir=sort_dir
    )
    counts = service.material_grade_counts(session, [row.id for row in rows])
    items = []
    for row in rows:
        item = MaterialOut.model_validate(row)
        item.grade_count = counts.get(row.id, 0)
        items.append(item)
    return Page.build(items, total, params)


@router.post("/materials", response_model=MaterialOut, status_code=201, tags=["materials"])
def create_material(payload: MaterialCreate, session: SessionDep, user: StaffUser) -> MaterialOut:
    return MaterialOut.model_validate(service.create_material(session, payload, user.id))


@router.get("/materials/{material_id}", response_model=MaterialOut, tags=["materials"])
def get_material(material_id: int, session: SessionDep, _: StaffUser) -> MaterialOut:
    from app.models.masters import Material

    return MaterialOut.model_validate(get_or_404(session, Material, material_id, "Material"))


@router.patch("/materials/{material_id}", response_model=MaterialOut, tags=["materials"])
def update_material(
    material_id: int, payload: MaterialUpdate, session: SessionDep, user: StaffUser
) -> MaterialOut:
    return MaterialOut.model_validate(
        service.update_material(session, material_id, payload, user.id)
    )


# --------------------------------------------------------------------------- #
# Grades
# --------------------------------------------------------------------------- #
@router.get("/grades", response_model=Page[GradeOut], tags=["grades"])
def list_grades(
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    q: str | None = None,
    material_id: int | None = Query(None, description="Only grades of this material"),
    status: RecordStatus | None = None,
    sort_by: str | None = Query(None, pattern="^(name|created_at|id)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
) -> Page[GradeOut]:
    rows, total = service.list_grades(
        session,
        params,
        q=q,
        material_id=material_id,
        status=status,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return Page.build([GradeOut.model_validate(row) for row in rows], total, params)


@router.post("/grades", response_model=GradeOut, status_code=201, tags=["grades"])
def create_grade(payload: GradeCreate, session: SessionDep, user: StaffUser) -> GradeOut:
    return GradeOut.model_validate(service.create_grade(session, payload, user.id))


@router.get("/grades/{grade_id}", response_model=GradeOut, tags=["grades"])
def get_grade(grade_id: int, session: SessionDep, _: StaffUser) -> GradeOut:
    from app.models.masters import Grade

    return GradeOut.model_validate(get_or_404(session, Grade, grade_id, "Grade"))


@router.patch("/grades/{grade_id}", response_model=GradeOut, tags=["grades"])
def update_grade(
    grade_id: int, payload: GradeUpdate, session: SessionDep, user: StaffUser
) -> GradeOut:
    return GradeOut.model_validate(service.update_grade(session, grade_id, payload, user.id))


# --------------------------------------------------------------------------- #
# Manufacturers
# --------------------------------------------------------------------------- #
@router.get("/manufacturers", response_model=Page[ManufacturerOut], tags=["manufacturers"])
def list_manufacturers(
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    q: str | None = None,
    status: RecordStatus | None = None,
    sort_by: str | None = Query(None, pattern="^(name|code|created_at|id)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
) -> Page[ManufacturerOut]:
    rows, total = service.list_manufacturers(
        session, params, q=q, status=status, sort_by=sort_by, sort_dir=sort_dir
    )
    return Page.build([ManufacturerOut.model_validate(row) for row in rows], total, params)


@router.post(
    "/manufacturers", response_model=ManufacturerOut, status_code=201, tags=["manufacturers"]
)
def create_manufacturer(
    payload: ManufacturerCreate, session: SessionDep, user: StaffUser
) -> ManufacturerOut:
    return ManufacturerOut.model_validate(service.create_manufacturer(session, payload, user.id))


@router.get(
    "/manufacturers/{manufacturer_id}", response_model=ManufacturerOut, tags=["manufacturers"]
)
def get_manufacturer(manufacturer_id: int, session: SessionDep, _: StaffUser) -> ManufacturerOut:
    from app.models.masters import Manufacturer

    return ManufacturerOut.model_validate(
        get_or_404(session, Manufacturer, manufacturer_id, "Manufacturer")
    )


@router.patch(
    "/manufacturers/{manufacturer_id}", response_model=ManufacturerOut, tags=["manufacturers"]
)
def update_manufacturer(
    manufacturer_id: int,
    payload: ManufacturerUpdate,
    session: SessionDep,
    user: StaffUser,
) -> ManufacturerOut:
    return ManufacturerOut.model_validate(
        service.update_manufacturer(session, manufacturer_id, payload, user.id)
    )


# --------------------------------------------------------------------------- #
# Applications
# --------------------------------------------------------------------------- #
@router.get("/applications", response_model=Page[ApplicationOut], tags=["applications"])
def list_applications(
    session: SessionDep,
    _: StaffUser,
    params: PageParams = Depends(page_params),
    q: str | None = None,
    status: RecordStatus | None = None,
    sort_by: str | None = Query(None, pattern="^(name|created_at|id)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
) -> Page[ApplicationOut]:
    rows, total = service.list_applications(
        session, params, q=q, status=status, sort_by=sort_by, sort_dir=sort_dir
    )
    return Page.build([ApplicationOut.model_validate(row) for row in rows], total, params)


@router.post("/applications", response_model=ApplicationOut, status_code=201, tags=["applications"])
def create_application(
    payload: ApplicationCreate, session: SessionDep, user: StaffUser
) -> ApplicationOut:
    return ApplicationOut.model_validate(service.create_application(session, payload, user.id))


@router.get("/applications/{application_id}", response_model=ApplicationOut, tags=["applications"])
def get_application(application_id: int, session: SessionDep, _: StaffUser) -> ApplicationOut:
    from app.models.masters import Application

    return ApplicationOut.model_validate(
        get_or_404(session, Application, application_id, "Application")
    )


@router.patch(
    "/applications/{application_id}", response_model=ApplicationOut, tags=["applications"]
)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    session: SessionDep,
    user: StaffUser,
) -> ApplicationOut:
    return ApplicationOut.model_validate(
        service.update_application(session, application_id, payload, user.id)
    )
