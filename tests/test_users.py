import pytest


def test_create_user(client):
    response = client.post(
        "/v1/users", json={"email": "ivan@example.com", "display_name": "Иван"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["email"] == "ivan@example.com"
    assert data["display_name"] == "Иван"
    assert data["role"] == "operator"  # значение по умолчанию
    assert "created_at" in data


def test_create_admin(client):
    response = client.post(
        "/v1/users",
        json={"email": "boss@example.com", "display_name": "Босс", "role": "admin"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "admin"


def test_create_user_with_duplicate_email(client, user):
    response = client.post(
        "/v1/users", json={"email": user["email"], "display_name": "Двойник"}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Запись с таким уникальным значением уже существует"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "display_name": "Иван"},
        {"email": "ivan@example", "display_name": "Иван"},
        {"email": "a" * 250 + "@example.com", "display_name": "Иван"},
        {"email": "ivan@example.com", "display_name": ""},
        {"email": "ivan@example.com", "display_name": "Иван", "role": "superuser"},
        {"email": "ivan@example.com"},
        {"id": 5, "email": "ivan@example.com", "display_name": "Иван"},
    ],
)
def test_create_user_with_invalid_data(client, payload):
    response = client.post("/v1/users", json=payload)

    assert response.status_code == 422


def test_list_users(client, user):
    response = client.get("/v1/users")

    assert response.status_code == 200
    assert response.json() == [user]


def test_list_users_when_empty(client):
    response = client.get("/v1/users")

    assert response.status_code == 200
    assert response.json() == []


def test_get_user(client, user):
    response = client.get(f"/v1/users/{user['id']}")

    assert response.status_code == 200
    assert response.json() == user


def test_get_missing_user(client):
    response = client.get("/v1/users/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_update_user_changes_only_sent_fields(client, user):
    response = client.patch(f"/v1/users/{user['id']}", json={"display_name": "Анна П."})

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Анна П."
    assert data["email"] == user["email"]  # не изменилось
    assert data["role"] == user["role"]  # не изменилось


def test_update_user_role(client, user):
    response = client.patch(f"/v1/users/{user['id']}", json={"role": "admin"})

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_update_user_with_duplicate_email(client, user):
    other = client.post(
        "/v1/users", json={"email": "ivan@example.com", "display_name": "Иван"}
    ).json()

    response = client.patch(f"/v1/users/{other['id']}", json={"email": user["email"]})

    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"display_name": None},
        {"email": None},
        {"role": "superuser"},
        {"created_at": "2026-01-01T00:00:00Z"},
    ],
)
def test_update_user_with_invalid_data(client, user, payload):
    response = client.patch(f"/v1/users/{user['id']}", json=payload)

    assert response.status_code == 422


def test_update_missing_user(client):
    response = client.patch("/v1/users/999", json={"display_name": "Никто"})

    assert response.status_code == 404


def test_delete_user(client, user):
    response = client.delete(f"/v1/users/{user['id']}")

    assert response.status_code == 204
    assert response.content == b""  # без тела
    assert client.get(f"/v1/users/{user['id']}").status_code == 404


def test_delete_missing_user(client):
    response = client.delete("/v1/users/999")

    assert response.status_code == 404


def test_delete_user_with_comments_is_forbidden(client, user, comment):
    response = client.delete(f"/v1/users/{user['id']}")

    assert response.status_code == 409
    assert client.get(f"/v1/users/{user['id']}").status_code == 200  # остался


def test_delete_assignee_clears_task_assignee(client, user, task):
    response = client.delete(f"/v1/users/{user['id']}")

    assert response.status_code == 204
    assert client.get(f"/v1/tasks/{task['id']}").json()["assignee_id"] is None