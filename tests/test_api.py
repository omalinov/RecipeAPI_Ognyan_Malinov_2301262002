import json

import pytest
from sqlalchemy.exc import IntegrityError


def request(client, method, path, status, **kwargs):
    response = client.request(method, path, **kwargs)
    assert response.status_code == status, response.text
    if status == 204:
        assert response.content == b""
        return None
    return response.json()


def create(client, resource, **payload):
    return request(client, "POST", f"/{resource}", 201, json=payload)


def recipe_data(author_id, **changes):
    return {
        "title": "Tomato Salad",
        "instructions": "Slice and toss.",
        "preparation_time": 10,
        "servings": 4,
        "author_id": author_id,
        **changes,
    }


@pytest.fixture
def catalogue(client):
    author = create(client, "authors", name="Maria", email="maria@example.com")
    category = create(client, "categories", name="Salads")
    ingredient = create(client, "ingredients", name="Tomato")
    data = recipe_data(author["id"], category_id=category["id"])
    recipe = create(client, "recipes", **data)
    return author, category, ingredient, recipe


@pytest.mark.parametrize("resource,original,replacement", [
    ("authors", {"name": " Maria ", "email": " maria@example.com "},
     {"name": "Mira", "email": "mira@example.com"}),
    ("categories", {"name": " Salads "}, {"name": "Desserts"}),
    ("ingredients", {"name": " Tomato "}, {"name": "Pepper"}),
    ("recipes", {"title": " Salad "}, {"title": "Pepper Salad", "servings": 2}),
])
def test_crud(client, resource, original, replacement):
    if resource == "recipes":
        author = create(client, "authors", name="Maria", email="maria@example.com")
        original = recipe_data(author["id"], **original)
        replacement = recipe_data(author["id"], **replacement)
    collection = f"/{resource}"
    assert request(client, "GET", collection, 200) == []
    item = create(client, resource, **original)
    for field, value in original.items():
        assert item[field] == (value.strip() if isinstance(value, str) else value)
    path = f"{collection}/{item['id']}"
    assert request(client, "GET", collection, 200) == [item]
    assert request(client, "GET", path, 200) == item
    updated = request(client, "PUT", path, 200, json=replacement)
    assert updated["id"] == item["id"]
    assert all(updated[key] == value for key, value in replacement.items())
    request(client, "DELETE", path, 204)
    assert request(client, "GET", collection, 200) == []
    request(client, "GET", path, 404)
    request(client, "PUT", path, 404, json=replacement)
    request(client, "DELETE", path, 404)


@pytest.mark.parametrize("resource,payload", [
    ("authors", {"name": " \t", "email": "a@example.com"}),
    ("authors", {"name": "A", "email": "invalid"}),
    ("categories", {"name": ""}),
    ("ingredients", {"name": "\t "}),
])
def test_resource_validation(client, resource, payload):
    request(client, "POST", f"/{resource}", 422, json=payload)


@pytest.mark.parametrize("field,value", [
    ("title", " \t"), ("instructions", ""), ("preparation_time", 0),
    ("preparation_time", False), ("preparation_time", 1.5),
    ("servings", -1), ("servings", True), ("servings", 2.5), ("servings", "2"),
    ("author_id", True), ("category_id", 0),
])
def test_recipe_validation(client, catalogue, field, value):
    author, _, _, recipe = catalogue
    payload = {**recipe_data(author["id"]), field: value}
    request(client, "POST", "/recipes", 422, json=payload)
    request(client, "PUT", f"/recipes/{recipe['id']}", 422, json=payload)


@pytest.mark.parametrize("quantity,unit", [
    (0, "g"), (-1, "g"), (True, "g"), ("4", "g"), (2, "kg"),
    (float("nan"), "g"), (float("inf"), "g"), (float("-inf"), "g"),
])
def test_association_validation(client, catalogue, quantity, unit):
    _, _, ingredient, recipe = catalogue
    path = f"/recipes/{recipe['id']}/ingredients"
    ingredient_id = ingredient["id"]
    fields = {"quantity": quantity, "unit": unit}
    request(client, "POST", path, 422,
            content=json.dumps({"ingredient_id": ingredient_id, **fields}),
            headers={"content-type": "application/json"})
    request(client, "POST", path, 201, json={"ingredient_id": ingredient_id, "quantity": 2, "unit": "pcs"})
    request(client, "PUT", f"{path}/{ingredient_id}", 422,
            content=json.dumps(fields), headers={"content-type": "application/json"})


