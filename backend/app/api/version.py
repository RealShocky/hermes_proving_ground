from __future__ import annotations

from dataclasses import dataclass, field

from app import APP_NAME, APP_VERSION


@dataclass(frozen=True)
class VersionInfo:
    app: str
    version: str
    build: str = field(default="")


def version_info() -> VersionInfo:
    return VersionInfo(app=APP_NAME, version=APP_VERSION)


def version_payload() -> dict[str, str]:
    info = version_info()
    return {
        "app": info.app,
        "version": info.version,
        "build": info.build,
    }
