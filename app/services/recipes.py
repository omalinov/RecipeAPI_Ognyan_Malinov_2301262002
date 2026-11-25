from math import isfinite

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Recipe, RecipeIngredient
from app.schemas import RecipeCreate, RecipeIngredientCreate, RecipeIngredientUpdate, RecipeResponse, RecipeUpdate
from app.services.authors import get_author_by_id
from app.services.categories import get_category_by_id
from app.services.common import commit_write, normalize
from app.services.ingredients import get_ingredient_by_id


TITLE_CONFLICT = "This author already has a recipe with that title."
LINK_CONFLICT = "This ingredient is already linked to the recipe."


def get_recipes(
    session: Session,
    title: str | None = None,
    category_id: int | None = None,
    max_preparation_time: int | None = None,
) -> list[Recipe]:
    query = select(Recipe).options(selectinload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient))
    if title is not None:
        # SQLite instr uses a literal substring, including any percent or underscore.
        query = query.where(func.instr(Recipe.normalized_title, normalize(title)) > 0)
    if category_id is not None:
        query = query.where(Recipe.category_id == category_id)
    if max_preparation_time is not None:
        query = query.where(Recipe.preparation_time <= max_preparation_time)
    return list(session.scalars(query.order_by(Recipe.id)))


def get_recipe_by_id(session: Session, recipe_id: int) -> Recipe:
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found.")
    return recipe


def get_author_recipes(session: Session, author_id: int) -> list[Recipe]:
    get_author_by_id(session, author_id)
    query = (
        select(Recipe)
        .where(Recipe.author_id == author_id)
        .options(selectinload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient))
        .order_by(Recipe.id)
    )
    return list(session.scalars(query))


def validate_recipe(
    session: Session, data: RecipeCreate | RecipeUpdate, recipe_id: int | None = None
) -> str:
    get_author_by_id(session, data.author_id)
    if data.category_id is not None:
        get_category_by_id(session, data.category_id)
    normalized_title = normalize(data.title)
    query = select(Recipe.id).where(
        Recipe.author_id == data.author_id, Recipe.normalized_title == normalized_title
    )
    if recipe_id is not None:
        query = query.where(Recipe.id != recipe_id)
    if session.scalar(query) is not None:
        raise HTTPException(status_code=409, detail=TITLE_CONFLICT)
    return normalized_title


def create_recipe(session: Session, data: RecipeCreate) -> Recipe:
    normalized_title = validate_recipe(session, data)
    recipe = Recipe(**data.model_dump(), normalized_title=normalized_title)
    session.add(recipe)
    commit_write(session, "The recipe conflicts with its author, category, or title.")
    return recipe


def update_recipe(session: Session, recipe_id: int, data: RecipeUpdate) -> Recipe:
    recipe = get_recipe_by_id(session, recipe_id)
    recipe.normalized_title = validate_recipe(session, data, recipe_id)
    for field, value in data.model_dump().items():
        setattr(recipe, field, value)
    commit_write(session, "The recipe conflicts with its author, category, or title.")
    return recipe


def delete_recipe(session: Session, recipe_id: int) -> None:
    session.delete(get_recipe_by_id(session, recipe_id))
    commit_write(session, "The recipe could not be deleted due to a database constraint.")


def get_recipe_ingredients(session: Session, recipe_id: int) -> list[RecipeIngredient]:
    get_recipe_by_id(session, recipe_id)
    query = (
        select(RecipeIngredient)
        .where(RecipeIngredient.recipe_id == recipe_id)
        .options(selectinload(RecipeIngredient.ingredient))
        .order_by(RecipeIngredient.ingredient_id)
    )
    return list(session.scalars(query))


def get_recipe_ingredient(session: Session, recipe_id: int, ingredient_id: int) -> RecipeIngredient:
    get_recipe_by_id(session, recipe_id)
    link = session.get(RecipeIngredient, (recipe_id, ingredient_id))
    if link is None:
        raise HTTPException(status_code=404, detail="Ingredient is not linked to this recipe.")
    return link


def add_recipe_ingredient(
    session: Session, recipe_id: int, data: RecipeIngredientCreate
) -> RecipeIngredient:
    get_recipe_by_id(session, recipe_id)
    get_ingredient_by_id(session, data.ingredient_id)
    if session.get(RecipeIngredient, (recipe_id, data.ingredient_id)) is not None:
        raise HTTPException(status_code=409, detail=LINK_CONFLICT)
    link = RecipeIngredient(recipe_id=recipe_id, **data.model_dump())
    session.add(link)
    commit_write(session, "The ingredient link conflicts with the recipe or ingredient.")
    return link


def update_recipe_ingredient(
    session: Session, recipe_id: int, ingredient_id: int, data: RecipeIngredientUpdate
) -> RecipeIngredient:
    link = get_recipe_ingredient(session, recipe_id, ingredient_id)
    link.quantity = data.quantity
    link.unit = data.unit
    commit_write(session, "The ingredient link could not be updated.")
    return link


def remove_recipe_ingredient(session: Session, recipe_id: int, ingredient_id: int) -> None:
    session.delete(get_recipe_ingredient(session, recipe_id, ingredient_id))
    commit_write(session, "The ingredient link could not be removed.")


def scale_recipe(session: Session, recipe_id: int, servings: int) -> RecipeResponse:
    recipe = RecipeResponse.model_validate(get_recipe_by_id(session, recipe_id))
    ratio = servings / recipe.servings
    for ingredient in recipe.ingredients:
        quantity = ingredient.quantity * ratio
        if not isfinite(quantity) or quantity <= 0:
            raise HTTPException(status_code=422, detail="Scaled quantity is outside the numeric range.")
        ingredient.quantity = quantity
    recipe.servings = servings
    return recipe
