from __future__ import annotations

from app.core import (
    health,
    health_payload,
    health_summary,
    health_summary_payload,
)
from app.tasks import Task


def test_health_returns_ok() -> None:
    current = health()

    assert current.status == "ok"
    assert current.app == "Hermes Proving Ground"
    assert current.version


def test_health_payload_is_json_ready() -> None:
    assert health_payload() == {
        "status": "ok",
        "app": "Hermes Proving Ground",
        "version": "0.1.0",
    }


def test_health_summary_empty_list() -> None:
    summary = health_summary([])

    assert summary.total == 0
    assert summary.done == 0


def test_health_summary_all_done() -> None:
    tasks = [
        Task(id="t1", title="A", status="done"),
        Task(id="t2", title="B", status="done"),
    ]

    summary = health_summary(tasks)

    assert summary.total == 2
    assert summary.done == 2


def test_health_summary_mixed_statuses() -> None:
    tasks = [
        Task(id="t1", title="A", status="todo"),
        Task(id="t2", title="B", status="in_progress"),
        Task(id="t3", title="C", status="done"),
        Task(id="t4", title="D", status="blocked"),
        Task(id="t5", title="E", status="done"),
    ]

    summary = health_summary(tasks)

    assert summary.total == 5
    assert summary.done == 2


def test_health_summary_no_done() -> None:
    tasks = [
        Task(id="t1", title="A", status="todo"),
        Task(id="t2", title="B", status="in_progress"),
    ]

    summary = health_summary(tasks)

    assert summary.total == 2
    assert summary.done == 0


def test_health_summary_payload() -> None:
    tasks = [
        Task(id="t1", title="A", status="todo"),
        Task(id="t2", title="B", status="done"),
    ]

    payload = health_summary_payload(tasks)

    assert payload == {"total": 2, "done": 1}
