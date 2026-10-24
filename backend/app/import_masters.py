"""Copy product master data in from an older desk database.

That system holds the book the traders already keep by hand - materials, their
grades, the manufacturers and every material/grade/manufacturer combination
they actually deal in. This reads it, read-only, and writes the same masters
here so inquiries can be recorded against real products from day one.

Usage::

    python -m app.import_masters --source-url postgresql://... --dry-run
    python -m app.import_masters --source-url postgresql://...

Re-running is safe: every row is matched on its natural key (a material by
name, a grade by material and name, a product by its combination) and an
existing row is left alone.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Grade, Manufacturer, Material, Product, User
from app.models.enums import AuditAction, UserRole
from app.services import audit
from app.services.masters import build_display_name

#: The source keeps materials, grades and manufacturers in their own tables and
#: a product as the combination of them, which is exactly our shape.
SOURCE_QUERY = text(
    """
    select
        m.name  as material,
        g.name  as grade,
        f.name  as manufacturer,
        p.packing
    from products p
    join grades g        on g.id = p.grade_id
    join materials m     on m.id = g.material_id
    join manufacturers f on f.id = p.manufacturer_id
    order by m.name, g.name, f.name
    """
)
#: Materials and grades exist in the source before anything is traded in them,
#: so they are read on their own rather than only through the products.
SOURCE_GRADES = text("select m.name, g.name from grades g join materials m on m.id = g.material_id")
SOURCE_MATERIALS = text("select name from materials")
SOURCE_MANUFACTURERS = text("select name from manufacturers")


@dataclass
class Book:
    """What the source holds, as plain names."""

    materials: set[str] = field(default_factory=set)
    manufacturers: set[str] = field(default_factory=set)
    #: (material, grade)
    grades: set[tuple[str, str]] = field(default_factory=set)
    #: (material, grade, manufacturer) -> packing
    products: dict[tuple[str, str, str], str | None] = field(default_factory=dict)


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text_value = " ".join(str(value).split())
    return text_value or None


def read_source(url: str) -> Book:
    """Read the masters out of the old desk database. Nothing is written there."""
    engine = create_engine(_driver(url), pool_pre_ping=True)
    book = Book()
    try:
        with engine.connect() as connection:
            for (name,) in connection.execute(SOURCE_MATERIALS):
                if cleaned := _clean(name):
                    book.materials.add(cleaned)
            for (name,) in connection.execute(SOURCE_MANUFACTURERS):
                if cleaned := _clean(name):
                    book.manufacturers.add(cleaned)
            for material, grade in connection.execute(SOURCE_GRADES):
                material, grade = _clean(material), _clean(grade)
                if material and grade:
                    book.grades.add((material, grade))
                    book.materials.add(material)
            for material, grade, manufacturer, packing in connection.execute(SOURCE_QUERY):
                material, grade = _clean(material), _clean(grade)
                manufacturer = _clean(manufacturer)
                if not (material and grade and manufacturer):
                    continue
                book.products[(material, grade, manufacturer)] = _clean(packing)
                book.materials.add(material)
                book.manufacturers.add(manufacturer)
                book.grades.add((material, grade))
    finally:
        engine.dispose()
    return book


def _driver(url: str) -> str:
    """Hosted Postgres hands out ``postgres://``; SQLAlchemy needs the driver named."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def _import_user(session: Session) -> int | None:
    user = session.scalar(select(User).where(User.role == UserRole.ADMIN).order_by(User.id))
    return user.id if user else None


def apply(session: Session, book: Book, *, user_id: int | None) -> Counter:
    stats: Counter = Counter()

    materials: dict[str, Material] = {
        row.name: row for row in session.scalars(select(Material)).all()
    }
    for name in sorted(book.materials):
        if name in materials:
            continue
        materials[name] = Material(name=name[:80])
        session.add(materials[name])
        stats["materials"] += 1
    session.flush()

    manufacturers: dict[str, Manufacturer] = {
        row.name: row for row in session.scalars(select(Manufacturer)).all()
    }
    for name in sorted(book.manufacturers):
        if name in manufacturers:
            continue
        manufacturers[name] = Manufacturer(name=name[:120])
        session.add(manufacturers[name])
        stats["manufacturers"] += 1
    session.flush()

    grades: dict[tuple[str, str], Grade] = {
        (row.material.name, row.name): row for row in session.scalars(select(Grade)).all()
    }
    for material_name, grade_name in sorted(book.grades):
        key = (material_name, grade_name)
        if key in grades:
            continue
        grades[key] = Grade(material_id=materials[material_name].id, name=grade_name[:80])
        session.add(grades[key])
        stats["grades"] += 1
    session.flush()

    existing_products = {
        (product.material_id, product.grade_id, product.manufacturer_id)
        for product in session.scalars(select(Product)).all()
    }
    for (material_name, grade_name, manufacturer_name), packing in sorted(book.products.items()):
        material = materials[material_name]
        grade = grades[(material_name, grade_name)]
        manufacturer = manufacturers[manufacturer_name]
        if (material.id, grade.id, manufacturer.id) in existing_products:
            continue
        product = Product(
            material_id=material.id,
            grade_id=grade.id,
            manufacturer_id=manufacturer.id,
            display_name=build_display_name(manufacturer, material, grade)[:200],
            description=f"Packing: {packing}" if packing else None,
        )
        session.add(product)
        session.flush()
        existing_products.add((material.id, grade.id, manufacturer.id))
        audit.record(
            session,
            user_id=user_id,
            entity_type="product",
            entity_id=product.id,
            action=AuditAction.CREATE,
            new_value={"display_name": product.display_name, "import": "legacy-desk"},
        )
        stats["products"] += 1

    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-url",
        required=True,
        help="Read-only connection string for the old desk database",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report, write nothing")
    args = parser.parse_args(argv)

    book = read_source(args.source_url)
    print(
        f"source holds: {len(book.materials)} materials, {len(book.grades)} grades, "
        f"{len(book.manufacturers)} manufacturers, {len(book.products)} products"
    )
    if args.dry_run:
        for key in sorted(book.products)[:10]:
            print("  e.g.", " / ".join(key))
        print("dry run - nothing written")
        return 0

    with SessionLocal() as session:
        stats = apply(session, book, user_id=_import_user(session))
        session.commit()
    print(f"written: {dict(stats) or 'nothing new'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
