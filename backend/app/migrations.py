from __future__ import annotations

"""Versioned SQLite migrations for the task persistence layer.

Migrations are plain dataclass records carrying ordered, idempotent SQL
statements. apply_migration runs them against a connection and records the
completed version in a lightweight user_version pragma, so re-applying an
already applied version is a no-op.
"""

import sqlite3
from dataclasses import dataclass, field

from app.schema import TASKS_INDEX_SQL, TASKS_SCHEMA_SQL


MIGRATION_VERSION = 1


@dataclass(frozen=True, slots=True)
class Migration:
    """A single numbered migration step."""

    version: int
    description: str
    statements: tuple[str, ...] = field(default_factory=tuple)


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        description="Create tasks table and status index",
        statements=(TASKS_SCHEMA_SQL, TASKS_INDEX_SQL),
    ),
)


def current_schema_version(connection: sqlite3.Connection) -> int:
    """Return the recorded schema version (0 for a brand-new database)."""
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def apply_migrations(connection: sqlite3.Connection) -> int:
    """Apply all pending migrations and return the resulting version.

    Idempotent: statements use IF NOT EXISTS, and the user_version pragma
    tracks which version has been applied.
    """
    applied = current_schema_version(connection)
    for migration in MIGRATIONS:
        if migration.version <= applied:
            continue
        with connection:
            for statement in migration.statements:
                connection.execute(statement)
            connection.execute(f"PRAGMA user_version = {migration.version}")
        applied = migration.version
    return applied


def ensure_schema(connection: sqlite3.Connection) -> int:
    """Convenience wrapper: apply every pending migration, returning version."""
    return apply_migrations(connection)
