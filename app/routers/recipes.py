from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.config import MAX_SCALED_SERVINGS
from app.database import DatabaseSession
from app.routers.parameters import IntegerParameter, ResourceId
from app.schemas import (
    NonBlankText,
    RecipeCreate,
    RecipeIngredientCreate,
    RecipeIngredientResponse,
    RecipeIngredientUpdate,
    RecipeResponse,
    RecipeUpdate,
    SQLITE_MAX_INTEGER,
)
from app.services import recipes


router = APIRouter(prefix="/recipes", tags=["Recipes"])
PositiveQuery = Annotated[IntegerParameter, Query(gt=0, le=SQLITE_MAX_INTEGER)]
ScaledServings = Annotated[IntegerParameter, Query(ge=1, le=MAX_SCALED_SERVINGS)]


@router.post("", response_model=RecipeResponse, status_code=201)
def create_recipe(data: RecipeCreate, session: DatabaseSession):
    return recipes.create_recipe(session, data)


@router.get("", response_model=list[RecipeResponse])
def list_recipes(
    session: DatabaseSession,
    title: NonBlankText | None = None,
    category_id: PositiveQuery | None = None,
    max_preparation_time: PositiveQuery | None = None,
):
    return recipes.get_recipes(session, title, category_id, max_preparation_time)


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(recipe_id: ResourceId, session: DatabaseSession):
    return recipes.get_recipe_by_id(session, recipe_id)


@router.put("/{recipe_id}", response_model=RecipeResponse, summary="Replace recipe fields")
def update_recipe(recipe_id: ResourceId, data: RecipeUpdate, session: DatabaseSession):
    return recipes.update_recipe(session, recipe_id, data)


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: ResourceId, session: DatabaseSession) -> Response:
    recipes.delete_recipe(session, recipe_id)
    return Response(status_code=204)


@router.get("/{recipe_id}/ingredients", response_model=list[RecipeIngredientResponse])
def list_recipe_ingredients(recipe_id: ResourceId, session: DatabaseSession):
    return recipes.get_recipe_ingredients(session, recipe_id)


@router.post("/{recipe_id}/ingredients", response_model=RecipeIngredientResponse, status_code=201)
def add_recipe_ingredient(recipe_id: ResourceId, data: RecipeIngredientCreate, session: DatabaseSession):
    return recipes.add_recipe_ingredient(session, recipe_id, data)


@router.put("/{recipe_id}/ingredients/{ingredient_id}", response_model=RecipeIngredientResponse)
def update_recipe_ingredient(
    recipe_id: ResourceId,
    ingredient_id: ResourceId,
    data: RecipeIngredientUpdate,
    session: DatabaseSession,
):
    return recipes.update_recipe_ingredient(session, recipe_id, ingredient_id, data)


@router.delete("/{recipe_id}/ingredients/{ingredient_id}", status_code=204)
def remove_recipe_ingredient(
    recipe_id: ResourceId, ingredient_id: ResourceId, session: DatabaseSession
) -> Response:
    recipes.remove_recipe_ingredient(session, recipe_id, ingredient_id)
    return Response(status_code=204)


@router.get("/{recipe_id}/scaled", response_model=RecipeResponse)
def get_scaled_recipe(recipe_id: ResourceId, servings: ScaledServings, session: DatabaseSession):
    """Scale ingredient quantities to the requested servings without saving them."""
    return recipes.scale_recipe(session, recipe_id, servings)
