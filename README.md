# TaskFlow API

REST API для управления задачами команды: пользователи, проекты, метки, задачи и комментарии.

**Технологии:** Python 3.12, FastAPI, PostgreSQL 16, SQLAlchemy 2, Alembic, Docker Compose.

## Запуск

Нужен установленный Docker (Docker Desktop).

```bash
git clone https://github.com/sashulik00/taskflow-api.git
cd taskflow-api
git checkout feature/taskflow-api
cp .env.example .env
docker compose up --build
```

На Windows (PowerShell) вместо `cp` используйте `copy .env.example .env`.
Файл `.env` необязателен: без него используются значения по умолчанию.

При старте контейнер `api` дожидается готовности PostgreSQL, автоматически применяет миграции (`alembic upgrade head`) и запускает API.

После запуска доступны:

- API: http://localhost:8000
- Проверка соединения с БД: http://localhost:8000/health
- Интерактивная документация: http://localhost:8000/docs

Остановка с сохранением данных:

```bash
docker compose down
```

Полный сброс вместе с данными БД:

```bash
docker compose down -v
```

## Примеры запросов

На Windows в PowerShell пишите `curl.exe` вместо `curl`.

Проверка работы API и базы данных:

```bash
curl http://localhost:8000/health
```

Создание проекта:

```bash
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Demo project", "description": "Test project"}'
```

Создание задачи в проекте:

```bash
curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "title": "First task", "priority": "high"}'
```

Список открытых задач проекта:

```bash
curl "http://localhost:8000/v1/tasks?project_id=1&status=open"
```

Перевод задачи в статус `done`:

```bash
curl -X PATCH http://localhost:8000/v1/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

## Ресурсы API

Для каждого ресурса (`users`, `projects`, `labels`, `tasks`, `comments`) есть пять операций:

| Метод | URL | Результат |
|---|---|---|
| GET | `/v1/{resource}` | список записей |
| GET | `/v1/{resource}/{id}` | одна запись |
| POST | `/v1/{resource}` | создание (201) |
| PATCH | `/v1/{resource}/{id}` | частичное обновление (200) |
| DELETE | `/v1/{resource}/{id}` | удаление (204) |

Фильтры: `GET /v1/tasks?project_id=1&status=open`, `GET /v1/comments?task_id=1`.

Ошибки: `404` — запись не найдена, `422` — неверные входные данные, `409` — дубликат уникального значения или нарушение внешнего ключа.

## Миграции

Схема БД создаётся только миграциями Alembic. Проверка миграций внутри контейнера:

```bash
docker compose exec api alembic upgrade head
docker compose exec api alembic downgrade base
docker compose exec api alembic upgrade head
```

## Тесты

Тесты используют PostgreSQL из Docker Compose и отдельную базу `taskflow_test`, которая создаётся автоматически. Рабочие данные не затрагиваются.

```bash
docker compose up -d db
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows (PowerShell)
# source .venv/bin/activate     # Linux / macOS
pip install -r requirements-dev.txt
pytest
```

Что проверяется:

- `tests/test_migrations.py` — миграционные тесты: `upgrade` создаёт пять таблиц, `downgrade` удаляет их, правила `CASCADE`, `SET NULL` и `RESTRICT` записаны в БД;
- `tests/test_health.py`, `test_users.py`, `test_projects.py`, `test_labels.py`, `test_tasks.py`, `test_comments.py` — интеграционные тесты API через `TestClient`: успешные сценарии (200, 201, 204) и ошибки (404, 409, 422), фильтры, каскадное удаление;
- `tests/test_unit.py` — юнит-тесты отдельных функций и Pydantic-схем, включая ответ 503 при недоступной БД.

Фикстуры находятся в `tests/conftest.py`. Покрытие кода считается автоматически (`pytest-cov`); если оно ниже 100 %, запуск завершается ошибкой.

## Структура проекта

```text
app/
├── main.py          # приложение FastAPI, /health, подключение роутеров
├── config.py        # настройки из переменных окружения
├── database.py      # подключение к БД и сессии
├── models.py        # модели SQLAlchemy (5 таблиц)
├── schemas.py       # Pydantic-схемы запросов и ответов
└── routers/         # CRUD для каждого ресурса
alembic/versions/    # миграции
Dockerfile
docker-compose.yml
```