from __future__ import annotations

"""SQLite schema definition and inspection helpers.

This module holds the database configuration constants (table layout,
column types, indexes) plus pure inspection helpers that read a database
connection without mutating it. It is the single source of truth for the
SQLite slice of the task persistence layer.
"""

import sqlite3

# Database file name used when no explicit path is supplied.
DEFAULT_DB_FILENAME = "tasks.db"

# Table name for persisted tasks.
TASKS_TABLE = "tasks"

# Task column definitions, in order.
TASK_COLUMNS: tuple[tuple[str, str], ...] = (
    ("id", "TEXT PRIMARY KEY"),
    ("title", "TEXT NOT NULL"),
    ("status", "TEXT NOT NULL"),
    ("created_at", "TEXT NOT NULL"),
)

# The complete schema, as one executable SQL string.
TASKS_SCHEMA_SQL = "\n".join(
    [
        f"CREATE TABLE IF NOT EXISTS {TASKS_TABLE} (",
        ",\n".join(
            "    " + f"{name} {definition}" for name, definition in TASK_COLUMNS
        ),
        ");",
    ]
)

# Indexes created on top of the base table.
TASKS_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);"
)

# Status column is a plain TEXT column; no CHECK constraint is enforced so
# that status validation stays in the application layer (app.tasks).


def get_table_columns(connection: sqlite3.Connection) -> list[tuple[str, str]]:
    """Return (name, type) pairs for the tasks table, in schema order."""
    cursor = connection.execute(f"PRAGMA table_info({TASKS_TABLE})")
    # PRAGMA table_info rows: cid, name, type, notnull, dflt_value, pk
    return [(row[1], row[2]) for row in cursor.fetchall()]


def get_index_names(connection: sqlite3.Connection) -> set[str]:
    """Return the set of index names on the tasks table.

    PRAGMA index_list rows are (seq, name, unique, origin, partial).
    """
    cursor = connection.execute(f"PRAGMA index_list({TASKS_TABLE})")
    return {row[1] for row in cursor.fetchall()}


def schema_is_current(connection: sqlite3.Connection) -> bool:
    """Return True if the tasks table exists with the expected columns.

    Comparison is case-insensitive on column names (SQLite is
    case-insensitive for identifiers) so that the check works against
    databases created by slightly different tooling.
    """
    expected = {name.lower() for name, _ in TASK_COLUMNS}
    actual = {name.lower() for name, _ in get_table_columns(connection)}
    return expected == actual
