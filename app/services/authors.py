from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Author, Recipe
from app.schemas import AuthorCreate, AuthorUpdate
from app.services.common import commit_write, normalize


AUTHOR_CONFLICT = "That email is already registered."


def get_authors(session: Session) -> list[Author]:
    return list(session.scalars(select(Author).order_by(Author.id)))


def get_author_by_id(session: Session, author_id: int) -> Author:
    author = session.get(Author, author_id)
    if author is None:
        raise HTTPException(status_code=404, detail="Author not found.")
    return author


def check_email(session: Session, normalized_email: str, author_id: int | None = None) -> None:
    query = select(Author.id).where(Author.normalized_email == normalized_email)
    if author_id is not None:
        query = query.where(Author.id != author_id)
    if session.scalar(query) is not None:
        raise HTTPException(status_code=409, detail=AUTHOR_CONFLICT)


def create_author(session: Session, data: AuthorCreate) -> Author:
    normalized_email = normalize(data.email)
    check_email(session, normalized_email)
    author = Author(**data.model_dump(), normalized_email=normalized_email)
    session.add(author)
    commit_write(session, AUTHOR_CONFLICT)
    return author


def update_author(session: Session, author_id: int, data: AuthorUpdate) -> Author:
    author = get_author_by_id(session, author_id)
    normalized_email = normalize(data.email)
    check_email(session, normalized_email, author_id)
    author.name = data.name
    author.email = data.email
    author.normalized_email = normalized_email
    commit_write(session, AUTHOR_CONFLICT)
    return author


def delete_author(session: Session, author_id: int) -> None:
    author = get_author_by_id(session, author_id)
    in_use = select(Recipe.author_id).where(Recipe.author_id == author_id).limit(1)
    if session.scalar(in_use) is not None:
        raise HTTPException(status_code=409, detail="An author with recipes cannot be deleted.")
    session.delete(author)
    commit_write(session, "An author with recipes cannot be deleted.")
