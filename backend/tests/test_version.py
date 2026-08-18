from __future__ import annotations

import http.client
import json
import socket
import threading
import time

from app.api.version import (
    VersionInfo,
    version_endpoint_body,
    version_info,
    version_payload,
)
from app.health_server import Handler, ThreadingHTTPServer


def test_version_info_returns_app_and_version() -> None:
    info = version_info()

    assert isinstance(info, VersionInfo)
    assert info.app == "Hermes Proving Ground"
    assert info.version == "0.1.0"
    assert info.build == ""


def test_version_payload_is_json_ready() -> None:
    payload = version_payload()

    assert payload == {
        "app": "Hermes Proving Ground",
        "version": "0.1.0",
        "build": "",
    }
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload


def test_version_payload_has_all_keys() -> None:
    payload = version_payload()

    assert "app" in payload
    assert "version" in payload
    assert "build" in payload


def test_version_build_tracks_build_metadata(monkeypatch) -> None:
    monkeypatch.setattr("app.api.version.BUILD_METADATA", "20260818T031317Z")

    info = version_info()
    payload = version_payload()

    assert info.build == "20260818T031317Z"
    assert payload["build"] == "20260818T031317Z"

    monkeypatch.undo()
    assert version_info().build == ""


def test_version_info_is_frozen() -> None:
    info = version_info()

    try:
        info.app = "changed"
        raise AssertionError("expected frozen version info")
    except Exception:
        pass


def test_version_endpoint_returns_json() -> None:
    server, port = _start_server()
    try:
        response, data = _get_json(port, "/version")

        assert response == 200
        assert data == {
            "app": "Hermes Proving Ground",
            "version": "0.1.0",
            "build": "",
        }
    finally:
        server.shutdown()


def test_version_endpoint_unknown_path_returns_404() -> None:
    server, port = _start_server()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/unknown")
        response = conn.getresponse()
        response.read()
        conn.close()

        assert response.status == 404
    finally:
        server.shutdown()


def test_version_endpoint_body_matches_live_endpoint() -> None:
    expected = json.dumps(version_payload(), sort_keys=True).encode("utf-8")

    assert version_endpoint_body() == expected
    assert json.loads(expected.decode("utf-8")) == version_payload()

    server, port = _start_server()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/version")
        response = conn.getresponse()
        body = response.read()
        conn.close()

        assert response.status == 200
        assert body == version_endpoint_body()
    finally:
        server.shutdown()


def _start_server() -> tuple[ThreadingHTTPServer, int]:
    host = "127.0.0.1"
    port = _free_port()
    server = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    return server, port


def _get_json(port: int, path: str) -> tuple[int, dict[str, str]]:
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
