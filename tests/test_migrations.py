from alembic import command
from sqlalchemy import inspect

from app.database import engine

APP_TABLES = {"users", "projects", "labels", "tasks", "comments"}


def get_tables() -> set[str]:
    return set(inspect(engine).get_table_names())


def get_delete_rules(table: str) -> dict[str, str]:
    """Вернуть правило ondelete для каждого внешнего ключа таблицы."""
    foreign_keys = inspect(engine).get_foreign_keys(table)
    return {
        fk["constrained_columns"][0]: fk["options"].get("ondelete")
        for fk in foreign_keys
    }


def test_upgrade_creates_exactly_five_tables():
    assert get_tables() - {"alembic_version"} == APP_TABLES


def test_downgrade_removes_tables_and_upgrade_restores_them(alembic_config):
    command.downgrade(alembic_config, "base")
    assert get_tables() & APP_TABLES == set()

    command.upgrade(alembic_config, "head")
    assert get_tables() - {"alembic_version"} == APP_TABLES


def test_repeated_upgrade_does_nothing(alembic_config):
    command.upgrade(alembic_config, "head")
    assert get_tables() - {"alembic_version"} == APP_TABLES


def test_task_foreign_key_rules():
    assert get_delete_rules("tasks") == {
        "project_id": "CASCADE",
        "assignee_id": "SET NULL",
        "label_id": "SET NULL",
    }


def test_comment_foreign_key_rules():
    assert get_delete_rules("comments") == {
        "task_id": "CASCADE",
        "author_id": "RESTRICT",
    }