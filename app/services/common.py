from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session


def normalize(value: str) -> str:
    return value.strip().casefold()


def commit_write(session: Session, conflict_detail: str) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=conflict_detail) from exc
    except SQLAlchemyError:
        session.rollback()
        raise
