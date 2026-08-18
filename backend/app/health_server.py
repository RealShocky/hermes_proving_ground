from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING

from app.api.tasks import create_task_payload, list_tasks_payload
from app.api.version import version_endpoint_body, version_payload
from app.core import health_payload, healthcheck_payload
from app.repository import TaskRepository

# Path to the static dashboard HTML relative to this file.
_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
_DASHBOARD_PATH = _FRONTEND_DIR / "dashboard.html"
_DASHBOARD_HTML = _DASHBOARD_PATH.read_text(encoding="utf-8") if _DASHBOARD_PATH.exists() else ""

if TYPE_CHECKING:
    pass


def _make_handler(repo: TaskRepository):
    """Return a Handler class bound to the given TaskRepository."""

    class Handler(BaseHTTPRequestHandler):
        repo_ref: TaskRepository  # type: ignore[misc]

        def do_GET(self) -> None:
            if self.path in {"/", "/healthz"}:
                body = json.dumps(health_payload(), sort_keys=True).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/version":
                body = version_endpoint_body()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/tasks":
                tasks = self.repo_ref.list_tasks()
                body = json.dumps(list_tasks_payload(tasks), sort_keys=True).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/healthcheck":
                tasks = self.repo_ref.list_tasks()
                body = json.dumps(healthcheck_payload(tasks), sort_keys=True).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/dashboard":
                body = _DASHBOARD_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self) -> None:
            if self.path == "/tasks":
                self._handle_create_task()
                return
            self.send_response(404)
            self.end_headers()

        def _handle_create_task(self) -> None:
            """Handle POST /tasks to create a new task."""
            from app.tasks import Task

            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                body_bytes = b""
            else:
                body_bytes = self.rfile.read(content_length)

            try:
                data = json.loads(body_bytes) if body_bytes else {}
            except json.JSONDecodeError:
                error_body = json.dumps({"error": "invalid JSON"}, sort_keys=True)
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(error_body.encode("utf-8"))))
                self.end_headers()
                self.wfile.write(error_body.encode("utf-8"))
                return

            if not isinstance(data, dict):
                error_body = json.dumps({"error": "request body must be a JSON object"}, sort_keys=True)
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(error_body.encode("utf-8"))))
                self.end_headers()
                self.wfile.write(error_body.encode("utf-8"))
                return

            title = data.get("title")
            if not title or not str(title).strip():
                error_body = json.dumps({"error": "task title is required"}, sort_keys=True)
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(error_body.encode("utf-8"))))
                self.end_headers()
                self.wfile.write(error_body.encode("utf-8"))
                return

            status = data.get("status", "todo")
            try:
                task = Task(title=str(title), status=str(status))
            except ValueError as exc:
                error_body = json.dumps({"error": str(exc)}, sort_keys=True)
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(error_body.encode("utf-8"))))
                self.end_headers()
                self.wfile.write(error_body.encode("utf-8"))
                return

            # Persist in the repository
            self.repo_ref.create(task)

            body = json.dumps(create_task_payload(task), sort_keys=True).encode("utf-8")
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    # Bind the repo as a class attribute after class creation.
    Handler.repo_ref = repo  # type: ignore[attr-defined]
    return Handler


# Default handler for backward compatibility (no repo).
Handler = _make_handler(TaskRepository())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        payload = health_payload()
        if payload["status"] != "ok":
            return 1
        print(json.dumps(payload, sort_keys=True))
        return 0

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"serving {args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
