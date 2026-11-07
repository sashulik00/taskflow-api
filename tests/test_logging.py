import logging

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.config import Settings, settings
from app.database import get_db
from app.logging_config import setup_logging
from app.main import app
from app.routers.common import commit_or_409


class BrokenSession:
    """Сессия, у которой база «недоступна»."""

    def execute(self, *args, **kwargs):
        raise SQLAlchemyError("database is down")


class FakeDatabaseError:
    pgcode = "23514"  # любая ошибка, кроме уникальности и внешнего ключа


class FailingCommitSession:
    def commit(self):
        raise IntegrityError("INSERT ...", {}, FakeDatabaseError())

    def rollback(self):
        pass


def messages(caplog, level):
    """Сообщения лога заданного уровня."""
    return [r.getMessage() for r in caplog.records if r.levelno == level]


def test_debug_is_logged_when_object_is_found(client, project, caplog):
    caplog.set_level(logging.DEBUG, logger="app")

    client.get(f"/v1/projects/{project['id']}")

    assert any("найден" in m for m in messages(caplog, logging.DEBUG))


def test_info_is_logged_for_every_request(client, caplog):
    caplog.set_level(logging.DEBUG, logger="app")

    client.get("/health")

    assert any("GET /health -> 200" in m for m in messages(caplog, logging.INFO))


def test_warning_is_logged_when_object_is_missing(client, caplog):
    caplog.set_level(logging.DEBUG, logger="app")

    client.get("/v1/projects/999")

    assert any("не найден" in m for m in messages(caplog, logging.WARNING))


def test_warning_is_logged_for_duplicate_value(client, user, caplog):
    caplog.set_level(logging.DEBUG, logger="app")

    client.post("/v1/users", json={"email": user["email"], "display_name": "Двойник"})

    assert any("уникальность" in m for m in messages(caplog, logging.WARNING))


def test_warning_is_logged_for_missing_reference(client, caplog):
    caplog.set_level(logging.DEBUG, logger="app")

    client.post("/v1/tasks", json={"project_id": 999, "title": "Тест"})

    assert any("внешний ключ" in m for m in messages(caplog, logging.WARNING))


def test_error_is_logged_for_unknown_database_error(caplog):
    caplog.set_level(logging.DEBUG, logger="app")

    with pytest.raises(HTTPException):
        commit_or_409(FailingCommitSession())

    assert any("ограничение" in m for m in messages(caplog, logging.ERROR))


def test_critical_is_logged_when_database_is_down(client, caplog):
    caplog.set_level(logging.DEBUG, logger="app")
    app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert any("недоступна" in m for m in messages(caplog, logging.CRITICAL))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("debug", logging.DEBUG),
        ("INFO", logging.INFO),
        ("warning", logging.WARNING),
        ("ERROR", logging.ERROR),
        ("critical", logging.CRITICAL),
    ],
)
def test_setup_logging_applies_level_from_settings(monkeypatch, value, expected):
    app_logger = logging.getLogger("app")
    previous = app_logger.level
    monkeypatch.setattr(settings, "log_level", value)
    try:
        setup_logging()
        assert app_logger.level == expected
    finally:
        app_logger.setLevel(previous)


def test_settings_read_log_level_from_environment(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "ERROR")

    assert Settings(_env_file=None, database_url="postgresql://x").log_level == "ERROR"


def test_settings_have_default_log_level(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    assert Settings(_env_file=None, database_url="postgresql://x").log_level == "INFO"
