from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.tasks import Task, VALID_TASK_STATUSES


def test_task_defaults_to_todo_with_generated_id() -> None:
    task = Task(title="Write focused tests")

    assert task.id
    assert task.title == "Write focused tests"
    assert task.status == "todo"
    assert task.created_at.tzinfo == UTC


def test_task_normalizes_title_status_and_created_at() -> None:
    created_at = datetime(2026, 7, 30, 12, 0, 0)

    task = Task(id=" task-1 ", title="  Ship benchmark  ", status=" DONE ", created_at=created_at)

    assert task.id == "task-1"
    assert task.title == "Ship benchmark"
    assert task.status == "done"
    assert task.created_at == datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)


def test_task_rejects_empty_title() -> None:
    with pytest.raises(ValueError, match="task title is required"):
        Task(title=" ")


def test_task_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="invalid task status"):
        Task(title="Write docs", status="waiting")


def test_task_rejects_empty_id() -> None:
    with pytest.raises(ValueError, match="task id is required"):
        Task(id=" ", title="Write docs")


def test_task_round_trips_to_dict() -> None:
    created_at = datetime(2026, 7, 30, 12, 30, 0, tzinfo=UTC)
    original = Task(id="task-1", title="Round trip", status="blocked", created_at=created_at)

    restored = Task.from_dict(original.to_dict())

    assert restored == original
    assert restored.to_dict() == {
        "id": "task-1",
        "title": "Round trip",
        "status": "blocked",
        "created_at": "2026-07-30T12:30:00Z",
    }


def test_valid_statuses_are_intentional() -> None:
    assert VALID_TASK_STATUSES == frozenset({"todo", "in_progress", "blocked", "done"})
