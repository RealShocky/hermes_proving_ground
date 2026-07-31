from __future__ import annotations

from app.core import health, health_payload


def test_health_returns_ok() -> None:
    current = health()

    assert current.status == "ok"
    assert current.app == "Hermes Proving Ground"
    assert current.version


def test_health_payload_is_json_ready() -> None:
    assert health_payload() == {
        "status": "ok",
        "app": "Hermes Proving Ground",
        "version": "0.1.0",
    }
