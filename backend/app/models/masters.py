"""Product master data: Material -> Grade, Manufacturer, Application, Product."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.mixins import StatusMixin

product_applications = Table(
    "product_applications",
    Base.metadata,
    Column(
        "product_id",
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "application_id",
        ForeignKey("applications.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Index("ix_product_applications_application_id", "application_id"),
)


class Material(Base, TimestampMixin, StatusMixin):
    __tablename__ = "materials"
    __table_args__ = (UniqueConstraint("name", name="uq_materials_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text())

    grades: Mapped[list[Grade]] = relationship(
        back_populates="material", cascade="all, delete-orphan", passive_deletes=True
    )


class Grade(Base, TimestampMixin, StatusMixin):
    __tablename__ = "grades"
    __table_args__ = (
        UniqueConstraint("material_id", "name", name="uq_grades_material_name"),
        Index("ix_grades_material_id_status", "material_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text())

    material: Mapped[Material] = relationship(back_populates="grades", lazy="joined")


class Manufacturer(Base, TimestampMixin, StatusMixin):
    __tablename__ = "manufacturers"
    __table_args__ = (
        UniqueConstraint("name", name="uq_manufacturers_name"),
        UniqueConstraint("code", name="uq_manufacturers_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text())


class Application(Base, TimestampMixin, StatusMixin):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("name", name="uq_applications_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text())

    products: Mapped[list[Product]] = relationship(
        secondary=product_applications, back_populates="applications"
    )


class Product(Base, TimestampMixin, StatusMixin):
    """Material + Grade + Manufacturer, with its own stable id."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint(
            "material_id", "grade_id", "manufacturer_id", name="uq_products_combination"
        ),
        Index("ix_products_material_grade", "material_id", "grade_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    grade_id: Mapped[int] = mapped_column(
        ForeignKey("grades.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    manufacturer_id: Mapped[int] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text())

    material: Mapped[Material] = relationship(lazy="joined")
    grade: Mapped[Grade] = relationship(lazy="joined", foreign_keys=[grade_id])
    manufacturer: Mapped[Manufacturer] = relationship(lazy="joined")
    applications: Mapped[list[Application]] = relationship(
        secondary=product_applications, back_populates="products", order_by="Application.name"
    )
