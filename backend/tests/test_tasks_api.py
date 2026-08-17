from __future__ import annotations

import http.client
import json
import socket
import threading
import time

from app.health_server import ThreadingHTTPServer, _make_handler
from app.repository import TaskRepository
from app.tasks import Task


def test_tasks_endpoint_returns_empty_list() -> None:
    """GET /tasks returns an empty JSON array when no tasks exist."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        response, data = _get_json(port, "/tasks")

        assert response == 200
        assert data == []
    finally:
        server.shutdown()


def test_tasks_endpoint_returns_all_tasks() -> None:
    """GET /tasks returns all tasks as a JSON array of task dicts."""
    repo = TaskRepository()
    repo.create(Task(id="a1", title="First", status="todo"))
    repo.create(Task(id="b2", title="Second", status="done"))
    server, port = _start_server(repo)
    try:
        response, data = _get_json(port, "/tasks")

        assert response == 200
        assert len(data) == 2
        ids = {item["id"] for item in data}
        assert ids == {"a1", "b2"}
        for item in data:
            assert "id" in item
            assert "title" in item
            assert "status" in item
            assert "created_at" in item
    finally:
        server.shutdown()


def test_tasks_endpoint_returns_correct_fields() -> None:
    """Each task in the response has the expected fields."""
    repo = TaskRepository()
    repo.create(Task(id="t1", title="Test Task", status="in_progress"))
    server, port = _start_server(repo)
    try:
        response, data = _get_json(port, "/tasks")

        assert response == 200
        assert len(data) == 1
        task = data[0]
        assert task["id"] == "t1"
        assert task["title"] == "Test Task"
        assert task["status"] == "in_progress"
        assert "created_at" in task
    finally:
        server.shutdown()


def test_tasks_endpoint_unknown_path_returns_404() -> None:
    """GET /unknown returns 404 on a tasks-enabled server."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/unknown")
        response = conn.getresponse()
        response.read()
        conn.close()

        assert response.status == 404
    finally:
        server.shutdown()


# -- POST /tests tests --


def test_create_task_returns_201() -> None:
    """POST /tasks with valid JSON creates a task and returns 201."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        payload = {"title": "New Task"}
        status, data = _post_json(port, "/tasks", payload)

        assert status == 201
        assert data["title"] == "New Task"
        assert data["status"] == "todo"
        assert "id" in data
        assert "created_at" in data
    finally:
        server.shutdown()


def test_create_task_with_status() -> None:
    """POST /tasks accepts an optional status field."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        payload = {"title": "In Progress Task", "status": "in_progress"}
        status, data = _post_json(port, "/tasks", payload)

        assert status == 201
        assert data["title"] == "In Progress Task"
        assert data["status"] == "in_progress"
    finally:
        server.shutdown()


def test_create_task_persists_in_repo() -> None:
    """POST /tasks persists the task so GET /tasks returns it."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        # Create via POST
        payload = {"title": "Persisted Task"}
        status, created = _post_json(port, "/tasks", payload)
        assert status == 201

        # Verify via GET
        status, tasks = _get_json(port, "/tasks")
        assert status == 200
        assert len(tasks) == 1
        assert tasks[0]["id"] == created["id"]
        assert tasks[0]["title"] == "Persisted Task"
    finally:
        server.shutdown()


def test_create_task_missing_title_returns_400() -> None:
    """POST /tasks without a title returns 400."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        payload = {}
        status, data = _post_json(port, "/tasks", payload)

        assert status == 400
        assert "error" in data
    finally:
        server.shutdown()


def test_create_task_empty_title_returns_400() -> None:
    """POST /tasks with an empty title returns 400."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        payload = {"title": ""}
        status, data = _post_json(port, "/tasks", payload)

        assert status == 400
        assert "error" in data
    finally:
        server.shutdown()


def test_create_task_invalid_status_returns_400() -> None:
    """POST /tasks with an invalid status returns 400."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        payload = {"title": "Bad Status", "status": "invalid_status"}
        status, data = _post_json(port, "/tasks", payload)

        assert status == 400
        assert "error" in data
    finally:
        server.shutdown()