@pytest.mark.parametrize("resource", ["categories", "ingredients"])
def test_unique_names(client, resource):
    first = create(client, resource, name=" \u0421\u0430\u043b\u0430\u0442\u0430 ")
    second = create(client, resource, name="Other")
    same_name = {"name": " \u0421\u0410\u041b\u0410\u0422\u0410 "}
    request(client, "POST", f"/{resource}", 409, json=same_name)
    request(client, "PUT", f"/{resource}/{second['id']}", 409, json=same_name)
    request(client, "PUT", f"/{resource}/{first['id']}", 200, json=same_name)
    assert request(client, "GET", f"/{resource}/{second['id']}", 200) == second


def test_unique_emails_and_recipe_titles(client):
    author = create(client, "authors", name="Maria", email="maria@example.com")
    other = create(client, "authors", name="Maria", email="other@example.com")
    email_payload = {"name": "Maria", "email": " MARIA@EXAMPLE.COM "}
    request(client, "POST", "/authors", 409, json=email_payload)
    request(client, "PUT", f"/authors/{other['id']}", 409, json=email_payload)
    request(client, "PUT", f"/authors/{author['id']}", 200, json=email_payload)

    title = " \u0411\u0430\u043d\u0438\u0446\u0430 "
    first = create(client, "recipes", **recipe_data(author["id"], title=title))
    second = create(client, "recipes", **recipe_data(other["id"], title=title))
    same_title = recipe_data(author["id"], title=" \u0411\u0410\u041d\u0418\u0426\u0410 ")
    request(client, "POST", "/recipes", 409, json=same_title)
    request(client, "PUT", f"/recipes/{second['id']}", 409, json=same_title)
    request(client, "PUT", f"/recipes/{first['id']}", 200, json=same_title)
    assert request(client, "GET", f"/recipes/{second['id']}", 200) == second


def test_recipe_references_and_replacement(client, catalogue):
    author, _, _, recipe = catalogue
    path = f"/recipes/{recipe['id']}"
    for fields in ({"author_id": 999}, {"category_id": 999}):
        payload = recipe_data(author["id"])
        payload.update(fields)
        request(client, "POST", "/recipes", 404, json=payload)
        request(client, "PUT", path, 404, json=payload)
    request(client, "PUT", path, 422, json={"title": "Incomplete"})
    replacement = request(client, "PUT", path, 200, json=recipe_data(author["id"]))
    assert replacement["category_id"] is None


def test_associations(client, catalogue):
    author, _, ingredient, recipe = catalogue
    author_path = f"/authors/{author['id']}/recipes"
    assert request(client, "GET", author_path, 200) == [recipe]
    request(client, "GET", "/authors/999/recipes", 404)
    other = create(client, "authors", name="Maria", email="other@example.com")
    assert request(client, "GET", f"/authors/{other['id']}/recipes", 200) == []

    path = f"/recipes/{recipe['id']}/ingredients"
    item = f"{path}/{ingredient['id']}"
    quantity = {"quantity": 2, "unit": "pcs"}
    data = {"ingredient_id": ingredient["id"], **quantity}
    assert request(client, "GET", path, 200) == []
    request(client, "GET", "/recipes/999/ingredients", 404)
    request(client, "POST", "/recipes/999/ingredients", 404, json=data)
    request(client, "PUT", f"/recipes/999/ingredients/{ingredient['id']}", 404, json=quantity)
    request(client, "DELETE", f"/recipes/999/ingredients/{ingredient['id']}", 404)
    request(client, "POST", path, 404, json={**data, "ingredient_id": 999})
    request(client, "PUT", f"{path}/999", 404, json=quantity)
    request(client, "DELETE", f"{path}/999", 404)
    request(client, "PUT", item, 404, json=quantity)
    request(client, "DELETE", item, 404)

    linked = request(client, "POST", path, 201, json=data)
    assert linked == {**data, "ingredient": ingredient}
    request(client, "POST", path, 409, json={**data, "quantity": 9})
    assert request(client, "GET", path, 200) == [linked]
    changed = request(client, "PUT", item, 200, json={"quantity": 12.5, "unit": "g"})
    assert changed == {**linked, "quantity": 12.5, "unit": "g"}
    assert request(client, "GET", path, 200) == [changed]
    request(client, "DELETE", item, 204)
    assert request(client, "GET", path, 200) == []
    assert request(client, "GET", f"/ingredients/{ingredient['id']}", 200) == ingredient


