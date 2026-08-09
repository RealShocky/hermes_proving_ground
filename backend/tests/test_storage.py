from __future__ import annotations

import json
import tempfile
from pathlib import Path
from datetime import UTC, datetime

import pytest

from app.storage import JsonFileAdapter
from app.tasks import Task
from app.repository import TaskNotFoundError


def _task(id: str, title: str = "Test task", status: str = "todo") -> Task:
    return Task(id=id, title=title, status=status)


# -- Constructor / initialization --


def test_adapter_starts_empty_when_file_missing(tmp_path: Path) -> None:
    adapter = JsonFileAdapter(tmp_path / "nonexistent.json")

    assert adapter.count() == 0
    assert adapter.list_tasks() == []


def test_adapter_loads_existing_file(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"
    file.write_text(
        json.dumps(
            [
                {"id": "t1", "title": "Loaded task", "status": "todo", "created_at": "2026-01-01T00:00:00Z"},
                {"id": "t2", "title": "Another", "status": "done", "created_at": "2026-01-01T00:00:00Z"},
            ]
        )
    )

    adapter = JsonFileAdapter(file)

    assert adapter.count() == 2
    assert adapter.get("t1").title == "Loaded task"
    assert adapter.get("t2").status == "done"


def test_adapter_ignores_malformed_json(tmp_path: Path) -> None:
    file = tmp_path / "bad.json"
    file.write_text("{not valid json\n")

    adapter = JsonFileAdapter(file)

    assert adapter.count() == 0


def test_adapter_ignores_non_list_json(tmp_path: Path) -> None:
    file = tmp_path / "obj.json"
    file.write_text('{"key": "value"}\n')

    adapter = JsonFileAdapter(file)

    assert adapter.count() == 0


def test_adapter_skips_invalid_items(tmp_path: Path) -> None:
    file = tmp_path / "mixed.json"
    file.write_text(
        json.dumps(
            [
                {"id": "t1", "title": "Good", "status": "todo", "created_at": "2026-01-01T00:00:00Z"},
                "not a dict",
                {"id": "", "title": "Bad id", "status": "todo"},
            ]
        )
    )

    adapter = JsonFileAdapter(file)

    assert adapter.count() == 1
    assert adapter.get("t1").title == "Good"


# -- create --


def test_create_persists_task(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"

    adapter = JsonFileAdapter(file)
    task = adapter.create(_task("t1", "Persist me"))

    assert task.id == "t1"
    assert adapter.count() == 1
    assert file.exists()
    data = json.loads(file.read_text())
    assert len(data) == 1
    assert data[0]["id"] == "t1"


def test_create_multiple_tasks_persists_all(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"

    adapter = JsonFileAdapter(file)
    adapter.create(_task("t1", "First"))
    adapter.create(_task("t2", "Second"))

    assert adapter.count() == 2
    data = json.loads(file.read_text())
    assert len(data) == 2


def test_create_rejects_duplicate_id(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"

    adapter = JsonFileAdapter(file)
    adapter.create(_task("t1"))

    with pytest.raises(Exception, match="already exists"):
        adapter.create(_task("t1"))


# -- get --


def test_get_returns_persisted_task(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"

    adapter = JsonFileAdapter(file)
    adapter.create(_task("t1", "Findable"))

    found = adapter.get("t1")

    assert found.title == "Findable"


def test_get_raises_on_missing(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"

    adapter = JsonFileAdapter(file)

    with pytest.raises(TaskNotFoundError, match="not found"):
        adapter.get("missing")


# -- update --


def test_update_persists_change(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"

    adapter = JsonFileAdapter(file)
    adapter.create(_task("t1", "Original", "todo"))
    updated = adapter.update("t1", title="Updated", status="in_progress")

    assert updated.title == "Updated"
    assert updated.status == "in_progress"
    data = json.loads(file.read_text())
    assert data[0]["title"] == "Updated"
    assert data[0]["status"] == "in_progress"


def test_update_preserves_created_at_in_file(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"
    created = datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC)
    task = Task(id="t1", title="Stable", created_at=created)

    adapter = JsonFileAdapter(file)
    adapter.create(task)
    adapter.update("t1", status="in_progress")

    data = json.loads(file.read_text())
    assert data[0]["created_at"] == "2026-06-15T10:00:00Z"


# -- list_tasks --


def test_list_tasks_returns_all(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"

    adapter = JsonFileAdapter(file)
    adapter.create(_task("t1", "A", "todo"))
    adapter.create(_task("t2", "B", "done"))
    adapter.create(_task("t3", "C", "in_progress"))

    tasks = adapter.list_tasks()

    assert len(tasks) == 3


def test_list_tasks_filtered(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"

    adapter = JsonFileAdapter(file)
    adapter.create(_task("t1", "A", "todo"))
    adapter.create(_task("t2", "B", "done"))
    adapter.create(_task("t3", "C", "todo"))

    tasks = adapter.list_tasks(status="todo")

    assert len(tasks) == 2
    assert all(t.status == "todo" for t in tasks)


# -- persistence round-trip --


def test_reload_after_process_restart(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"

    # First "process" creates tasks
    adapter1 = JsonFileAdapter(file)
    adapter1.create(_task("t1", "Task one", "todo"))
    adapter1.create(_task("t2", "Task two", "done"))

    # Second "process" reloads from file
    adapter2 = JsonFileAdapter(file)

    assert adapter2.count() == 2
    assert adapter2.get("t1").title == "Task one"
    assert adapter2.get("t2").status == "done"


def test_file_format_is_deterministic(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"

    adapter = JsonFileAdapter(file)
    adapter.create(_task("t1", "Alpha", "todo"))
    adapter.create(_task("t2", "Beta", "done"))

    first_read = file.read_text()

    # Re-save and compare
    adapter.save()
    second_read = file.read_text()

    assert first_read == second_read


def test_save_produces_sorted_keys(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"

    adapter = JsonFileAdapter(file)
    adapter.create(_task("t1", "Key order"))

    data = json.loads(file.read_text())
    keys = list(data[0].keys())

    assert keys == sorted(keys)
