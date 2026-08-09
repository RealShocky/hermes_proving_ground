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


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]

