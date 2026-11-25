from fastapi import APIRouter, Response

from app.database import DatabaseSession
from app.routers.parameters import ResourceId
from app.schemas import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services import categories


router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(data: CategoryCreate, session: DatabaseSession):
    return categories.create_category(session, data)


@router.get("", response_model=list[CategoryResponse])
def list_categories(session: DatabaseSession):
    return categories.get_categories(session)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: ResourceId, session: DatabaseSession):
    return categories.get_category_by_id(session, category_id)


@router.put("/{category_id}", response_model=CategoryResponse, summary="Replace category fields")
def update_category(category_id: ResourceId, data: CategoryUpdate, session: DatabaseSession):
    return categories.update_category(session, category_id, data)


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: ResourceId, session: DatabaseSession) -> Response:
    categories.delete_category(session, category_id)
    return Response(status_code=204)
