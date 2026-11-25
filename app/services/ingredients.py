from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Ingredient, RecipeIngredient
from app.schemas import IngredientCreate, IngredientUpdate
from app.services.common import commit_write, normalize


INGREDIENT_CONFLICT = "That ingredient name already exists."


def get_ingredients(session: Session) -> list[Ingredient]:
    return list(session.scalars(select(Ingredient).order_by(Ingredient.id)))


def get_ingredient_by_id(session: Session, ingredient_id: int) -> Ingredient:
    ingredient = session.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found.")
    return ingredient


def check_name(session: Session, normalized_name: str, ingredient_id: int | None = None) -> None:
    query = select(Ingredient.id).where(Ingredient.normalized_name == normalized_name)
    if ingredient_id is not None:
        query = query.where(Ingredient.id != ingredient_id)
    if session.scalar(query) is not None:
        raise HTTPException(status_code=409, detail=INGREDIENT_CONFLICT)


def create_ingredient(session: Session, data: IngredientCreate) -> Ingredient:
    normalized_name = normalize(data.name)
    check_name(session, normalized_name)
    ingredient = Ingredient(**data.model_dump(), normalized_name=normalized_name)
    session.add(ingredient)
    commit_write(session, INGREDIENT_CONFLICT)
    return ingredient


def update_ingredient(session: Session, ingredient_id: int, data: IngredientUpdate) -> Ingredient:
    ingredient = get_ingredient_by_id(session, ingredient_id)
    normalized_name = normalize(data.name)
    check_name(session, normalized_name, ingredient_id)
    ingredient.name = data.name
    ingredient.normalized_name = normalized_name
    commit_write(session, INGREDIENT_CONFLICT)
    return ingredient


def delete_ingredient(session: Session, ingredient_id: int) -> None:
    ingredient = get_ingredient_by_id(session, ingredient_id)
    in_use = select(RecipeIngredient.ingredient_id).where(RecipeIngredient.ingredient_id == ingredient_id).limit(1)
    if session.scalar(in_use) is not None:
        raise HTTPException(status_code=409, detail="An ingredient used in a recipe cannot be deleted.")
    session.delete(ingredient)
    commit_write(session, "An ingredient used in a recipe cannot be deleted.")
