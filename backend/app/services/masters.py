"""Master data services: materials, grades, manufacturers, applications, products."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, ValidationError
from app.core.pagination import PageParams, apply_sort, paginate
from app.models.enums import AuditAction, PartyProductRelationship, PartyType, RecordStatus
from app.models.masters import Application, Grade, Manufacturer, Material, Product
from app.models.party import Party, PartyLocation, PartyProduct
from app.schemas.masters import (
    ApplicationCreate,
    ApplicationUpdate,
    GradeCreate,
    GradeUpdate,
    ManufacturerCreate,
    ManufacturerUpdate,
    MaterialCreate,
    MaterialUpdate,
    ProductCreate,
    ProductUpdate,
)
from app.services import audit
from app.services.common import apply_patch, ensure_unique, get_or_404, require_active


def _filter_status(stmt: Select, model, status: RecordStatus | None) -> Select:
    return stmt.where(model.status == status) if status else stmt


# --------------------------------------------------------------------------- #
# Materials
# --------------------------------------------------------------------------- #
def list_materials(
    session: Session,
    params: PageParams,
    *,
    q: str | None = None,
    status: RecordStatus | None = None,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> tuple[Sequence[Material], int]:
    stmt = select(Material)
    if q:
        stmt = stmt.where(Material.name.ilike(f"%{q}%"))
    stmt = _filter_status(stmt, Material, status)
    stmt = apply_sort(
        stmt,
        sort_by,
        sort_dir,
        {"name": Material.name, "created_at": Material.created_at, "id": Material.id},
        "name",
    )
    return paginate(session, stmt, params)


def create_material(session: Session, payload: MaterialCreate, user_id: int) -> Material:
    ensure_unique(
        session,
        Material,
        name=payload.name,
        case_insensitive_field="name",
        message=f"Material '{payload.name}' already exists.",
    )
    material = Material(name=payload.name, description=payload.description)
    session.add(material)
    session.flush()
    audit.record(
        session,
        user_id=user_id,
        entity_type="material",
        entity_id=material.id,
        action=AuditAction.CREATE,
        new_value={"name": material.name},
    )
    return material


def update_material(
    session: Session, material_id: int, payload: MaterialUpdate, user_id: int
) -> Material:
    material = get_or_404(session, Material, material_id, "Material")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        ensure_unique(
            session,
            Material,
            name=data["name"],
            exclude_id=material_id,
            case_insensitive_field="name",
            message=f"Material '{data['name']}' already exists.",
        )
    changes = apply_patch(material, data, {"name", "description", "status"})
    audit.record_changes(
        session,
        user_id=user_id,
        entity_type="material",
        entity_id=material.id,
        changes=changes,
        action=AuditAction.STATUS_CHANGE if "status" in changes else AuditAction.UPDATE,
    )
    return material


def material_grade_counts(session: Session, material_ids: Sequence[int]) -> dict[int, int]:
    if not material_ids:
        return {}
    rows = session.execute(
        select(Grade.material_id, func.count(Grade.id))
        .where(Grade.material_id.in_(material_ids))
        .group_by(Grade.material_id)
    ).all()
    return {material_id: count for material_id, count in rows}


# --------------------------------------------------------------------------- #
# Grades
# --------------------------------------------------------------------------- #
def list_grades(
    session: Session,
    params: PageParams,
    *,
    q: str | None = None,
    material_id: int | None = None,
    status: RecordStatus | None = None,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> tuple[Sequence[Grade], int]:
    stmt = select(Grade)
    if q:
        stmt = stmt.where(Grade.name.ilike(f"%{q}%"))
    if material_id is not None:
        stmt = stmt.where(Grade.material_id == material_id)
    stmt = _filter_status(stmt, Grade, status)
    stmt = apply_sort(
        stmt,
        sort_by,
        sort_dir,
        {"name": Grade.name, "created_at": Grade.created_at, "id": Grade.id},
        "name",
    )
    return paginate(session, stmt, params)


def create_grade(session: Session, payload: GradeCreate, user_id: int) -> Grade:
    material = get_or_404(session, Material, payload.material_id, "Material")
    require_active(material, "Material")
    ensure_unique(
        session,
        Grade,
        material_id=material.id,
        name=payload.name,
        case_insensitive_field="name",
        message=f"Grade '{payload.name}' already exists for material '{material.name}'.",
    )
    grade = Grade(material_id=material.id, name=payload.name, description=payload.description)
    session.add(grade)
    session.flush()
    audit.record(
        session,
        user_id=user_id,
        entity_type="grade",
        entity_id=grade.id,
        action=AuditAction.CREATE,
        new_value={"name": grade.name, "material_id": material.id},
    )
    return grade


def update_grade(session: Session, grade_id: int, payload: GradeUpdate, user_id: int) -> Grade:
    grade = get_or_404(session, Grade, grade_id, "Grade")
    data = payload.model_dump(exclude_unset=True)
    if "material_id" in data and data["material_id"] != grade.material_id:
        in_use = session.scalar(select(func.count(Product.id)).where(Product.grade_id == grade.id))
        if in_use:
            raise ConflictError(
                "This grade is already used by products; moving it to another material "
                "would make those products inconsistent."
            )
        get_or_404(session, Material, data["material_id"], "Material")
    if "name" in data or "material_id" in data:
        ensure_unique(
            session,
            Grade,
            material_id=data.get("material_id", grade.material_id),
            name=data.get("name", grade.name),
            exclude_id=grade.id,
            case_insensitive_field="name",
            message="A grade with this name already exists for the selected material.",
        )
    changes = apply_patch(grade, data, {"name", "description", "status", "material_id"})
    audit.record_changes(
        session,
        user_id=user_id,
        entity_type="grade",
        entity_id=grade.id,
        changes=changes,
        action=AuditAction.STATUS_CHANGE if "status" in changes else AuditAction.UPDATE,
    )
    return grade


# --------------------------------------------------------------------------- #
# Manufacturers
# --------------------------------------------------------------------------- #
def list_manufacturers(
    session: Session,
    params: PageParams,
    *,
    q: str | None = None,
    status: RecordStatus | None = None,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> tuple[Sequence[Manufacturer], int]:
    stmt = select(Manufacturer)
    if q:
        stmt = stmt.where(or_(Manufacturer.name.ilike(f"%{q}%"), Manufacturer.code.ilike(f"%{q}%")))
    stmt = _filter_status(stmt, Manufacturer, status)
    stmt = apply_sort(
        stmt,
        sort_by,
        sort_dir,
        {
            "name": Manufacturer.name,
            "code": Manufacturer.code,
            "created_at": Manufacturer.created_at,
            "id": Manufacturer.id,
        },
        "name",
    )
    return paginate(session, stmt, params)


def create_manufacturer(
    session: Session, payload: ManufacturerCreate, user_id: int
) -> Manufacturer:
    ensure_unique(
        session,
        Manufacturer,
        name=payload.name,
        case_insensitive_field="name",
        message=f"Manufacturer '{payload.name}' already exists.",
    )
    if payload.code:
        ensure_unique(
            session,
            Manufacturer,
            code=payload.code,
            case_insensitive_field="code",
            message=f"Manufacturer code '{payload.code}' is already used.",
        )
    manufacturer = Manufacturer(
        name=payload.name, code=payload.code, description=payload.description
    )
    session.add(manufacturer)
    session.flush()
    audit.record(
        session,
        user_id=user_id,
        entity_type="manufacturer",
        entity_id=manufacturer.id,
        action=AuditAction.CREATE,
        new_value={"name": manufacturer.name},
    )
    return manufacturer


def update_manufacturer(
    session: Session, manufacturer_id: int, payload: ManufacturerUpdate, user_id: int
) -> Manufacturer:
    manufacturer = get_or_404(session, Manufacturer, manufacturer_id, "Manufacturer")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        ensure_unique(
            session,
            Manufacturer,
            name=data["name"],
            exclude_id=manufacturer_id,
            case_insensitive_field="name",
            message=f"Manufacturer '{data['name']}' already exists.",
        )
    if data.get("code"):
        ensure_unique(
            session,
            Manufacturer,
            code=data["code"],
            exclude_id=manufacturer_id,
            case_insensitive_field="code",
            message=f"Manufacturer code '{data['code']}' is already used.",
        )
    changes = apply_patch(manufacturer, data, {"name", "code", "description", "status"})
    audit.record_changes(
        session,
        user_id=user_id,
        entity_type="manufacturer",
        entity_id=manufacturer.id,
        changes=changes,
        action=AuditAction.STATUS_CHANGE if "status" in changes else AuditAction.UPDATE,
    )
    return manufacturer


# --------------------------------------------------------------------------- #
# Applications
# --------------------------------------------------------------------------- #
def list_applications(
    session: Session,
    params: PageParams,
    *,
    q: str | None = None,
    status: RecordStatus | None = None,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> tuple[Sequence[Application], int]:
    stmt = select(Application)
    if q:
        stmt = stmt.where(Application.name.ilike(f"%{q}%"))
    stmt = _filter_status(stmt, Application, status)
    stmt = apply_sort(
        stmt,
        sort_by,
        sort_dir,
        {"name": Application.name, "created_at": Application.created_at, "id": Application.id},
        "name",
    )
    return paginate(session, stmt, params)


def create_application(session: Session, payload: ApplicationCreate, user_id: int) -> Application:
    ensure_unique(
        session,
        Application,
        name=payload.name,
        case_insensitive_field="name",
        message=f"Application '{payload.name}' already exists.",
    )
    application = Application(name=payload.name, description=payload.description)
    session.add(application)
    session.flush()
    audit.record(
        session,
        user_id=user_id,
        entity_type="application",
        entity_id=application.id,
        action=AuditAction.CREATE,
        new_value={"name": application.name},
    )
    return application


def update_application(
    session: Session, application_id: int, payload: ApplicationUpdate, user_id: int
) -> Application:
    application = get_or_404(session, Application, application_id, "Application")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        ensure_unique(
            session,
            Application,
            name=data["name"],
            exclude_id=application_id,
            case_insensitive_field="name",
            message=f"Application '{data['name']}' already exists.",
        )
    changes = apply_patch(application, data, {"name", "description", "status"})
    audit.record_changes(
        session,
        user_id=user_id,
        entity_type="application",
        entity_id=application.id,
        changes=changes,
        action=AuditAction.STATUS_CHANGE if "status" in changes else AuditAction.UPDATE,
    )
    return application


# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #
def _validate_combination(
    session: Session, material_id: int, grade_id: int, manufacturer_id: int, *, new: bool
) -> tuple[Material, Grade, Manufacturer]:
    material = get_or_404(session, Material, material_id, "Material")
    grade = get_or_404(session, Grade, grade_id, "Grade")
    manufacturer = get_or_404(session, Manufacturer, manufacturer_id, "Manufacturer")
    if grade.material_id != material.id:
        raise ValidationError(
            f"Grade '{grade.name}' belongs to material '{grade.material.name}', "
            f"not '{material.name}'.",
            field="grade_id",
        )
    if new:
        require_active(material, "Material")
        require_active(grade, "Grade")
        require_active(manufacturer, "Manufacturer")
    return material, grade, manufacturer


def build_display_name(manufacturer: Manufacturer, material: Material, grade: Grade) -> str:
    return f"{manufacturer.name} {material.name} {grade.name}"


def _resolve_applications(session: Session, application_ids: list[int]) -> list[Application]:
    unique_ids = list(dict.fromkeys(application_ids))
    if not unique_ids:
        return []
    found = (
        session.execute(select(Application).where(Application.id.in_(unique_ids))).scalars().all()
    )
    missing = set(unique_ids) - {a.id for a in found}
    if missing:
        raise ValidationError(
            f"Unknown application id(s): {', '.join(str(i) for i in sorted(missing))}.",
            field="application_ids",
        )
    for application in found:
        require_active(application, "Application")
    return list(found)


def list_products(
    session: Session,
    params: PageParams,
    *,
    q: str | None = None,
    material_id: int | None = None,
    grade_id: int | None = None,
    manufacturer_id: int | None = None,
    application_id: int | None = None,
    status: RecordStatus | None = None,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> tuple[Sequence[Product], int]:
    stmt = select(Product).options(selectinload(Product.applications))
    if q:
        like = f"%{q}%"
        stmt = (
            stmt.join(Product.material)
            .join(Grade, Product.grade_id == Grade.id)
            .join(Product.manufacturer)
            .where(
                or_(
                    Product.display_name.ilike(like),
                    Material.name.ilike(like),
                    Grade.name.ilike(like),
                    Manufacturer.name.ilike(like),
                )
            )
        )
    if material_id is not None:
        stmt = stmt.where(Product.material_id == material_id)
    if grade_id is not None:
        stmt = stmt.where(Product.grade_id == grade_id)
    if manufacturer_id is not None:
        stmt = stmt.where(Product.manufacturer_id == manufacturer_id)
    if application_id is not None:
        stmt = stmt.where(Product.applications.any(Application.id == application_id))
    stmt = _filter_status(stmt, Product, status)
    stmt = apply_sort(
        stmt,
        sort_by,
        sort_dir,
        {
            "display_name": Product.display_name,
            "created_at": Product.created_at,
            "id": Product.id,
        },
        "display_name",
    )
    return paginate(session, stmt, params)


def get_product(session: Session, product_id: int) -> Product:
    return get_or_404(session, Product, product_id, "Product")


def create_product(session: Session, payload: ProductCreate, user_id: int) -> Product:
    material, grade, manufacturer = _validate_combination(
        session, payload.material_id, payload.grade_id, payload.manufacturer_id, new=True
    )
    ensure_unique(
        session,
        Product,
        material_id=material.id,
        grade_id=grade.id,
        manufacturer_id=manufacturer.id,
        message=(f"Product '{build_display_name(manufacturer, material, grade)}' already exists."),
    )
    product = Product(
        material_id=material.id,
        grade_id=grade.id,
        manufacturer_id=manufacturer.id,
        display_name=payload.display_name or build_display_name(manufacturer, material, grade),
        description=payload.description,
    )
    product.applications = _resolve_applications(session, payload.application_ids)
    session.add(product)
    session.flush()
    audit.record(
        session,
        user_id=user_id,
        entity_type="product",
        entity_id=product.id,
        action=AuditAction.CREATE,
        new_value={
            "display_name": product.display_name,
            "material_id": material.id,
            "grade_id": grade.id,
            "manufacturer_id": manufacturer.id,
            "application_ids": [a.id for a in product.applications],
        },
    )
    return product


def update_product(
    session: Session, product_id: int, payload: ProductUpdate, user_id: int
) -> Product:
    product = get_or_404(session, Product, product_id, "Product")
    data = payload.model_dump(exclude_unset=True)

    target_material = data.get("material_id", product.material_id)
    target_grade = data.get("grade_id", product.grade_id)
    target_manufacturer = data.get("manufacturer_id", product.manufacturer_id)
    combination_changed = (
        target_material,
        target_grade,
        target_manufacturer,
    ) != (product.material_id, product.grade_id, product.manufacturer_id)

    if combination_changed:
        material, grade, manufacturer = _validate_combination(
            session, target_material, target_grade, target_manufacturer, new=False
        )
        ensure_unique(
            session,
            Product,
            material_id=material.id,
            grade_id=grade.id,
            manufacturer_id=manufacturer.id,
            exclude_id=product.id,
            message="Another product already uses this material/grade/manufacturer combination.",
        )

    changes = apply_patch(
        product,
        data,
        {
            "material_id",
            "grade_id",
            "manufacturer_id",
            "display_name",
            "description",
            "status",
        },
    )

    if data.get("application_ids") is not None:
        applications = _resolve_applications(session, data["application_ids"])
        before = sorted(a.id for a in product.applications)
        after = sorted(a.id for a in applications)
        if before != after:
            product.applications = applications
            changes["application_ids"] = [str(before), str(after)]

    session.flush()
    audit.record_changes(
        session,
        user_id=user_id,
        entity_type="product",
        entity_id=product.id,
        changes=changes,
        action=AuditAction.STATUS_CHANGE if "status" in changes else AuditAction.UPDATE,
    )
    return product


def parties_for_product(
    session: Session,
    product_id: int,
    *,
    party_type: PartyType,
    relationship_types: Sequence[PartyProductRelationship] | None = None,
    only_active: bool = True,
) -> list[dict]:
    """'Which suppliers can provide product X / which customers want it?'"""
    get_or_404(session, Product, product_id, "Product")
    primary_city = (
        select(PartyLocation.party_id, func.min(PartyLocation.location_id).label("location_id"))
        .group_by(PartyLocation.party_id)
        .subquery()
    )
    stmt = (
        select(Party, PartyProduct, primary_city.c.location_id)
        .join(PartyProduct, PartyProduct.party_id == Party.id)
        .outerjoin(primary_city, primary_city.c.party_id == Party.id)
        .where(PartyProduct.product_id == product_id, Party.party_type == party_type)
        .order_by(Party.name)
    )
    if relationship_types:
        stmt = stmt.where(PartyProduct.relationship_type.in_(list(relationship_types)))
    if only_active:
        stmt = stmt.where(Party.status == RecordStatus.ACTIVE, PartyProduct.active.is_(True))

    results: list[dict] = []
    for party, link, _location_id in session.execute(stmt).all():
        city = None
        if party.locations:
            city = party.locations[0].location.city
        results.append(
            {
                "party_id": party.id,
                "party_name": party.name,
                "party_type": party.party_type.value,
                "relationship_type": link.relationship_type.value,
                "phone": party.phone,
                "city": city,
                "notes": link.notes,
            }
        )
    return results
