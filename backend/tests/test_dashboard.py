from __future__ import annotations

import http.client
import socket
import threading
import time

from app.health_server import Handler, ThreadingHTTPServer


def test_dashboard_endpoint_returns_html() -> None:
    server, port = _start_server()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/dashboard")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        conn.close()

        assert response.status == 200
        assert "text/html" in response.getheader("Content-Type")
        assert "Task Dashboard" in body
    finally:
        server.shutdown()


def test_dashboard_contains_task_count_elements() -> None:
    server, port = _start_server()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/dashboard")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        conn.close()

        assert "id=\"total\"" in body
        assert "id=\"todo\"" in body
        assert "id=\"in_progress\"" in body
        assert "id=\"blocked\"" in body
        assert "id=\"done\"" in body
    finally:
        server.shutdown()


def test_dashboard_html_file_exists() -> None:
    from pathlib import Path

    dashboard_path = (
        Path(__file__).resolve().parent.parent.parent / "frontend" / "dashboard.html"
    )
    assert dashboard_path.exists()
    content = dashboard_path.read_text(encoding="utf-8")
    assert "Task Dashboard" in content
    assert "DOCTYPE html" in content


def _start_server() -> tuple[ThreadingHTTPServer, int]:
    host = "127.0.0.1"
    port = _free_port()
    server = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    return server, port


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
