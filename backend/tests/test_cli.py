from __future__ import annotations

import io
import json
import sys

import pytest

from app.cli import main, parse_args


def test_create_task_prints_json() -> None:
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        main(["create", "Write tests"])

        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    data = json.loads(output)

    assert data["title"] == "Write tests"
    assert data["status"] == "todo"
    assert data["id"]
    assert data["created_at"]


def test_create_task_with_status() -> None:
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        main(["create", "Ship feature", "--status", "in_progress"])

        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    data = json.loads(output)

    assert data["title"] == "Ship feature"
    assert data["status"] == "in_progress"


def test_create_task_invalid_status_raises() -> None:
    with pytest.raises(ValueError, match="invalid task status"):
        main(["create", "Bad task", "--status", "invalid"])


def test_no_command_prints_help_and_exits() -> None:
    with pytest.raises(SystemExit):
        main([])


def test_parse_args_defaults() -> None:
    args = parse_args(["create", "Review PR"])

    assert args.title == "Review PR"
    assert args.status == "todo"
