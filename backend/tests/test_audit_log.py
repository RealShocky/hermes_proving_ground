from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.audit_log import AuditLog, AuditLogEntry


# -- AuditLogEntry model --


def test_entry_defaults_to_generated_id_and_timestamp() -> None:
    entry = AuditLogEntry(task_id="t1", action="created")

    assert entry.entry_id
    assert entry.task_id == "t1"
    assert entry.action == "created"
    assert entry.field_name is None
    assert entry.old_value is None
    assert entry.new_value is None
    assert entry.timestamp.tzinfo == UTC


def test_entry_with_all_fields() -> None:
    entry = AuditLogEntry(
        task_id="t1",
        action="updated",
        field_name="status",
        old_value="todo",
        new_value="done",
    )

    assert entry.task_id == "t1"
    assert entry.action == "updated"
    assert entry.field_name == "status"
    assert entry.old_value == "todo"
    assert entry.new_value == "done"


def test_entry_rejects_empty_task_id() -> None:
    with pytest.raises(ValueError, match="task_id is required"):
        AuditLogEntry(task_id=" ", action="created")


def test_entry_rejects_invalid_action() -> None:
    with pytest.raises(ValueError, match="invalid action"):
        AuditLogEntry(task_id="t1", action="invalid")


def test_entry_actions_are_intentional() -> None:
    for action in ("created", "updated", "deleted"):
        entry = AuditLogEntry(task_id="t1", action=action)
        assert entry.action == action


def test_entry_uses_utc_timestamp() -> None:
    ts = datetime(2026, 7, 31, 10, 0, 0, tzinfo=UTC)
    entry = AuditLogEntry(task_id="t1", action="created", timestamp=ts)

    assert entry.timestamp == ts
    assert entry.timestamp.tzinfo == UTC


def test_entry_naive_timestamp_gets_utc() -> None:
    naive_ts = datetime(2026, 7, 31, 10, 0, 0)
    entry = AuditLogEntry(task_id="t1", action="created", timestamp=naive_ts)

    assert entry.timestamp.tzinfo == UTC
    assert entry.timestamp.hour == 10


def test_entry_is_frozen() -> None:
    entry = AuditLogEntry(task_id="t1", action="created")

    with pytest.raises(Exception):
        entry.task_id = "t2"


def test_entry_to_dict() -> None:
    ts = datetime(2026, 7, 31, 10, 0, 0, tzinfo=UTC)
    entry = AuditLogEntry(
        task_id="t1",
        action="updated",
        field_name="status",
        old_value="todo",
        new_value="done",
        entry_id="abc123",
        timestamp=ts,
    )

    result = entry.to_dict()

    assert result == {
        "entry_id": "abc123",
        "task_id": "t1",
        "action": "updated",
        "field_name": "status",
        "old_value": "todo",
        "new_value": "done",
        "timestamp": "2026-07-31T10:00:00Z",
    }


def test_entry_round_trips_from_dict() -> None:
    original = AuditLogEntry(
        task_id="t1",
        action="updated",
        field_name="status",
        old_value="todo",
        new_value="done",
        entry_id="abc123",
        timestamp=datetime(2026, 7, 31, 10, 0, 0, tzinfo=UTC),
    )

    restored = AuditLogEntry.from_dict(original.to_dict())

    assert restored.entry_id == original.entry_id
    assert restored.task_id == original.task_id
    assert restored.action == original.action
    assert restored.field_name == original.field_name
    assert restored.old_value == original.old_value
    assert restored.new_value == original.new_value
    assert restored.timestamp == original.timestamp


# -- AuditLog append-only behavior --


def test_log_starts_empty() -> None:
    log = AuditLog()

    assert log.is_empty()
    assert log.count() == 0
    assert log.get_entries() == []


def test_append_adds_entry() -> None:
    log = AuditLog()
    entry = AuditLogEntry(task_id="t1", action="created")

    result = log.append(entry)

    assert result is entry
    assert log.count() == 1
    assert not log.is_empty()


def test_append_preserves_order() -> None:
    log = AuditLog()

    e1 = AuditLogEntry(task_id="t1", action="created", entry_id="e1")
    e2 = AuditLogEntry(task_id="t1", action="updated", entry_id="e2")
    e3 = AuditLogEntry(task_id="t2", action="created", entry_id="e3")

    log.append(e1)
    log.append(e2)
    log.append(e3)

    entries = log.get_entries()
    assert len(entries) == 3
    assert entries[0].entry_id == "e1"
    assert entries[1].entry_id == "e2"
    assert entries[2].entry_id == "e3"


def test_get_entries_filtered_by_task_id() -> None:
    log = AuditLog()

    log.append(AuditLogEntry(task_id="t1", action="created", entry_id="e1"))
    log.append(AuditLogEntry(task_id="t2", action="created", entry_id="e2"))
    log.append(AuditLogEntry(task_id="t1", action="updated", entry_id="e3"))

    t1_entries = log.get_entries(task_id="t1")

    assert len(t1_entries) == 2
    assert all(e.task_id == "t1" for e in t1_entries)


def test_get_entries_returns_copy() -> None:
    log = AuditLog()
    log.append(AuditLogEntry(task_id="t1", action="created"))

    entries = log.get_entries()
    entries.clear()

    assert log.count() == 1


def test_log_entries_cannot_be_mutated() -> None:
    log = AuditLog()
    entry = AuditLogEntry(task_id="t1", action="created")
    log.append(entry)

    stored = log.get_entries()[0]

    with pytest.raises(Exception):
        stored.action = "deleted"


def test_log_entries_cannot_be_removed() -> None:
    log = AuditLog()

    log.append(AuditLogEntry(task_id="t1", action="created"))
    log.append(AuditLogEntry(task_id="t1", action="updated"))
    log.append(AuditLogEntry(task_id="t1", action="deleted"))

    # The log provides no delete or pop method - entries persist
    assert log.count() == 3
    assert not hasattr(log, "remove")
    assert not hasattr(log, "pop")
    assert not hasattr(log, "clear")


def test_append_multiple_tasks_independent() -> None:
    log = AuditLog()

    log.append(AuditLogEntry(task_id="t1", action="created", entry_id="a"))
    log.append(AuditLogEntry(task_id="t2", action="created", entry_id="b"))

    t1_entries = log.get_entries(task_id="t1")
    t2_entries = log.get_entries(task_id="t2")
    all_entries = log.get_entries()

    assert len(t1_entries) == 1
    assert len(t2_entries) == 1
    assert len(all_entries) == 2


def test_full_create_update_delete_audit_trail() -> None:
    log = AuditLog()

    # Task created
    log.append(AuditLogEntry(task_id="t1", action="created"))
    assert log.count() == 1

    # Task updated - status changed
    log.append(
        AuditLogEntry(
            task_id="t1",
            action="updated",
            field_name="status",
            old_value="todo",
            new_value="done",
        )
    )
    assert log.count() == 2

    # Verify the full trail
    trail = log.get_entries(task_id="t1")
    assert len(trail) == 2
    assert trail[0].action == "created"
    assert trail[1].action == "updated"
    assert trail[1].old_value == "todo"
    assert trail[1].new_value == "done"
