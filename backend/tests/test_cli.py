from __future__ import annotations

import io
import json
import sys
import tempfile

from app.cli import build_parser, list_tasks, main, parse_args
from app.tasks import Task


def _sample_tasks() -> list[Task]:
    return [
        Task(id="t1", title="Write tests", status="todo"),
        Task(id="t2", title="Ship feature", status="in_progress"),
        Task(id="t3", title="Fix bug", status="blocked"),
        Task(id="t4", title="Write docs", status="done"),
    ]


def _capture_stdout(argv: list[str]) -> tuple[int, str]:
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        code = main(argv)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    return code, output


def test_create_task_prints_json() -> None:
    code, output = _capture_stdout(["create", "Write tests"])

    data = json.loads(output)

    assert code == 0
    assert data["title"] == "Write tests"
    assert data["status"] == "todo"
    assert data["id"]
    assert data["created_at"]


def test_create_task_with_status() -> None:
    code, output = _capture_stdout(["create", "Ship feature", "--status", "in_progress"])

    data = json.loads(output)

    assert code == 0
    assert data["title"] == "Ship feature"
    assert data["status"] == "in_progress"


def test_create_task_invalid_status_raises() -> None:
    code = main(["create", "Bad task", "--status", "invalid"])

    assert code == 1


def test_no_command_prints_help_and_exits() -> None:
    code = main([])

    assert code == 1


def test_parse_args_defaults() -> None:
    args = parse_args(["create", "Review PR"])

    assert args.title == "Review PR"
    assert args.status == "todo"


def test_list_tasks_returns_all_tasks_when_no_filter() -> None:
    result = list_tasks(_sample_tasks())

    assert [task["id"] for task in result] == ["t1", "t2", "t3", "t4"]


def test_list_tasks_filters_by_status() -> None:
    result = list_tasks(_sample_tasks(), status_filter=" DONE ")

    assert len(result) == 1
    assert result[0]["id"] == "t4"
    assert result[0]["status"] == "done"


def test_list_tasks_rejects_invalid_status() -> None:
    try:
        list_tasks(_sample_tasks(), status_filter="waiting")
    except ValueError as exc:
        assert "invalid status filter" in str(exc)
    else:
        raise AssertionError("expected invalid status filter")


def test_build_parser_accepts_list_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(["list", "--input", "tasks.json", "--status", "done"])

    assert args.command == "list"
    assert args.input_file == "tasks.json"
    assert args.status == "done"


def test_main_list_empty_returns_zero() -> None:
    code, output = _capture_stdout(["list"])

    assert code == 0
    assert json.loads(output) == []


def test_main_list_with_file_and_filter() -> None:
    tasks = [
        {"id": "t1", "title": "A", "status": "todo"},
        {"id": "t2", "title": "B", "status": "done"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        json.dump(tasks, tmp)
        tmp_path = tmp.name

    code, output = _capture_stdout(["list", "--input", tmp_path, "--status", "done"])

    assert code == 0
    assert json.loads(output)[0]["id"] == "t2"


def test_main_list_invalid_status_returns_one() -> None:
    code = main(["list", "--status", "invalid"])

    assert code == 1
