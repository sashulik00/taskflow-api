import pytest


def test_create_project(client):
    response = client.post(
        "/v1/projects", json={"name": "Ремонт", "description": "Список дел"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Ремонт"
    assert data["description"] == "Список дел"
    assert "created_at" in data


def test_create_project_without_description(client):
    response = client.post("/v1/projects", json={"name": "Ремонт"})

    assert response.status_code == 201
    assert response.json()["description"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": ""},
        {"name": "x" * 201},
        {"id": 5, "name": "Ремонт"},
    ],
)
def test_create_project_with_invalid_data(client, payload):
    response = client.post("/v1/projects", json=payload)

    assert response.status_code == 422


def test_list_projects(client, project):
    response = client.get("/v1/projects")

    assert response.status_code == 200
    assert response.json() == [project]


def test_get_project(client, project):
    response = client.get(f"/v1/projects/{project['id']}")

    assert response.status_code == 200
    assert response.json() == project


def test_get_missing_project(client):
    response = client.get("/v1/projects/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_update_project_name(client, project):
    response = client.patch(f"/v1/projects/{project['id']}", json={"name": "Диплом"})

    assert response.status_code == 200
    assert response.json()["name"] == "Диплом"


def test_update_project_can_clear_description(client):
    project = client.post(
        "/v1/projects", json={"name": "Ремонт", "description": "Список дел"}
    ).json()

    response = client.patch(f"/v1/projects/{project['id']}", json={"description": None})

    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["name"] == "Ремонт"


def test_update_project_with_null_name(client, project):
    response = client.patch(f"/v1/projects/{project['id']}", json={"name": None})

    assert response.status_code == 422


def test_update_missing_project(client):
    response = client.patch("/v1/projects/999", json={"name": "Диплом"})

    assert response.status_code == 404


def test_delete_project(client, project):
    response = client.delete(f"/v1/projects/{project['id']}")

    assert response.status_code == 204
    assert client.get(f"/v1/projects/{project['id']}").status_code == 404


def test_delete_missing_project(client):
    response = client.delete("/v1/projects/999")

    assert response.status_code == 404


def test_delete_project_deletes_its_tasks_and_comments(client, project, task, comment):
    response = client.delete(f"/v1/projects/{project['id']}")

    assert response.status_code == 204
    assert client.get(f"/v1/tasks/{task['id']}").status_code == 404
    assert client.get(f"/v1/comments/{comment['id']}").status_code == 404