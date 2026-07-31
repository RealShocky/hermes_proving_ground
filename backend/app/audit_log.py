from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import final
from uuid import uuid4


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


@final
@dataclass(frozen=True)
class AuditLogEntry:
    """Immutable record of a single task change.

    Attributes:
        entry_id: Unique identifier for this log entry.
        task_id: The task that was changed.
        action: The change type (created, updated, deleted).
        field_name: Which field changed (None for create/delete).
        old_value: Previous value of the field (None for create).
        new_value: New value of the field (None for delete).
        timestamp: When the change occurred.
    """

    task_id: str
    action: str
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    entry_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id is required")
        # Validate action
        valid_actions = {"created", "updated", "deleted"}
        if self.action not in valid_actions:
            raise ValueError(
                f"invalid action {self.action!r}; expected one of: "
                f"{sorted(valid_actions)}"
            )
        # Ensure timestamp is timezone-aware
        if self.timestamp.tzinfo is None:
            object.__setattr__(self, "timestamp", self.timestamp.replace(tzinfo=UTC))

    def to_dict(self) -> dict:
        """Serialize to a JSON-ready dictionary."""
        return {
            "entry_id": self.entry_id,
            "task_id": self.task_id,
            "action": self.action,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp.isoformat().replace("+00:00", "Z"),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "AuditLogEntry":
        """Deserialize from a dictionary."""
        raw_ts = payload.get("timestamp")
        if raw_ts:
            ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        else:
            ts = _utc_now()
        return cls(
            task_id=payload["task_id"],
            action=payload["action"],
            field_name=payload.get("field_name"),
            old_value=payload.get("old_value"),
            new_value=payload.get("new_value"),
            entry_id=payload.get("entry_id", uuid4().hex),
            timestamp=ts,
        )


class AuditLog:
    """Append-only log of task changes.

    Entries can only be added, never modified or removed.
    """

    def __init__(self) -> None:
        self._entries: list[AuditLogEntry] = []

    def append(self, entry: AuditLogEntry) -> AuditLogEntry:
        """Add an entry to the log. Returns the entry."""
        self._entries.append(entry)
        return entry

    def get_entries(self, task_id: str | None = None) -> list[AuditLogEntry]:
        """Return entries, optionally filtered by task_id."""
        if task_id is None:
            return list(self._entries)
        return [e for e in self._entries if e.task_id == task_id]

    def count(self) -> int:
        """Return total number of entries."""
        return len(self._entries)

    def is_empty(self) -> bool:
        """Return True if the log has no entries."""
        return len(self._entries) == 0
