from fastapi import APIRouter, Response

from app.database import DatabaseSession
from app.routers.parameters import ResourceId
from app.schemas import AuthorCreate, AuthorResponse, AuthorUpdate, RecipeResponse
from app.services import authors, recipes


router = APIRouter(prefix="/authors", tags=["Authors"])


@router.post("", response_model=AuthorResponse, status_code=201)
def create_author(data: AuthorCreate, session: DatabaseSession):
    return authors.create_author(session, data)


@router.get("", response_model=list[AuthorResponse])
def list_authors(session: DatabaseSession):
    return authors.get_authors(session)


@router.get("/{author_id}", response_model=AuthorResponse)
def get_author(author_id: ResourceId, session: DatabaseSession):
    return authors.get_author_by_id(session, author_id)


@router.put("/{author_id}", response_model=AuthorResponse, summary="Replace author fields")
def update_author(author_id: ResourceId, data: AuthorUpdate, session: DatabaseSession):
    return authors.update_author(session, author_id, data)


@router.delete("/{author_id}", status_code=204)
def delete_author(author_id: ResourceId, session: DatabaseSession) -> Response:
    authors.delete_author(session, author_id)
    return Response(status_code=204)


@router.get("/{author_id}/recipes", response_model=list[RecipeResponse])
def list_author_recipes(author_id: ResourceId, session: DatabaseSession):
    return recipes.get_author_recipes(session, author_id)
