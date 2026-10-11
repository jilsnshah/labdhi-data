"""Master data rules: grade/material consistency, uniqueness, soft deactivation."""

from __future__ import annotations


def test_grade_must_belong_to_selected_material(client, auth, masters):
    response = client.post(
        "/api/v1/products",
        json={
            "material_id": masters["material_id"],
            "grade_id": masters["other_grade_id"],  # HDPE grade under PVC
            "manufacturer_id": masters["manufacturer_id"],
        },
        headers=auth,
    )
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["field"] == "grade_id"
    assert "belongs to material" in body["message"]


def test_duplicate_product_combination_is_rejected(client, auth, masters):
    response = client.post(
        "/api/v1/products",
        json={
            "material_id": masters["material_id"],
            "grade_id": masters["grade_id"],
            "manufacturer_id": masters["manufacturer_id"],
        },
        headers=auth,
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["error"]["message"]


def test_product_display_name_is_generated(client, auth, masters):
    product = client.get(f"/api/v1/products/{masters['product_id']}", headers=auth).json()
    assert product["display_name"] == "Reliance PVC K-67"
    assert [a["name"] for a in product["applications"]] == ["PVC Pipes"]


def test_duplicate_material_name_is_rejected_case_insensitively(client, auth, masters):
    response = client.post("/api/v1/materials", json={"name": "pvc"}, headers=auth)
    assert response.status_code == 409


def test_grades_are_filtered_by_material(client, auth, masters):
    rows = client.get(f"/api/v1/grades?material_id={masters['material_id']}", headers=auth).json()
    assert [row["name"] for row in rows["items"]] == ["K-67"]


def test_inactive_product_cannot_be_used_for_new_links(client, auth, masters, parties):
    client.patch(
        f"/api/v1/products/{masters['product_id']}",
        json={"status": "INACTIVE"},
        headers=auth,
    )
    response = client.post(
        f"/api/v1/parties/{parties['customer']}/products",
        json={"product_id": masters["product_id"]},
        headers=auth,
    )
    assert response.status_code == 422
    assert "inactive" in response.json()["error"]["message"]


def test_master_deactivation_keeps_history(client, auth, masters, parties):
    """Deactivating a product must not delete it or its relationships."""
    client.post(
        f"/api/v1/parties/{parties['customer']}/products",
        json={"product_id": masters["product_id"]},
        headers=auth,
    )
    client.patch(
        f"/api/v1/products/{masters['product_id']}",
        json={"status": "INACTIVE"},
        headers=auth,
    )
    product = client.get(f"/api/v1/products/{masters['product_id']}", headers=auth)
    assert product.status_code == 200
    assert product.json()["status"] == "INACTIVE"
    links = client.get(f"/api/v1/parties/{parties['customer']}/products", headers=auth).json()
    assert len(links) == 1


def test_grade_cannot_move_material_once_used_by_products(client, auth, masters):
    response = client.patch(
        f"/api/v1/grades/{masters['grade_id']}",
        json={"material_id": masters["other_material_id"]},
        headers=auth,
    )
    assert response.status_code == 409


def test_sorting_rejects_unknown_column(client, auth, masters):
    response = client.get("/api/v1/materials?sort_by=bogus", headers=auth)
    assert response.status_code == 422
