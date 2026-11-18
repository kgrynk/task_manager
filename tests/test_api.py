import pytest
from fastapi.testclient import TestClient

from backend.main import create_app

TASKS = "/api/tasks"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "tasks.sqlite3")) as client:
        yield client


def test_crud_and_filter(client):
    assert client.get(TASKS).json() == []
    response = client.post(TASKS, json={"title": "  Write a test  "})
    assert response.status_code == 201
    task = response.json()
    assert task == {"id": task["id"], "title": "Write a test", "description": "", "status": "todo"}
    url = f'{TASKS}/{task["id"]}'
    assert client.get(url).json() == task

    another = client.post(TASKS, json={"title": "Second task", "status": "in_progress"}).json()
    updated_data = {"title": "Review the test", "description": "After changes", "status": "done"}
    response = client.put(url, json=updated_data)
    assert response.status_code == 200
    updated = {"id": task["id"], **updated_data}
    assert response.json() == updated
    assert client.get(TASKS).json() == [another, updated]
    assert client.get(TASKS, params={"status": "done"}).json() == [updated]
    assert client.get(TASKS, params={"status": "todo"}).json() == []

    response = client.delete(url)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(TASKS).json() == [another]
    assert client.get(url).status_code == 404
    assert client.put(url, json=updated_data).status_code == 404
    assert client.delete(url).status_code == 404


@pytest.mark.parametrize("data", [
    {},
    {"title": "   "},
    {"title": "x" * 121},
    {"title": "Task", "description": "x" * 1001},
    {"title": "Task", "status": "unknown"},
])
def test_rejects_invalid_task(client, data):
    assert client.post(TASKS, json=data).status_code == 422
    assert client.get(TASKS).json() == []


def test_rejects_invalid_filter_and_id(client):
    assert client.get(TASKS, params={"status": "unknown"}).status_code == 422
    assert client.get(f"{TASKS}/0").status_code == 422


def test_tasks_survive_restart(tmp_path):
    database = tmp_path / "tasks.sqlite3"
    with TestClient(create_app(database)) as client:
        created = client.post(TASKS, json={"title": "Keep this task"}).json()
    with TestClient(create_app(database)) as client:
        assert client.get(TASKS).json() == [created]
