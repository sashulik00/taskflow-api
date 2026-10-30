import pytest


def test_create_comment(client, task, user):
    response = client.post(
        "/v1/comments",
        json={"task_id": task["id"], "author_id": user["id"], "body": "Готово"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["task_id"] == task["id"]
    assert data["author_id"] == user["id"]
    assert data["body"] == "Готово"
    assert "created_at" in data


@pytest.mark.parametrize("body", ["", "   "])
def test_create_comment_with_blank_body(client, task, user, body):
    response = client.post(
        "/v1/comments",
        json={"task_id": task["id"], "author_id": user["id"], "body": body},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"author_id": 1, "body": "Без задачи"},
        {"task_id": 1, "body": "Без автора"},
        {"task_id": 1, "author_id": 1},
        {"id": 5, "task_id": 1, "author_id": 1, "body": "С id"},
    ],
)
def test_create_comment_with_invalid_data(client, task, payload):
    response = client.post("/v1/comments", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["task_id", "author_id"])
def test_create_comment_with_missing_reference(client, task, user, field):
    payload = {"task_id": task["id"], "author_id": user["id"], "body": "Текст"}
    payload[field] = 999

    response = client.post("/v1/comments", json=payload)

    assert response.status_code == 409


def test_list_comments_with_task_filter(client, project, user, comment):
    other_task = client.post(
        "/v1/tasks", json={"project_id": project["id"], "title": "Другая задача"}
    ).json()
    other_comment = client.post(
        "/v1/comments",
        json={"task_id": other_task["id"], "author_id": user["id"], "body": "Ещё"},
    ).json()

    all_comments = client.get("/v1/comments").json()
    filtered = client.get("/v1/comments", params={"task_id": other_task["id"]}).json()

    assert all_comments == [comment, other_comment]
    assert filtered == [other_comment]


def test_list_comments_for_task_without_comments(client, task):
    response = client.get("/v1/comments", params={"task_id": task["id"]})

    assert response.status_code == 200
    assert response.json() == []


def test_get_comment(client, comment):
    response = client.get(f"/v1/comments/{comment['id']}")

    assert response.status_code == 200
    assert response.json() == comment


def test_get_missing_comment(client):
    response = client.get("/v1/comments/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Comment not found"


def test_update_comment_body(client, comment):
    response = client.patch(f"/v1/comments/{comment['id']}", json={"body": "Исправила"})

    assert response.status_code == 200
    assert response.json()["body"] == "Исправила"
    assert response.json()["task_id"] == comment["task_id"]


@pytest.mark.parametrize(
    "payload",
    [
        {"body": "   "},
        {"body": None},
        {"task_id": 2},
        {"author_id": 2},
    ],
)
def test_update_comment_with_invalid_data(client, comment, payload):
    response = client.patch(f"/v1/comments/{comment['id']}", json=payload)

    assert response.status_code == 422


def test_update_missing_comment(client):
    response = client.patch("/v1/comments/999", json={"body": "Текст"})

    assert response.status_code == 404


def test_delete_comment(client, comment):
    response = client.delete(f"/v1/comments/{comment['id']}")

    assert response.status_code == 204
    assert client.get(f"/v1/comments/{comment['id']}").status_code == 404


def test_delete_missing_comment(client):
    response = client.delete("/v1/comments/999")

    assert response.status_code == 404