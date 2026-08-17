from __future__ import annotations

"""Focused tests for the SQLite persistence adapter.

All tests run against in-memory SQLite or temporary files; no external
database server is required.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.sqlite_adapter import SqliteAdapter
from app.schema import TASKS_TABLE
from app.tasks import Task, TaskTransitionError
from app.repository import TaskAlreadyExistsError, TaskNotFoundError


def _task(id: str, title: str = "Test task", status: str = "todo") -> Task:
    return Task(id=id, title=title, status=status)


# -- constructor / initialization --


def test_adapter_starts_empty_on_memory_db() -> None:
    adapter = SqliteAdapter(":memory:")

    assert adapter.count() == 0
    assert list(adapter.list_tasks()) == []
    adapter.close()


def test_adapter_creates_file_with_schema(tmp_path: Path) -> None:
    db_file = tmp_path / "tasks.db"

    adapter = SqliteAdapter(db_file)
    assert adapter.count() == 0
    assert db_file.exists()
    adapter.close()


def test_adapter_opens_nested_file_path(tmp_path: Path) -> None:
    db_file = tmp_path / "nested" / "dir" / "tasks.db"

    adapter = SqliteAdapter(db_file)
    assert adapter.count() == 0
    adapter.close()


def test_adapter_rejects_invalid_status_on_load(tmp_path: Path) -> None:
    db_file = tmp_path / "tasks.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        f"CREATE TABLE {TASKS_TABLE} "
        "(id TEXT PRIMARY KEY, title TEXT NOT NULL, "
        "status TEXT NOT NULL, created_at TEXT NOT NULL)"
    )
    conn.execute(
        f"INSERT INTO {TASKS_TABLE} VALUES (?, ?, ?, ?)",
        ("t1", "Bad status", "not_a_status", "2026-01-01T00:00:00Z"),
    )
    conn.execute(
        f"INSERT INTO {TASKS_TABLE} VALUES (?, ?, ?, ?)",
        ("t2", "Good status", "todo", "2026-01-01T00:00:00Z"),
    )
    conn.commit()
    conn.close()

    adapter = SqliteAdapter(db_file)
    assert adapter.count() == 1
    assert adapter.get("t2").title == "Good status"
    adapter.close()


# -- create --


def test_create_persists_task_to_db(tmp_path: Path) -> None:
    db_file = tmp_path / "tasks.db"

    adapter = SqliteAdapter(db_file)
    task = adapter.create(_task("t1", "Persist me"))
    assert task.id == "t1"
    assert adapter.count() == 1
    adapter.close()

    # Inspect the raw database file directly.
    conn = sqlite3.connect(str(db_file))
    rows = conn.execute(
        f"SELECT id, title, status FROM {TASKS_TABLE}"
    ).fetchall()
    conn.close()
    assert rows == [("t1", "Persist me", "todo")]


def test_create_multiple_tasks_persists_all(tmp_path: Path) -> None:
    db_file = tmp_path / "tasks.db"

    adapter = SqliteAdapter(db_file)
    adapter.create(_task("t1", "First"))
    adapter.create(_task("t2", "Second"))

    assert adapter.count() == 2
    adapter.close()


def test_create_rejects_duplicate_id() -> None:
    adapter = SqliteAdapter(":memory:")
    adapter.create(_task("t1"))

    with pytest.raises(TaskAlreadyExistsError, match="already exists"):
        adapter.create(_task("t1"))
    adapter.close()


# -- get --


def test_get_returns_persisted_task(tmp_path: Path) -> None:
    db_file = tmp_path / "tasks.db"

    adapter = SqliteAdapter(db_file)
    adapter.create(_task("t1", "Findable"))
    found = adapter.get("t1")
    assert found.title == "Findable"
    adapter.close()


def test_get_raises_on_missing() -> None:
    adapter = SqliteAdapter(":memory:")

    with pytest.raises(TaskNotFoundError, match="not found"):
        adapter.get("missing")
    adapter.close()


# -- update --


def test_update_persists_change(tmp_path: Path) -> None:
    db_file = tmp_path / "tasks.db"

    adapter = SqliteAdapter(db_file)
    adapter.create(_task("t1", "Original", "todo"))
    updated = adapter.update("t1", title="Updated", status="in_progress")
    assert updated.title == "Updated"
    assert updated.status == "in_progress"
    adapter.close()

    conn = sqlite3.connect(str(db_file))
    rows = conn.execute(
        f"SELECT id, title, status FROM {TASKS_TABLE}"
    ).fetchall()
    conn.close()
    assert rows == [("t1", "Updated", "in_progress")]


def test_update_preserves_created_at_in_db(tmp_path: Path) -> None:
    db_file = tmp_path / "tasks.db"
    created = datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC)
    task = Task(id="t1", title="Stable", created_at=created)

    adapter = SqliteAdapter(db_file)
    adapter.create(task)
    adapter.update("t1", status="in_progress")
    adapter.close()

    conn = sqlite3.connect(str(db_file))
    row = conn.execute(f"SELECT created_at FROM {TASKS_TABLE}").fetchone()
    conn.close()
    assert row == ("2026-06-15T10:00:00Z",)


def test_update_rejects_invalid_transition() -> None:
    adapter = SqliteAdapter(":memory:")
    adapter.create(_task("t1", "Done task", "done"))

    with pytest.raises(TaskTransitionError):
        adapter.update("t1", status="todo")
    adapter.close()


# -- list_tasks / count --


def test_list_tasks_returns_all(tmp_path: Path) -> None:
    db_file = tmp_path / "tasks.db"

    adapter = SqliteAdapter(db_file)
    adapter.create(_task("t1", "A", "todo"))
    adapter.create(_task("t2", "B", "done"))
    adapter.create(_task("t3", "C", "in_progress"))

    assert len(adapter.list_tasks()) == 3
    adapter.close()


def test_list_tasks_filtered() -> None:
    adapter = SqliteAdapter(":memory:")
    adapter.create(_task("t1", "A", "todo"))
    adapter.create(_task("t2", "B", "done"))
    adapter.create(_task("t3", "C", "todo"))

    tasks = adapter.list_tasks(status="todo")
    assert len(tasks) == 2
    assert all(t.status == "todo" for t in tasks)
    adapter.close()


# -- persistence round-trip --


def test_reload_after_reopen(tmp_path: Path) -> None:
    db_file = tmp_path / "tasks.db"

    adapter1 = SqliteAdapter(db_file)
    adapter1.create(_task("t1", "Task one", "todo"))
    adapter1.create(_task("t2", "Task two", "done"))
    adapter1.close()

    adapter2 = SqliteAdapter(db_file)
    assert adapter2.count() == 2
    assert adapter2.get("t1").title == "Task one"
    assert adapter2.get("t2").status == "done"
    adapter2.close()


def test_db_round_trip_preserves_full_row(tmp_path: Path) -> None:
    db_file = tmp_path / "tasks.db"
    created = datetime(2026, 2, 1, 9, 30, 0, tzinfo=UTC)
    task = Task(id="t42", title="Round trip", status="in_progress", created_at=created)

    adapter1 = SqliteAdapter(db_file)
    adapter1.create(task)
    adapter1.close()

    adapter2 = SqliteAdapter(db_file)
    reloaded = adapter2.get("t42")
    adapter2.close()

    assert reloaded.id == "t42"
    assert reloaded.title == "Round trip"
    assert reloaded.status == "in_progress"
    assert reloaded.created_at == created


def test_close_closes_underlying_connection(tmp_path: Path) -> None:
    db_file = tmp_path / "tasks.db"

    adapter = SqliteAdapter(db_file)
    adapter.create(_task("t1"))
    adapter.close()

    # A fresh connection sees the committed data.
    conn = sqlite3.connect(str(db_file))
    rows = conn.execute(f"SELECT COUNT(*) FROM {TASKS_TABLE}").fetchone()
    conn.close()
    assert rows == (1,)
