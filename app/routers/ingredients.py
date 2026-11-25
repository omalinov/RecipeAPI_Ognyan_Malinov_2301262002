from fastapi import APIRouter, Response

from app.database import DatabaseSession
from app.routers.parameters import ResourceId
from app.schemas import IngredientCreate, IngredientResponse, IngredientUpdate
from app.services import ingredients


router = APIRouter(prefix="/ingredients", tags=["Ingredients"])


@router.post("", response_model=IngredientResponse, status_code=201)
def create_ingredient(data: IngredientCreate, session: DatabaseSession):
    return ingredients.create_ingredient(session, data)


@router.get("", response_model=list[IngredientResponse])
def list_ingredients(session: DatabaseSession):
    return ingredients.get_ingredients(session)


@router.get("/{ingredient_id}", response_model=IngredientResponse)
def get_ingredient(ingredient_id: ResourceId, session: DatabaseSession):
    return ingredients.get_ingredient_by_id(session, ingredient_id)


@router.put("/{ingredient_id}", response_model=IngredientResponse, summary="Replace ingredient fields")
def update_ingredient(ingredient_id: ResourceId, data: IngredientUpdate, session: DatabaseSession):
    return ingredients.update_ingredient(session, ingredient_id, data)


@router.delete("/{ingredient_id}", status_code=204)
def delete_ingredient(ingredient_id: ResourceId, session: DatabaseSession) -> Response:
    ingredients.delete_ingredient(session, ingredient_id)
    return Response(status_code=204)