def test_create_task_invalid_json_returns_400() -> None:
    """POST /tasks with invalid JSON body returns 400."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        status, data = _post_raw(port, "/tasks", "not json at all")

        assert status == 400
        assert "error" in data
    finally:
        server.shutdown()


def test_create_task_no_body_returns_400() -> None:
    """POST /tasks with no body returns 400 (missing title)."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        status, data = _post_raw(port, "/tasks", "")

        assert status == 400
        assert "error" in data
    finally:
        server.shutdown()


def test_post_unknown_path_returns_404() -> None:
    """POST /unknown returns 404."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        status, _ = _post_raw(port, "/unknown", "{}")

        assert status == 404
    finally:
        server.shutdown()


# -- /healthcheck tests --


def test_healthcheck_endpoint_returns_version_and_task_summary() -> None:
    """GET /healthcheck returns version info plus a task summary."""
    repo = TaskRepository()
    repo.create(Task(id="h1", title="First", status="todo"))
    repo.create(Task(id="h2", title="Second", status="done"))
    repo.create(Task(id="h3", title="Third", status="in_progress"))
    server, port = _start_server(repo)
    try:
        response, data = _get_json(port, "/healthcheck")

        assert response == 200
        assert data == {
            "app": "Hermes Proving Ground",
            "version": "0.1.0",
            "build": "",
            "status": "ok",
            "tasks": {"total": 3, "done": 1},
        }
    finally:
        server.shutdown()


def test_healthcheck_endpoint_empty_repo() -> None:
    """GET /healthcheck reports a zero task summary when no tasks exist."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        response, data = _get_json(port, "/healthcheck")

        assert response == 200
        assert data["status"] == "ok"
        assert data["app"] == "Hermes Proving Ground"
        assert data["version"] == "0.1.0"
        assert data["tasks"] == {"total": 0, "done": 0}
    finally:
        server.shutdown()


def test_healthcheck_endpoint_reflects_new_task() -> None:
    """GET /healthcheck task summary updates after POST /tasks."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        status, created = _post_json(port, "/tasks", {"title": "Fresh"})
        assert status == 201

        response, data = _get_json(port, "/healthcheck")
        assert response == 200
        assert data["tasks"] == {"total": 1, "done": 0}
    finally:
        server.shutdown()


def test_healthcheck_endpoint_json_content_type() -> None:
    """GET /healthcheck responds with application/json."""
    repo = TaskRepository()
    server, port = _start_server(repo)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/healthcheck")
        response = conn.getresponse()
        response.read()
        content_type = response.getheader("Content-Type")
        conn.close()

        assert response.status == 200
        assert content_type == "application/json"
    finally:
        server.shutdown()


# -- helpers --


def _start_server(repo: TaskRepository) -> tuple[ThreadingHTTPServer, int]:
    host = "127.0.0.1"
    port = _free_port()
    Handler = _make_handler(repo)
    server = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    return server, port


def _get_json(port: int, path: str) -> tuple[int, list]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    response = conn.getresponse()
    body = response.read().decode("utf-8")
    conn.close()
    return response.status, json.loads(body)


def _post_json(
    port: int, path: str, payload: dict
) -> tuple[int, dict]:
    """Send a POST with JSON body and return (status, parsed_json)."""
    body = json.dumps(payload).encode("utf-8")
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST",
        path,
        body=body,
        headers={"Content-Type": "application/json"},
    )
    response = conn.getresponse()
    resp_body = response.read().decode("utf-8")
    conn.close()
    return response.status, json.loads(resp_body)


def _post_raw(
    port: int, path: str, raw_body: str
) -> tuple[int, dict]:
    """Send a POST with raw body and return (status, parsed_json)."""
    body = raw_body.encode("utf-8")
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST",
        path,
        body=body,
        headers={"Content-Type": "application/json"},
    )
    response = conn.getresponse()
    resp_body = response.read().decode("utf-8")
    conn.close()
    if resp_body:
        return response.status, json.loads(resp_body)
    return response.status, {}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
