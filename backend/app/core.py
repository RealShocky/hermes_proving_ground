from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app import APP_NAME, APP_VERSION
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
