import os
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://taskflow:taskflow@localhost:5432/taskflow_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402

TABLES = "comments, tasks, labels, projects, users"


def create_test_database() -> None:
    """Создать базу taskflow_test, если её ещё нет."""
    url = make_url(TEST_DATABASE_URL)
    admin_engine = create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin_engine.connect() as connection:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        )
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    return Config("alembic.ini")


@pytest.fixture(scope="session", autouse=True)
def prepare_database(alembic_config):
    """Один раз за запуск: создать тестовую базу и применить миграции."""
    create_test_database()
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables(prepare_database):
    """Перед каждым тестом: очистить таблицы и сбросить нумерацию id."""
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def client():
    """Клиент для отправки запросов к API."""
    with TestClient(app) as test_client:
        yield test_client


# ---------- готовые записи для тестов ----------

@pytest.fixture
def user(client):
    response = client.post(
        "/v1/users", json={"email": "anna@example.com", "display_name": "Анна"}
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def project(client):
    response = client.post("/v1/projects", json={"name": "Курсовой проект"})
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def label(client):
    response = client.post("/v1/labels", json={"name": "backend"})
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def task(client, project, user, label):
    response = client.post(
        "/v1/tasks",
        json={
            "project_id": project["id"],
            "assignee_id": user["id"],
            "label_id": label["id"],
            "title": "Сделать API",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def comment(client, task, user):
    response = client.post(
        "/v1/comments",
        json={"task_id": task["id"], "author_id": user["id"], "body": "Начала работу"},
    )
    assert response.status_code == 201
    return response.json()