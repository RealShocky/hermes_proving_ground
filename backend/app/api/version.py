from __future__ import annotations

import json
from dataclasses import dataclass

from app import APP_NAME, APP_VERSION, BUILD_METADATA


@dataclass(frozen=True)
class VersionInfo:
    app: str
    version: str
    build: str


def version_info() -> VersionInfo:
    return VersionInfo(app=APP_NAME, version=APP_VERSION, build=BUILD_METADATA)


def version_payload() -> dict[str, str]:
    info = version_info()
    return {
        "app": info.app,
        "version": info.version,
        "build": info.build,
    }


def version_endpoint_body() -> bytes:
    """Build the JSON body served by the /version endpoint."""
    return json.dumps(version_payload(), sort_keys=True).encode("utf-8")
