from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

UserRole = Literal["operator", "admin"]
TaskStatus = Literal["open", "in_progress", "done"]
TaskPriority = Literal["low", "medium", "high"]

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


class InputSchema(BaseModel):
    """Базовая схема для входящих данных: лишние поля (например, id) запрещены."""

    model_config = ConfigDict(extra="forbid")


class ReadSchema(BaseModel):
    """Базовая схема для ответов: умеет читать данные из объектов SQLAlchemy."""

    model_config = ConfigDict(from_attributes=True)


# ---------- users ----------

class UserCreate(InputSchema):
    email: str = Field(max_length=255, pattern=EMAIL_PATTERN)
    display_name: str = Field(min_length=1, max_length=255)
    role: UserRole = "operator"


class UserUpdate(InputSchema):
    # default=None: поле можно не передавать, но передать null нельзя
    email: str = Field(default=None, max_length=255, pattern=EMAIL_PATTERN)
    display_name: str = Field(default=None, min_length=1, max_length=255)
    role: UserRole = Field(default=None)


class UserRead(ReadSchema):
    id: int
    email: str
    display_name: str
    role: str
    created_at: datetime


# ---------- projects ----------

class ProjectCreate(InputSchema):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ProjectUpdate(InputSchema):
    name: str = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class ProjectRead(ReadSchema):
    id: int
    name: str
    description: str | None
    created_at: datetime


# ---------- labels ----------

class LabelCreate(InputSchema):
    name: str = Field(min_length=1, max_length=64)
    color: str = Field(default="#6b7280", pattern=COLOR_PATTERN)


class LabelUpdate(InputSchema):
    name: str = Field(default=None, min_length=1, max_length=64)
    color: str = Field(default=None, pattern=COLOR_PATTERN)


class LabelRead(ReadSchema):
    id: int
    name: str
    color: str


# ---------- tasks ----------

class TaskCreate(InputSchema):
    project_id: int
    assignee_id: int | None = None
    label_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus = "open"
    priority: TaskPriority = "medium"


class TaskUpdate(InputSchema):
    project_id: int = Field(default=None)
    assignee_id: int | None = None
    label_id: int | None = None
    title: str = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus = Field(default=None)
    priority: TaskPriority = Field(default=None)


class TaskRead(ReadSchema):
    id: int
    project_id: int
    assignee_id: int | None
    label_id: int | None
    title: str
    description: str | None
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime


# ---------- comments ----------

def _check_not_blank(value: str | None) -> str | None:
    if value is not None and not value.strip():
        raise ValueError("Комментарий не может быть пустым")
    return value


class CommentCreate(InputSchema):
    task_id: int
    author_id: int
    body: str

    _body_not_blank = field_validator("body")(_check_not_blank)


class CommentUpdate(InputSchema):
    # у комментария меняется только текст
    body: str = Field(default=None)

    _body_not_blank = field_validator("body")(_check_not_blank)


class CommentRead(ReadSchema):
    id: int
    task_id: int
    author_id: int
    body: str
    created_at: datetime