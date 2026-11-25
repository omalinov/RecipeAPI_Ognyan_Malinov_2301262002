from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category
from app.schemas import CategoryCreate, CategoryUpdate
from app.services.common import commit_write, normalize


CATEGORY_CONFLICT = "That category name already exists."


def get_categories(session: Session) -> list[Category]:
    return list(session.scalars(select(Category).order_by(Category.id)))


def get_category_by_id(session: Session, category_id: int) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found.")
    return category


def check_name(session: Session, normalized_name: str, category_id: int | None = None) -> None:
    query = select(Category.id).where(Category.normalized_name == normalized_name)
    if category_id is not None:
        query = query.where(Category.id != category_id)
    if session.scalar(query) is not None:
        raise HTTPException(status_code=409, detail=CATEGORY_CONFLICT)


def create_category(session: Session, data: CategoryCreate) -> Category:
    normalized_name = normalize(data.name)
    check_name(session, normalized_name)
    category = Category(**data.model_dump(), normalized_name=normalized_name)
    session.add(category)
    commit_write(session, CATEGORY_CONFLICT)
    return category


def update_category(session: Session, category_id: int, data: CategoryUpdate) -> Category:
    category = get_category_by_id(session, category_id)
    normalized_name = normalize(data.name)
    check_name(session, normalized_name, category_id)
    category.name = data.name
    category.normalized_name = normalized_name
    commit_write(session, CATEGORY_CONFLICT)
    return category


def delete_category(session: Session, category_id: int) -> None:
    category = get_category_by_id(session, category_id)
    session.delete(category)
    commit_write(session, "The category could not be deleted due to a database constraint.")
