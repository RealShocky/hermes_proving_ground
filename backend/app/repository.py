from __future__ import annotations

from typing import Sequence

from app.tasks import Task, validate_transition


class TaskNotFoundError(ValueError):
    """Raised when a requested task id does not exist in the repository."""
    pass


class TaskAlreadyExistsError(ValueError):
    """Raised when trying to create a task with an id that already exists."""
    pass


class TaskRepository:
    """In-memory task repository with create, list, get, and update operations."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def create(self, task: Task) -> Task:
        """Store a new task. Raises TaskAlreadyExistsError if id is duplicated."""
        if task.id in self._tasks:
            raise TaskAlreadyExistsError(f"task {task.id!r} already exists")
        self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Task:
        """Retrieve a task by id. Raises TaskNotFoundError if missing."""
        try:
            return self._tasks[task_id]
        except KeyError:
            raise TaskNotFoundError(f"task {task_id!r} not found")

    def update(self, task_id: str, title: str | None = None, status: str | None = None) -> Task:
        """Update title and/or status of an existing task.

        Returns the updated task. Raises TaskNotFoundError if the id does not exist.
        Validation errors are raised by the Task dataclass itself.
        Status transitions are validated against VALID_TRANSITIONS rules.
        """
        current = self.get(task_id)

        if status is not None:
            validate_transition(current.status, status)

        new_title = title if title is not None else current.title
        new_status = status if status is not None else current.status

        updated = Task(
            id=current.id,
            title=new_title,
            status=new_status,
            created_at=current.created_at,
        )
        self._tasks[task_id] = updated
        return updated

    def list_tasks(self, status: str | None = None) -> Sequence[Task]:
        """Return all tasks, optionally filtered by status."""
        if status is None:
            return list(self._tasks.values())
        return [t for t in self._tasks.values() if t.status == status]

    def count(self) -> int:
        """Return total number of tasks in the repository."""
        return len(self._tasks)
