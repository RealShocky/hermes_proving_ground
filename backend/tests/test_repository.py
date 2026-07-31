from __future__ import annotations

import pytest

from app.repository import (
    TaskAlreadyExistsError,
    TaskNotFoundError,
    TaskRepository,
)
from app.tasks import Task, TaskTransitionError


def _task(id: str, title: str = "Test task", status: str = "todo") -> Task:
    return Task(id=id, title=title, status=status)


# -- create --


def test_create_returns_the_task() -> None:
    repo = TaskRepository()
    task = _task("t1")

    result = repo.create(task)

    assert result is task
    assert result.id == "t1"
    assert repo.count() == 1


def test_create_rejects_duplicate_id() -> None:
    repo = TaskRepository()
    t1 = _task("t1", "First")
    t2 = _task("t1", "Second")

    repo.create(t1)

    with pytest.raises(TaskAlreadyExistsError, match="already exists"):
        repo.create(t2)


def test_create_multiple_tasks() -> None:
    repo = TaskRepository()

    repo.create(_task("t1", "Alpha"))
    repo.create(_task("t2", "Beta"))
    repo.create(_task("t3", "Gamma"))

    assert repo.count() == 3


# -- get --


def test_get_returns_existing_task() -> None:
    repo = TaskRepository()
    task = _task("t1", "Find me")
    repo.create(task)

    found = repo.get("t1")

    assert found.id == "t1"
    assert found.title == "Find me"


def test_get_raises_on_missing_task() -> None:
    repo = TaskRepository()

    with pytest.raises(TaskNotFoundError, match="not found"):
        repo.get("no-such-id")


# -- update --


def test_update_status() -> None:
    repo = TaskRepository()
    repo.create(_task("t1", "Pending", "todo"))

    updated = repo.update("t1", status="in_progress")

    assert updated.status == "in_progress"
    assert updated.title == "Pending"
    assert repo.get("t1").status == "in_progress"


def test_update_title() -> None:
    repo = TaskRepository()
    repo.create(_task("t1", "Old title"))

    updated = repo.update("t1", title="New title")

    assert updated.title == "New title"
    assert updated.status == "todo"
    assert repo.get("t1").title == "New title"


def test_update_both_title_and_status() -> None:
    repo = TaskRepository()
    repo.create(_task("t1", "Old", "todo"))

    updated = repo.update("t1", title="New", status="in_progress")

    assert updated.title == "New"
    assert updated.status == "in_progress"


def test_update_preserves_created_at() -> None:
    from datetime import UTC, datetime

    created = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    task = Task(id="t1", title="Original", created_at=created)
    repo = TaskRepository()
    repo.create(task)

    updated = repo.update("t1", status="in_progress")

    assert updated.created_at == created


def test_update_raises_on_missing_task() -> None:
    repo = TaskRepository()

    with pytest.raises(TaskNotFoundError, match="not found"):
        repo.update("no-such-id", status="in_progress")


def test_update_validates_new_status() -> None:
    repo = TaskRepository()
    repo.create(_task("t1"))

    with pytest.raises(ValueError, match="invalid task status"):
        repo.update("t1", status="invalid")


def test_update_validates_new_title() -> None:
    repo = TaskRepository()
    repo.create(_task("t1"))

    with pytest.raises(ValueError, match="task title is required"):
        repo.update("t1", title="")


# -- update transition validation --


def test_update_allows_todo_to_in_progress() -> None:
    repo = TaskRepository()
    repo.create(_task("t1", "A", "todo"))

    updated = repo.update("t1", status="in_progress")

    assert updated.status == "in_progress"


def test_update_allows_in_progress_to_done() -> None:
    repo = TaskRepository()
    repo.create(_task("t1", "A", "in_progress"))

    updated = repo.update("t1", status="done")

    assert updated.status == "done"


def test_update_allows_todo_to_blocked() -> None:
    repo = TaskRepository()
    repo.create(_task("t1", "A", "todo"))

    updated = repo.update("t1", status="blocked")

    assert updated.status == "blocked"


def test_update_allows_blocked_to_in_progress() -> None:
    repo = TaskRepository()
    repo.create(_task("t1", "A", "blocked"))

    updated = repo.update("t1", status="in_progress")

    assert updated.status == "in_progress"


def test_update_allows_todo_to_done() -> None:
    repo = TaskRepository()
    repo.create(_task("t1", "A", "todo"))

    updated = repo.update("t1", status="done")

    assert updated.status == "done"


def test_update_rejects_done_to_any_status() -> None:
    repo = TaskRepository()
    repo.create(_task("t1", "A", "done"))

    for target in ("todo", "in_progress", "blocked"):
        with pytest.raises(TaskTransitionError, match="cannot transition from 'done'"):
            repo.update("t1", status=target)


def test_update_preserves_status_on_title_only_change() -> None:
    repo = TaskRepository()
    repo.create(_task("t1", "Original", "in_progress"))

    updated = repo.update("t1", title="Updated")

    assert updated.title == "Updated"
    assert updated.status == "in_progress"


# -- list_tasks --


def test_list_empty() -> None:
    repo = TaskRepository()

    assert repo.list_tasks() == []


def test_list_all_tasks() -> None:
    repo = TaskRepository()
    repo.create(_task("t1", "A", "todo"))
    repo.create(_task("t2", "B", "done"))
    repo.create(_task("t3", "C", "in_progress"))

    tasks = repo.list_tasks()

    assert len(tasks) == 3
    assert [t.id for t in tasks] == ["t1", "t2", "t3"]


def test_list_filtered_by_status() -> None:
    repo = TaskRepository()
    repo.create(_task("t1", "A", "todo"))
    repo.create(_task("t2", "B", "done"))
    repo.create(_task("t3", "C", "todo"))
    repo.create(_task("t4", "D", "done"))

    tasks = repo.list_tasks(status="todo")

    assert len(tasks) == 2
    assert all(t.status == "todo" for t in tasks)


def test_list_filtered_no_matches() -> None:
    repo = TaskRepository()
    repo.create(_task("t1", "A", "todo"))

    tasks = repo.list_tasks(status="blocked")

    assert tasks == []


# -- count --


def test_count_starts_at_zero() -> None:
    repo = TaskRepository()
    assert repo.count() == 0


def test_count_increments_on_create() -> None:
    repo = TaskRepository()
    repo.create(_task("t1"))
    assert repo.count() == 1
    repo.create(_task("t2"))
    assert repo.count() == 2


# -- integration: full workflow --


def test_full_create_get_update_list_workflow() -> None:
    repo = TaskRepository()

    # Create
    task = repo.create(_task("t1", "Write tests", "todo"))
    assert task.status == "todo"

    # Get
    found = repo.get("t1")
    assert found.title == "Write tests"

    # Update with valid transition
    updated = repo.update("t1", status="in_progress")
    assert updated.status == "in_progress"

    # List
    all_tasks = repo.list_tasks()
    assert len(all_tasks) == 1

    done_list = repo.list_tasks(status="in_progress")
    assert len(done_list) == 1
    assert done_list[0].id == "t1"
