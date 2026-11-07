import logging
from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=Base)

# Коды ошибок PostgreSQL
UNIQUE_VIOLATION = "23505"
FOREIGN_KEY_VIOLATION = "23503"


def get_or_404(db: Session, model: type[ModelT], object_id: int, name: str) -> ModelT:
    """Найти запись по id или вернуть клиенту ошибку 404."""
    obj = db.get(model, object_id)
    if obj is None:
        logger.warning("%s с id=%s не найден", name, object_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found")
    logger.debug("%s с id=%s найден", name, object_id)
    return obj


def commit_or_409(db: Session) -> None:
    """Сохранить изменения; при нарушении правил базы вернуть 409 вместо 500."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        code = getattr(exc.orig, "pgcode", None)
        if code == UNIQUE_VIOLATION:
            logger.warning("Нарушена уникальность (pgcode=%s)", code)
            detail = "Запись с таким уникальным значением уже существует"
        elif code == FOREIGN_KEY_VIOLATION:
            logger.warning("Нарушен внешний ключ (pgcode=%s)", code)
            detail = "Связанная запись не найдена или запись используется в других таблицах"
        else:
            logger.error("Нарушено ограничение базы данных (pgcode=%s)", code)
            detail = "Данные нарушают ограничения базы данных"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
