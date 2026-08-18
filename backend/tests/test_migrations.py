from __future__ import annotations

"""Focused tests for the SQLite schema and migration layer.

All tests run against in-memory SQLite databases; no external database
server or file is required.
"""

import sqlite3

from app.migrations import (
    MIGRATIONS,
    MIGRATION_VERSION,
    apply_migrations,
    current_schema_version,
    ensure_schema,
)
from app.schema import (
    TASKS_INDEX_SQL,
    TASKS_SCHEMA_SQL,
    TASKS_TABLE,
    TASK_COLUMNS,
    get_index_names,
    get_table_columns,
    schema_is_current,
)


def _fresh_db() -> sqlite3.Connection:
    return sqlite3.connect(":memory:")


# -- migration metadata --


def test_migration_versions_are_sequential() -> None:
    versions = [m.version for m in MIGRATIONS]
    assert versions == list(range(1, len(versions) + 1))
    assert MIGRATION_VERSION == versions[-1]


def test_migration_statements_are_non_empty_sql() -> None:
    for migration in MIGRATIONS:
        assert migration.description
        assert migration.statements
        for statement in migration.statements:
            assert statement.strip()


# -- schema constants --


def test_task_columns_define_id_as_primary_key() -> None:
    names = {name for name, _ in TASK_COLUMNS}
    assert names == {"id", "title", "status", "created_at"}
    id_definition = dict(TASK_COLUMNS)["id"]
    assert "PRIMARY KEY" in id_definition.upper()


def test_schema_sql_creates_the_tasks_table() -> None:
    conn = _fresh_db()
    try:
        conn.execute(TASKS_SCHEMA_SQL)
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (TASKS_TABLE,),
        ).fetchone()
        assert table is not None
    finally:
        conn.close()


# -- applying migrations --


def test_apply_migrations_creates_expected_table() -> None:
    conn = _fresh_db()
    try:
        version = apply_migrations(conn)
        assert version == MIGRATION_VERSION
        assert current_schema_version(conn) == MIGRATION_VERSION
        assert schema_is_current(conn)
    finally:
        conn.close()


def test_apply_migrations_creates_expected_columns() -> None:
    conn = _fresh_db()
    try:
        apply_migrations(conn)
        columns = get_table_columns(conn)
        assert [name for name, _ in columns] == [name for name, _ in TASK_COLUMNS]
        expected_types = {name: definition.split()[0].upper() for name, definition in TASK_COLUMNS}
        for name, col_type in columns:
            assert col_type.upper() == expected_types[name]
    finally:
        conn.close()


def test_apply_migrations_creates_status_index() -> None:
    conn = _fresh_db()
    try:
        apply_migrations(conn)
        assert "idx_tasks_status" in get_index_names(conn)
    finally:
        conn.close()


def test_apply_migrations_is_idempotent() -> None:
    conn = _fresh_db()
    try:
        first = apply_migrations(conn)
        second = apply_migrations(conn)
        third = ensure_schema(conn)
        assert (first, second, third) == (MIGRATION_VERSION,) * 3
        assert current_schema_version(conn) == MIGRATION_VERSION
        assert schema_is_current(conn)
    finally:
        conn.close()


def test_schema_is_current_false_before_migration() -> None:
    conn = _fresh_db()
    try:
        assert not schema_is_current(conn)
        apply_migrations(conn)
        assert schema_is_current(conn)
    finally:
        conn.close()


def test_ensure_schema_is_idempotent_on_preexisting_db() -> None:
    conn = _fresh_db()
    try:
        # Simulate an older database that already has the table.
        conn.execute(TASKS_SCHEMA_SQL)
        conn.execute(TASKS_INDEX_SQL)
        ensure_schema(conn)
        ensure_schema(conn)
        assert schema_is_current(conn)
    finally:
        conn.close()
