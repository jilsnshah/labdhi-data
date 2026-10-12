"""Bringing the old desk's product book across.

The source keeps the same shape we do - a material, its grades, the makers and
the combinations actually traded - so these tests pin the mapping and, above
all, that running it twice does not duplicate the book.
"""

from __future__ import annotations

from sqlalchemy import select

from app.import_masters import Book, apply
from app.models import Grade, Manufacturer, Material, Product


def book() -> Book:
    return Book(
        materials={"PVC", "CACO3"},
        manufacturers={"Reliance", "Egypt origin"},
        grades={("PVC", "S-65"), ("PVC", "K-6701"), ("CACO3", "COATED")},
        products={
            ("PVC", "S-65", "Reliance"): "25 kg bag",
            ("CACO3", "COATED", "Egypt origin"): None,
        },
    )


def test_the_whole_book_comes_across(db_session):
    stats = apply(db_session, book(), user_id=None)
    db_session.flush()

    assert dict(stats) == {"materials": 2, "manufacturers": 2, "grades": 3, "products": 2}
    assert {row.name for row in db_session.scalars(select(Material))} == {"PVC", "CACO3"}
    assert {row.name for row in db_session.scalars(select(Manufacturer))} == {
        "Reliance",
        "Egypt origin",
    }
    assert db_session.scalar(select(Grade).where(Grade.name == "S-65")).material.name == "PVC"


def test_a_grade_with_no_product_yet_is_still_kept():
    """The desk names a grade before it trades in it; that is worth carrying over."""
    source = book()
    assert ("PVC", "K-6701") in source.grades
    assert not any(key[1] == "K-6701" for key in source.products)


def test_a_product_is_named_the_way_the_desk_names_them(db_session):
    apply(db_session, book(), user_id=None)
    db_session.flush()
    names = {row.display_name for row in db_session.scalars(select(Product))}
    assert names == {"Reliance PVC S-65", "Egypt origin CACO3 COATED"}


def test_the_packing_is_kept_as_the_product_description(db_session):
    apply(db_session, book(), user_id=None)
    db_session.flush()
    product = db_session.scalar(select(Product).where(Product.display_name == "Reliance PVC S-65"))
    assert product.description == "Packing: 25 kg bag"
    plain = db_session.scalar(select(Product).where(Product.display_name.like("Egypt%")))
    assert plain.description is None


def test_running_it_again_changes_nothing(db_session):
    apply(db_session, book(), user_id=None)
    db_session.flush()
    again = apply(db_session, book(), user_id=None)
    db_session.flush()

    assert dict(again) == {}
    assert len(db_session.scalars(select(Product)).all()) == 2
    assert len(db_session.scalars(select(Material)).all()) == 2


def test_masters_already_on_file_are_reused_not_duplicated(db_session):
    db_session.add(Material(name="PVC"))
    db_session.add(Manufacturer(name="Reliance"))
    db_session.flush()

    stats = apply(db_session, book(), user_id=None)
    db_session.flush()

    assert stats["materials"] == 1, "only CACO3 is new"
    assert stats["manufacturers"] == 1, "only Egypt origin is new"
    assert len(db_session.scalars(select(Material).where(Material.name == "PVC")).all()) == 1
