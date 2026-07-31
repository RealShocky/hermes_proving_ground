from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import FrozenSet
from uuid import uuid4


VALID_TASK_STATUSES = frozenset({"todo", "in_progress", "blocked", "done"})

# Valid status transitions: current_status -> set of allowed next statuses.
# "done" is terminal -- no outgoing transitions.
VALID_TRANSITIONS: dict[str, FrozenSet[str]] = {
    "todo": frozenset({"in_progress", "blocked", "done"}),
    "in_progress": frozenset({"done", "blocked", "todo"}),
    "blocked": frozenset({"in_progress", "todo", "done"}),
    "done": frozenset(),
}


class TaskTransitionError(ValueError):
    """Raised when a task status transition is not allowed."""
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _normalize_title(value: str) -> str:
    title = value.strip()
    if not title:
        raise ValueError("task title is required")
    return title


def _normalize_status(value: str) -> str:
    status = value.strip().lower()
    if status not in VALID_TASK_STATUSES:
        allowed = ", ".join(sorted(VALID_TASK_STATUSES))
        raise ValueError(f"invalid task status {value!r}; expected one of: {allowed}")
    return status


def validate_transition(current_status: str, new_status: str) -> None:
    """Raise TaskTransitionError if transitioning from current_status to new_status is invalid."""
    current_status = _normalize_status(current_status)
    new_status = _normalize_status(new_status)
    if current_status == new_status:
        return
    allowed = VALID_TRANSITIONS.get(current_status, frozenset())
    if new_status not in allowed:
        raise TaskTransitionError(
            f"cannot transition from {current_status!r} to {new_status!r}"
        )


@dataclass(slots=True)
class Task:
    title: str
    status: str = "todo"
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        self.title = _normalize_title(self.title)
        self.status = _normalize_status(self.status)
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=UTC)
        else:
            self.created_at = self.created_at.astimezone(UTC)
        if not str(self.id).strip():
            raise ValueError("task id is required")
        self.id = str(self.id).strip()

    def transition_to(self, new_status: str) -> None:
        """Update status after validating the transition is allowed."""
        validate_transition(self.status, new_status)
        self.status = new_status

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at.isoformat().replace("+00:00", "Z"),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, str]) -> "Task":
        raw_created_at = payload.get("created_at")
        if raw_created_at:
            created_at = datetime.fromisoformat(raw_created_at.replace("Z", "+00:00"))
        else:
            created_at = _utc_now()
        return cls(
            id=str(payload.get("id", "")),
            title=str(payload.get("title", "")),
            status=str(payload.get("status", "todo")),
            created_at=created_at,
        )
