from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from app.repository import (
    TaskAlreadyExistsError,
    TaskNotFoundError,
    TaskRepository,
)
from app.tasks import Task


class JsonFileAdapter:
    """JSON file persistence adapter for tasks.

    Wraps an in-memory TaskRepository and persists all changes to a JSON file.
    The file format is a simple JSON array of task dicts.
    """

    def __init__(self, filepath: str | Path) -> None:
        self._filepath = Path(filepath)
        self._repo = TaskRepository()
        self._load()

    # -- persistence helpers --

    def _load(self) -> None:
        """Load tasks from the JSON file, if it exists."""
        if not self._filepath.exists():
            return
        try:
            data = json.loads(self._filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(data, list):
            return
        for item in data:
            if isinstance(item, dict):
                try:
                    self._repo.create(Task.from_dict(item))
                except (ValueError, KeyError):
                    continue

    def save(self) -> None:
        """Write the current task set to the JSON file."""
        tasks_json = json.dumps(
            [task.to_dict() for task in self._repo.list_tasks()],
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        self._filepath.write_text(tasks_json + "\n", encoding="utf-8")

    # -- forwarded repository interface --

    def create(self, task: Task) -> Task:
        """Store a new task and persist to file."""
        self._repo.create(task)
        self.save()
        return task

    def get(self, task_id: str) -> Task:
        """Retrieve a task by id. Raises TaskNotFoundError if missing."""
        return self._repo.get(task_id)

    def update(self, task_id: str, title: str | None = None, status: str | None = None) -> Task:
        """Update a task and persist to file."""
        updated = self._repo.update(task_id, title=title, status=status)
        self.save()
        return updated

    def list_tasks(self, status: str | None = None) -> Sequence[Task]:
        """Return all tasks, optionally filtered by status."""
        return self._repo.list_tasks(status=status)

    def count(self) -> int:
        """Return total number of tasks."""
        return self._repo.count()
