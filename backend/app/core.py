from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app import APP_NAME, APP_VERSION
from app.api.version import version_payload
from app.tasks import Task


@dataclass(frozen=True)
class Health:
    status: str
    app: str
    version: str


@dataclass(frozen=True)
class HealthSummary:
    total: int
    done: int


def health() -> Health:
    return Health(status="ok", app=APP_NAME, version=APP_VERSION)


def health_payload() -> dict[str, str]:
    current = health()
    return {
        "status": current.status,
        "app": current.app,
        "version": current.version,
    }


def health_summary(tasks: Sequence[Task]) -> HealthSummary:
    total = len(tasks)
    done = sum(1 for task in tasks if task.status == "done")
    return HealthSummary(total=total, done=done)


def health_summary_payload(tasks: Sequence[Task]) -> dict[str, int]:
    summary = health_summary(tasks)
    return {
        "total": summary.total,
        "done": summary.done,
    }


def healthcheck_payload(tasks: Sequence[Task]) -> dict[str, object]:
    """Compose an API healthcheck payload that includes version and task summary.

    Merges the version payload (app, version, build) with the health payload
    (status) and the task summary (total, done).
    """
    payload: dict[str, object] = dict(version_payload())
    payload.update(health_payload())
    payload["tasks"] = health_summary_payload(tasks)
    return payload
