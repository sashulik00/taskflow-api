from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base

ModelT = TypeVar("ModelT", bound=Base)

# Коды ошибок PostgreSQL
UNIQUE_VIOLATION = "23505"
FOREIGN_KEY_VIOLATION = "23503"


def get_or_404(db: Session, model: type[ModelT], object_id: int, name: str) -> ModelT:
    """Найти запись по id или вернуть клиенту ошибку 404."""
    obj = db.get(model, object_id)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found"
        )
    return obj


def commit_or_409(db: Session) -> None:
    """Сохранить изменения; при нарушении правил базы вернуть 409 вместо 500."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        code = getattr(exc.orig, "pgcode", None)
        if code == UNIQUE_VIOLATION:
            detail = "Запись с таким уникальным значением уже существует"
        elif code == FOREIGN_KEY_VIOLATION:
            detail = "Связанная запись не найдена или запись используется в других таблицах"
        else:
            detail = "Данные нарушают ограничения базы данных"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc