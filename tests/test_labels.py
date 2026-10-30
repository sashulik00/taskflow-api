import pytest


def test_create_label_with_default_color(client):
    response = client.post("/v1/labels", json={"name": "bug"})

    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "bug", "color": "#6b7280"}


def test_create_label_with_custom_color(client):
    response = client.post("/v1/labels", json={"name": "bug", "color": "#FF0000"})

    assert response.status_code == 201
    assert response.json()["color"] == "#FF0000"


def test_create_label_with_duplicate_name(client, label):
    response = client.post("/v1/labels", json={"name": label["name"]})

    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": ""},
        {"name": "x" * 65},
        {"name": "bug", "color": "red"},
        {"name": "bug", "color": "#12345"},
        {"name": "bug", "color": "#GGGGGG"},
        {"name": "bug", "color": "123456"},
    ],
)
def test_create_label_with_invalid_data(client, payload):
    response = client.post("/v1/labels", json=payload)

    assert response.status_code == 422


def test_list_labels(client, label):
    response = client.get("/v1/labels")

    assert response.status_code == 200
    assert response.json() == [label]


def test_get_label(client, label):
    response = client.get(f"/v1/labels/{label['id']}")

    assert response.status_code == 200
    assert response.json() == label


def test_get_missing_label(client):
    response = client.get("/v1/labels/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Label not found"


def test_update_label_color(client, label):
    response = client.patch(f"/v1/labels/{label['id']}", json={"color": "#00ff00"})

    assert response.status_code == 200
    assert response.json()["color"] == "#00ff00"
    assert response.json()["name"] == label["name"]


def test_update_label_with_duplicate_name(client, label):
    other = client.post("/v1/labels", json={"name": "frontend"}).json()

    response = client.patch(f"/v1/labels/{other['id']}", json={"name": label["name"]})

    assert response.status_code == 409


def test_update_label_with_invalid_color(client, label):
    response = client.patch(f"/v1/labels/{label['id']}", json={"color": "green"})

    assert response.status_code == 422


def test_update_missing_label(client):
    response = client.patch("/v1/labels/999", json={"name": "bug"})

    assert response.status_code == 404


def test_delete_label(client, label):
    response = client.delete(f"/v1/labels/{label['id']}")

    assert response.status_code == 204
    assert client.get(f"/v1/labels/{label['id']}").status_code == 404


def test_delete_missing_label(client):
    response = client.delete("/v1/labels/999")

    assert response.status_code == 404


def test_delete_label_clears_task_label(client, label, task):
    response = client.delete(f"/v1/labels/{label['id']}")

    assert response.status_code == 204
    assert client.get(f"/v1/tasks/{task['id']}").json()["label_id"] is None