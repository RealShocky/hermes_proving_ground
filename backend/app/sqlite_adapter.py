from __future__ import annotations

"""SQLite persistence adapter for tasks.

Wraps an in-memory TaskRepository backed by a SQLite database. The schema
is created (or migrated) from app.migrations on first use, and every
mutating operation persists to the database with a single INSERT or
UPDATE. Status transition validation is inherited from the repository,
matching the behaviour of JsonFileAdapter.
"""

import sqlite3
from pathlib import Path
from typing import Sequence

from app.migrations import ensure_schema
from app.repository import TaskRepository
from app.schema import TASKS_TABLE, TASK_COLUMNS
from app.tasks import Task

# Column names in the order used by the SELECT/INSERT/UPDATE statements.
_TASK_ROW_COLUMNS = tuple(name for name, _ in TASK_COLUMNS)


def _task_from_row(row: tuple[str, str, str, str]) -> Task:
    payload = dict(zip(_TASK_ROW_COLUMNS, row))
    return Task.from_dict(payload)


class SqliteAdapter:
    """SQLite persistence adapter for tasks.

    Exposes the same create / get / update / list_tasks / count surface as
    JsonFileAdapter, persisting to a SQLite database instead of a JSON file.
    The ``db_path`` may be any file path or the special value ":memory:".
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = db_path if isinstance(db_path, Path) else Path(str(db_path))
        self._repo = TaskRepository()
        self._connection: sqlite3.Connection | None = None
        conn = self.connection()
        ensure_schema(conn)
        self._load()

    @property
    def db_path(self) -> str:
        """The database path as passed to the constructor."""
        return str(self._db_path)

    def connection(self) -> sqlite3.Connection:
        """Return the live SQLite connection, opening it on first use."""
        if self._connection is None:
            if self._db_path != Path(":memory:"):
                self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(str(self._db_path))
        return self._connection

    def close(self) -> None:
        """Close the underlying connection if it is open."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    # -- persistence helpers --

    def _load(self) -> None:
        """Load tasks from the database into the in-memory repository."""
        conn = self.connection()
        cursor = conn.execute(
            f"SELECT {', '.join(_TASK_ROW_COLUMNS)} FROM {TASKS_TABLE}"
        )
        for row in cursor.fetchall():
            try:
                self._repo.create(_task_from_row(row))
            except (ValueError, KeyError):
                continue

    def _insert(self, task: Task) -> None:
        data = task.to_dict()
        conn = self.connection()
        with conn:
            conn.execute(
                f"INSERT INTO {TASKS_TABLE} ({', '.join(_TASK_ROW_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in _TASK_ROW_COLUMNS)})",
                tuple(data[c] for c in _TASK_ROW_COLUMNS),
            )

    def _update(self, task: Task) -> None:
        data = task.to_dict()
        conn = self.connection()
        with conn:
            conn.execute(
                f"UPDATE {TASKS_TABLE} SET title = ?, status = ?, created_at = ? "
                "WHERE id = ?",
                (data["title"], data["status"], data["created_at"], task.id),
            )

    # -- forwarded repository interface --

    def create(self, task: Task) -> Task:
        """Store a new task and persist to the database."""
        self._repo.create(task)
        self._insert(task)
        return task

    def get(self, task_id: str) -> Task:
        """Retrieve a task by id. Raises TaskNotFoundError if missing."""
        return self._repo.get(task_id)

    def update(self, task_id: str, title: str | None = None, status: str | None = None) -> Task:
        """Update a task and persist to the database."""
        updated = self._repo.update(task_id, title=title, status=status)
        self._update(updated)
        return updated

    def list_tasks(self, status: str | None = None) -> Sequence[Task]:
        """Return all tasks, optionally filtered by status."""
        return self._repo.list_tasks(status=status)

    def count(self) -> int:
        """Return total number of tasks."""
        return self._repo.count()