def test_filtering(client, catalogue):
    author, category, _, _ = catalogue
    other = create(client, "categories", name="Other")
    title = "\u0421\u0430\u043b\u0430\u0442\u0430"
    match = create(client, "recipes", **recipe_data(
        author["id"], title=f"{title} 100%_ Fresh", category_id=category["id"]
    ))
    for prefix, category_id, time in [
        ("Slow", category["id"], 11), ("Other", other["id"], 5),
    ]:
        create(client, "recipes", **recipe_data(
            author["id"], title=f"{prefix} {title} 100XX", category_id=category_id, preparation_time=time
        ))

    filters = {"title": " \u0410\u041b\u0410\u0422 ", "category_id": category["id"], "max_preparation_time": 10}
    assert request(client, "GET", "/recipes", 200, params=filters) == [match]
    for wildcard in ("%_", "%", "_"):
        assert request(client, "GET", "/recipes", 200, params={"title": wildcard}) == [match]
    assert request(client, "GET", "/recipes", 200, params={"title": "missing"}) == []
    assert request(client, "GET", "/recipes", 200, params={"category_id": 999}) == []
    for invalid in ({"category_id": 0}, {"max_preparation_time": -1},
                    {"max_preparation_time": "1.5"}, {"title": " \t"}):
        request(client, "GET", "/recipes", 422, params=invalid)


def test_scaling_is_read_only(client, catalogue):
    _, _, ingredient, recipe = catalogue
    base = f"/recipes/{recipe['id']}"
    quantity = {"ingredient_id": ingredient["id"], "quantity": 3.5, "unit": "pcs"}
    assert request(client, "GET", f"{base}/scaled", 200, params={"servings": 2}) == {
        **recipe, "servings": 2,
    }
    linked = request(client, "POST", f"{base}/ingredients", 201, json=quantity)
    for servings, expected in [(1, 0.875), (2, 1.75), (8, 7), (52, 45.5)]:
        scaled = request(client, "GET", f"{base}/scaled", 200, params={"servings": servings})
        assert scaled == {**recipe, "servings": servings,
                          "ingredients": [{**linked, "quantity": expected}]}
    for servings in [0, -1, 1.5, 53, "true", "2.0"]:
        request(client, "GET", f"{base}/scaled", 422, params={"servings": servings})
    request(client, "GET", f"{base}/scaled", 422)
    request(client, "GET", "/recipes/999/scaled", 404, params={"servings": 2})
    assert request(client, "GET", base, 200) == {**recipe, "ingredients": [linked]}


def test_deletion_policies(client, database, catalogue):
    author, category, ingredient, recipe = catalogue
    paths = [
        f"/authors/{author['id']}", f"/categories/{category['id']}",
        f"/ingredients/{ingredient['id']}", f"/recipes/{recipe['id']}",
    ]
    author_path, category_path, ingredient_path, recipe_path = paths
    request(client, "POST", f"{recipe_path}/ingredients", 201,
            json={"ingredient_id": ingredient["id"], "quantity": 3, "unit": "pcs"})
    request(client, "DELETE", author_path, 409)
    request(client, "DELETE", ingredient_path, 409)
    request(client, "DELETE", category_path, 204)
    assert request(client, "GET", recipe_path, 200)["category_id"] is None
    request(client, "DELETE", recipe_path, 204)
    with database.connect() as conn:
        assert conn.exec_driver_sql("SELECT count(*) FROM recipe_ingredients").scalar_one() == 0
    assert request(client, "GET", ingredient_path, 200) == ingredient
    request(client, "DELETE", author_path, 204)
    request(client, "DELETE", ingredient_path, 204)


def test_foreign_key_enforcement(client, database, catalogue):
    author, _, ingredient, recipe = catalogue
    request(client, "POST", f"/recipes/{recipe['id']}/ingredients", 201,
            json={"ingredient_id": ingredient["id"], "quantity": 1, "unit": "g"})
    with database.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        for sql, values in [
            ("DELETE FROM authors WHERE id = ?", (author["id"],)),
            ("DELETE FROM ingredients WHERE id = ?", (ingredient["id"],)),
            ("UPDATE recipes SET author_id = 999 WHERE id = ?", (recipe["id"],)),
            ("UPDATE recipes SET category_id = 999 WHERE id = ?", (recipe["id"],)),
        ]:
            with pytest.raises(IntegrityError):
                conn.exec_driver_sql(sql, values)
            conn.rollback()
        assert conn.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_openapi_and_swagger(client):
    spec = request(client, "GET", "/openapi.json", 200)
    assert spec["paths"]["/recipes"]["post"]["responses"]["201"]
    assert spec["paths"]["/recipes/{recipe_id}/scaled"]["get"]
    assert spec["paths"]["/authors/{author_id}/recipes"]["get"]
    assert all(not path.endswith("/") for path in spec["paths"])
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "/openapi.json" in docs.text
