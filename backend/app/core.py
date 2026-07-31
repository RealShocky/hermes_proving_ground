from __future__ import annotations

from dataclasses import dataclass

from app import APP_NAME, APP_VERSION


@dataclass(frozen=True)
class Health:
    status: str
    app: str
    version: str


def health() -> Health:
    return Health(status="ok", app=APP_NAME, version=APP_VERSION)


def health_payload() -> dict[str, str]:
    current = health()
    return {
        "status": current.status,
        "app": current.app,
        "version": current.version,
    }
