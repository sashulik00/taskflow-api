import pytest


def test_create_task_with_defaults(client, project):
    response = client.post(
        "/v1/tasks", json={"project_id": project["id"], "title": "Купить краску"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == project["id"]
    assert data["title"] == "Купить краску"
    assert data["status"] == "open"  # по умолчанию
    assert data["priority"] == "medium"  # по умолчанию
    assert data["assignee_id"] is None
    assert data["label_id"] is None
    assert data["description"] is None
    assert "created_at" in data
    assert "updated_at" in data


def test_create_task_with_all_fields(client, project, user, label):
    response = client.post(
        "/v1/tasks",
        json={
            "project_id": project["id"],
            "assignee_id": user["id"],
            "label_id": label["id"],
            "title": "Сделать API",
            "description": "Пять ресурсов",
            "status": "in_progress",
            "priority": "high",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["assignee_id"] == user["id"]
    assert data["label_id"] == label["id"]
    assert data["status"] == "in_progress"
    assert data["priority"] == "high"


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "Без проекта"},
        {"project_id": 1},
        {"project_id": 1, "title": ""},
        {"project_id": 1, "title": "x" * 201},
        {"project_id": 1, "title": "Тест", "status": "closed"},
        {"project_id": 1, "title": "Тест", "priority": "urgent"},
        {"project_id": 1, "title": "Тест", "updated_at": "2026-01-01T00:00:00Z"},
    ],
)
def test_create_task_with_invalid_data(client, project, payload):
    response = client.post("/v1/tasks", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["project_id", "assignee_id", "label_id"])
def test_create_task_with_missing_reference(client, project, field):
    payload = {"project_id": project["id"], "title": "Тест", field: 999}

    response = client.post("/v1/tasks", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Связанная запись не найдена или запись используется в других таблицах"
    )


def create_task(client, project_id, title, status="open"):
    response = client.post(
        "/v1/tasks", json={"project_id": project_id, "title": title, "status": status}
    )
    assert response.status_code == 201
    return response.json()


def test_list_tasks_with_filters(client):
    first = client.post("/v1/projects", json={"name": "Первый"}).json()
    second = client.post("/v1/projects", json={"name": "Второй"}).json()
    open_task = create_task(client, first["id"], "Открытая")
    done_task = create_task(client, first["id"], "Готовая", status="done")
    other_task = create_task(client, second["id"], "Из другого проекта")

    all_tasks = client.get("/v1/tasks").json()
    by_project = client.get("/v1/tasks", params={"project_id": first["id"]}).json()
    by_status = client.get("/v1/tasks", params={"status": "open"}).json()
    by_both = client.get(
        "/v1/tasks", params={"project_id": first["id"], "status": "done"}
    ).json()

    assert [t["id"] for t in all_tasks] == [open_task["id"], done_task["id"], other_task["id"]]
    assert [t["id"] for t in by_project] == [open_task["id"], done_task["id"]]
    assert [t["id"] for t in by_status] == [open_task["id"], other_task["id"]]
    assert [t["id"] for t in by_both] == [done_task["id"]]


def test_list_tasks_with_no_matches(client, task):
    response = client.get("/v1/tasks", params={"status": "done"})

    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_with_invalid_status_filter(client):
    response = client.get("/v1/tasks", params={"status": "closed"})

    assert response.status_code == 422


def test_get_task(client, task):
    response = client.get(f"/v1/tasks/{task['id']}")

    assert response.status_code == 200
    assert response.json() == task


def test_get_missing_task(client):
    response = client.get("/v1/tasks/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_update_task_status_to_done(client, task):
    response = client.patch(f"/v1/tasks/{task['id']}", json={"status": "done"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["title"] == task["title"]  # не изменилось
    assert data["updated_at"] > task["updated_at"]  # время изменения обновилось


def test_update_task_can_remove_assignee_and_label(client, task):
    response = client.patch(
        f"/v1/tasks/{task['id']}", json={"assignee_id": None, "label_id": None}
    )

    assert response.status_code == 200
    assert response.json()["assignee_id"] is None
    assert response.json()["label_id"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"title": None},
        {"project_id": None},
        {"status": "closed"},
        {"priority": None},
        {"id": 5},
    ],
)
def test_update_task_with_invalid_data(client, task, payload):
    response = client.patch(f"/v1/tasks/{task['id']}", json=payload)

    assert response.status_code == 422


def test_update_task_with_missing_project(client, task):
    response = client.patch(f"/v1/tasks/{task['id']}", json={"project_id": 999})

    assert response.status_code == 409


def test_update_missing_task(client):
    response = client.patch("/v1/tasks/999", json={"status": "done"})

    assert response.status_code == 404


def test_delete_task(client, task):
    response = client.delete(f"/v1/tasks/{task['id']}")

    assert response.status_code == 204
    assert client.get(f"/v1/tasks/{task['id']}").status_code == 404


def test_delete_task_deletes_its_comments(client, task, comment):
    response = client.delete(f"/v1/tasks/{task['id']}")

    assert response.status_code == 204
    assert client.get(f"/v1/comments/{comment['id']}").status_code == 404


def test_delete_missing_task(client):
    response = client.delete("/v1/tasks/999")

    assert response.status_code == 404