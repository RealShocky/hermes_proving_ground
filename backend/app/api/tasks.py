from __future__ import annotations

from typing import Sequence

from app.tasks import Task


def list_tasks_payload(tasks: Sequence[Task]) -> list[dict[str, str]]:
    """Convert a sequence of tasks to a JSON-serializable list of dicts."""
    return [task.to_dict() for task in tasks]

