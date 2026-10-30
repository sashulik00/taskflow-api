import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app import schemas
from app.database import get_db
from app.main import app
from app.routers.common import commit_or_409, get_or_404


# ---------- поддельные сессии базы данных ----------

class BrokenSession:
    """Сессия, у которой база «недоступна»."""

    def execute(self, *args, **kwargs):
        raise SQLAlchemyError("database is down")


class FakeDatabaseError:
    """Имитация ошибки PostgreSQL с нужным кодом."""

    def __init__(self, pgcode):
        self.pgcode = pgcode


class FailingCommitSession:
    """Сессия, у которой commit() заканчивается ошибкой целостности."""

    def __init__(self, pgcode):
        self.pgcode = pgcode
        self.rolled_back = False

    def commit(self):
        raise IntegrityError("INSERT ...", {}, FakeDatabaseError(self.pgcode))

    def rollback(self):
        self.rolled_back = True


class FakeGetSession:
    """Сессия, у которой get() возвращает заранее заданный объект."""

    def __init__(self, result):
        self.result = result

    def get(self, model, object_id):
        return self.result


# ---------- /health при недоступной базе ----------

def test_health_returns_503_when_database_is_down(client):
    app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


# ---------- commit_or_409 ----------

def test_commit_or_409_does_nothing_when_commit_succeeds():
    class OkSession:
        committed = False

        def commit(self):
            self.committed = True

    session = OkSession()

    commit_or_409(session)

    assert session.committed is True


@pytest.mark.parametrize(
    ("pgcode", "detail"),
    [
        ("23505", "Запись с таким уникальным значением уже существует"),
        ("23503", "Связанная запись не найдена или запись используется в других таблицах"),
        ("23514", "Данные нарушают ограничения базы данных"),
        (None, "Данные нарушают ограничения базы данных"),
    ],
)
def test_commit_or_409_turns_integrity_error_into_409(pgcode, detail):
    session = FailingCommitSession(pgcode)

    with pytest.raises(HTTPException) as error:
        commit_or_409(session)

    assert error.value.status_code == 409
    assert error.value.detail == detail
    assert session.rolled_back is True  # транзакция откатилась


# ---------- get_or_404 ----------

def test_get_or_404_returns_found_object():
    found = object()

    assert get_or_404(FakeGetSession(found), object, 1, "Thing") is found


def test_get_or_404_raises_404_when_object_is_missing():
    with pytest.raises(HTTPException) as error:
        get_or_404(FakeGetSession(None), object, 1, "Thing")

    assert error.value.status_code == 404
    assert error.value.detail == "Thing not found"


# ---------- Pydantic-схемы ----------

def test_task_create_has_default_status_and_priority():
    task = schemas.TaskCreate(project_id=1, title="Тест")

    assert task.status == "open"
    assert task.priority == "medium"


def test_label_create_has_default_color():
    assert schemas.LabelCreate(name="bug").color == "#6b7280"


def test_update_schema_keeps_only_sent_fields():
    update = schemas.UserUpdate(display_name="Анна")

    assert update.model_dump(exclude_unset=True) == {"display_name": "Анна"}


def test_input_schema_rejects_extra_fields():
    with pytest.raises(ValidationError):
        schemas.ProjectCreate(id=5, name="Тест")


@pytest.mark.parametrize("body", ["", "   ", "\n\t"])
def test_comment_body_cannot_be_blank(body):
    with pytest.raises(ValidationError):
        schemas.CommentCreate(task_id=1, author_id=1, body=body)


def test_comment_body_with_text_is_accepted():
    comment = schemas.CommentCreate(task_id=1, author_id=1, body="  Текст  ")

    assert comment.body == "  Текст  "