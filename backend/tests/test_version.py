from __future__ import annotations

from app.api.version import version_info, version_payload


def test_version_info_returns_app_and_version() -> None:
    info = version_info()

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


def test_version_payload_has_all_keys() -> None:
    payload = version_payload()

    assert "app" in payload
    assert "version" in payload
    assert "build" in payload


def test_version_info_is_frozen() -> None:
    info = version_info()

    try:
        info.app = "changed"
        assert False, "expected FrozenInstanceError"
    except Exception:
        pass
