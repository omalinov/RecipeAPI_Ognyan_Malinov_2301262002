# Recipe Catalogue API

A FastAPI REST API backed by SQLite. It manages authors, categories, ingredients and recipes, including the quantity and unit of each ingredient in a recipe.

## Run locally

Use Python 3.14 and run the commands from the repository root.

**Windows (PowerShell)**

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` in place of `python` below.

**Linux**

```bash
python3.14 -m venv .venv
source .venv/bin/activate
```

**Either platform**

```sh
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

Open [Swagger UI](http://127.0.0.1:8000/docs) or the [OpenAPI schema](http://127.0.0.1:8000/openapi.json). The commands use the local `recipes.db` file.

## Endpoints

Each collection supports `POST` and `GET`. Each item URL, such as `/authors/1`, supports `GET`, `PUT` and `DELETE`.

| Collection | Resource |
| --- | --- |
| `/authors` | Author name and email |
| `/categories` | Category name |
| `/ingredients` | Ingredient name |
| `/recipes` | Title, instructions, preparation time in minutes, servings, difficulty, author ID and optional category ID |

`PUT` replaces the resource's editable fields. Omitting `category_id` on a recipe update clears its category. Recipe ingredients are managed through their own endpoints.

| Method and path | Behavior |
| --- | --- |
| `GET /authors/{author_id}/recipes` | List the author's recipes |
| `GET /recipes/{recipe_id}/ingredients` | List ingredient details, quantities and units |
| `POST /recipes/{recipe_id}/ingredients` | Link an existing ingredient by ID with a quantity and unit |
| `PUT /recipes/{recipe_id}/ingredients/{ingredient_id}` | Replace the link's quantity and unit |
| `DELETE /recipes/{recipe_id}/ingredients/{ingredient_id}` | Remove the link |
| `GET /recipes/{recipe_id}/scaled?servings=6` | Read a recipe with quantities scaled to six servings |

`GET /recipes` combines `title`, `category_id` and `max_preparation_time` with AND. Title is a literal case-insensitive substring and maximum time is inclusive. Scaling accepts 1 to **52** servings (50 + 02). It multiplies each original quantity by the ratio of requested to original servings and preserves the ingredient IDs and units, including fractional `pcs`. Quantities use SQLite floating-point values. A scaled quantity outside the positive finite range returns 422. Scaling reads the database and builds a separate response.

| Status | Meaning |
| --- | --- |
| 200 | Read or update succeeded. An existing parent with no related records returns an empty list. |
| 201 | Resource or ingredient link created |
| 204 | Resource or ingredient link deleted, with an empty body |
| 404 | Resource, referenced author/category/ingredient, or ingredient link missing |
| 409 | Duplicate unique value, duplicate ingredient link, or deletion blocked by a reference |
| 422 | Invalid request data or query parameters |

## Swagger walkthrough

In Swagger UI, expand each operation, select **Try it out**, enter the data and select **Execute**. Use the IDs returned by your requests in place of the example IDs.

1. Create an author with `POST /authors` and `{"name":"Maria Petrova","email":"maria@example.com"}`.
2. Create a category with `POST /categories` and `{"name":"Salads"}`.
3. Create an ingredient with `POST /ingredients` and `{"name":"Tomato"}`.
4. Create a recipe with `POST /recipes`. Confirm that each create operation returns 201.

   ```json
   {
     "title": "Tomato Salad",
     "instructions": "Slice the tomatoes and toss with salt.",
     "preparation_time": 10,
     "servings": 4,
     "author_id": 1,
     "category_id": 1,
     "difficulty": "easy"
   }
   ```

5. Use `POST /recipes/{recipe_id}/ingredients` with `{"ingredient_id":1,"quantity":3.5,"unit":"pcs"}`. Repeat the request and check for 409. List the links to confirm the quantity is still 3.5.
6. Use `GET /recipes/{recipe_id}/scaled` with `servings=6`. Check for six servings and 5.25 pcs. Fetch the original recipe and confirm four servings and 3.5 pcs. Try `servings=53` and confirm 422.
7. List the author's recipes and filter `GET /recipes` with `title=tomato`, the salad category ID and `max_preparation_time=10`. Both requests should return the recipe. Try deleting the author while the recipe exists and confirm 409.

## Data model and code

An author has many recipes. A category can have many recipes, and recipes can also be uncategorized. Recipes and ingredients are many-to-many through `recipe_ingredients`, whose composite key stores each pair once. The link also stores its quantity and unit (`g`, `ml` or `pcs`). SQLite cascades recipe deletion to links and sets recipe category IDs to NULL on category deletion. It restricts deletion of referenced authors and ingredients. Foreign keys are enabled on every database connection.

Routers define the HTTP contract and inject a per-request SQLAlchemy session. Services query the database, enforce business rules, and commit or roll back writes. SQLAlchemy models describe persisted entities and relationships, while Pydantic schemas validate requests and serialize responses. Display names and titles are trimmed. Services use trimmed, Unicode-casefolded keys for unique category and ingredient names, per-author recipe titles, and author emails. Authors can share a name.

## Migrations and tests

Revision `0001` creates the catalogue tables. Revision `0002` adds required difficulty (`easy`, `medium`, `hard`), backfills existing rows to `easy`, and keeps their ingredient links intact during SQLite's table rebuild. New recipe requests must provide difficulty. Downgrading to `0001` removes difficulty values while preserving recipes and ingredient links.

```sh
pytest
python -m alembic current
python -m alembic check
```

Tests use temporary SQLite databases initialized by Alembic. They cover the API contract, validation, constraints, scaling, deletion behavior, fresh migration, and upgrade and downgrade with existing data.
