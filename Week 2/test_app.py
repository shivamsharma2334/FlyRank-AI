from fastapi.testclient import TestClient
from app import app, tasks

client = TestClient(app)


def reset_tasks():
    tasks.clear()
    tasks.extend([
        {"id": 1, "title": "Learn HTTP", "done": False},
        {"id": 2, "title": "Build CRUD API", "done": False},
        {"id": 3, "title": "Test with Swagger", "done": True},
    ])


def setup_function():
    reset_tasks()


def test_root_and_health():
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}


def test_read_all_and_single_task():
    assert client.get("/tasks").status_code == 200
    assert client.get("/tasks/1").json()["title"] == "Learn HTTP"
    assert client.get("/tasks/99").status_code == 404


def test_create_validation_and_create():
    bad = client.post("/tasks", json={})
    assert bad.status_code == 400

    response = client.post("/tasks", json={"title": "Buy milk"})
    assert response.status_code == 201
    assert response.json()["title"] == "Buy milk"
    assert response.json()["done"] is False


def test_update():
    response = client.put("/tasks/1", json={"done": True})
    assert response.status_code == 200
    assert response.json()["done"] is True

    bad = client.put("/tasks/1", json={})
    assert bad.status_code == 400
    assert client.put("/tasks/99", json={"done": True}).status_code == 404


def test_delete():
    response = client.delete("/tasks/2")
    assert response.status_code == 204
    assert client.get("/tasks/2").status_code == 404
    assert client.delete("/tasks/99").status_code == 404
