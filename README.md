# Recipe Catalogue API

A FastAPI and SQLite API for authors, recipes, categories, and ingredients.

## Run locally

Use Python 3.14. From the repository root, create a virtual environment with `python -m venv .venv`. On Windows you can also use `py -3.14 -m venv .venv`.

- In PowerShell, run `.\.venv\Scripts\Activate.ps1`.
- On Linux, run `source .venv/bin/activate`.

```sh
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

Open [Swagger UI](http://127.0.0.1:8000/docs). Run `pytest` to test against temporary SQLite databases.

## API at a glance

- `/authors`, `/recipes`, `/categories`, and `/ingredients` support CRUD. `PUT` replaces editable fields. Omitting a recipe's category clears it.
- `GET /authors/{id}/recipes` lists an author's recipes. `GET /recipes` combines the `title`, `category_id`, and `max_preparation_time` filters.
- `/recipes/{id}/ingredients` lists and adds ingredient links. Append the ingredient ID to edit or remove a link.
- `GET /recipes/{id}/scaled?servings=6` recalculates quantities for **1 to 52 servings** and leaves stored quantities unchanged.

Responses use 200 for reads and updates, 201 for creates, 204 for deletes, 404 for missing resources or references, 409 for conflicts, and 422 for invalid input.

## Try it in Swagger

Select **Try it out** and **Execute** for each request. Use the IDs returned by your own requests.

1. Create an author with `POST /authors` and `{"name":"Maria","email":"maria@example.com"}`.
2. Create a category with `POST /categories` and `{"name":"Salads"}`, then an ingredient with `POST /ingredients` and `{"name":"Tomato"}`.
3. Create a recipe with `POST /recipes` and `{"title":"Tomato Salad","instructions":"Slice and toss.","preparation_time":10,"servings":4,"difficulty":"easy","author_id":1,"category_id":1}`.
4. Link the ingredient with `POST /recipes/{id}/ingredients` and `{"ingredient_id":1,"quantity":3.5,"unit":"pcs"}`. Repeat and check for 409.
5. Call `GET /recipes/{id}/scaled?servings=6`. Expect 5.25 pcs. Fetch the original recipe and confirm it still has 3.5 pcs.

## Project structure

Routers handle HTTP requests, services handle queries and business rules, SQLAlchemy models define tables, and Pydantic schemas validate API data. Each recipe has an author and an optional category. Recipes share ingredients through links that store quantities and units. Category names, ingredient names, emails, and each author's recipe titles are unique regardless of case or surrounding whitespace.

Alembic revision `0001` creates the tables. Revision `0002` adds required difficulty (`easy`, `medium`, `hard`) and gives existing recipes the value `easy`.
