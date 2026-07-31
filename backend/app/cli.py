from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from app.tasks import Task, VALID_TASK_STATUSES


def create_task(args: argparse.Namespace) -> int:
    try:
        task = Task(title=args.title, status=args.status)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    json.dump(task.to_dict(), sys.stdout)
    sys.stdout.write("\n")
    return 0


def list_tasks(tasks: Sequence[Task], status_filter: str | None = None) -> list[dict[str, str]]:
    if status_filter is not None:
        status_filter = status_filter.strip().lower()
        if status_filter not in VALID_TASK_STATUSES:
            allowed = ", ".join(sorted(VALID_TASK_STATUSES))
            raise ValueError(f"invalid status filter {status_filter!r}; expected one of: {allowed}")
        tasks = [task for task in tasks if task.status == status_filter]
    return [task.to_dict() for task in tasks]


def _load_tasks(path: str | None) -> list[Task]:
    if path is None:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("task input file must contain a JSON array")
    return [Task.from_dict(item) for item in payload]


def print_tasks(args: argparse.Namespace) -> int:
    try:
        tasks = _load_tasks(args.input_file)
        result = list_tasks(tasks, status_filter=args.status)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def mark_done(args: argparse.Namespace) -> int:
    try:
        tasks = _load_tasks(args.input_file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    task_id = args.task_id.strip()
    found = False
    result_tasks = []
    for task in tasks:
        if task.id == task_id:
            task.status = "done"
            found = True
        result_tasks.append(task)

    if not found:
        print(f"error: task {task_id!r} not found", file=sys.stderr)
        return 1

    print(json.dumps([t.to_dict() for t in result_tasks], indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hpg",
        description="Hermes Proving Ground CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create", help="Create a new task")
    create_parser.add_argument("title", help="Task title")
    create_parser.add_argument("--status", default="todo", help="Task status (default: todo)")
    create_parser.set_defaults(func=create_task)

    list_parser = subparsers.add_parser("list", help="List tasks with optional status filter")
    list_parser.add_argument(
        "--status",
        default=None,
        help="Filter by status (todo, in_progress, blocked, done)",
    )
    list_parser.add_argument(
        "--input",
        dest="input_file",
        default=None,
        help="Path to a JSON file containing task objects",
    )
    list_parser.set_defaults(func=print_tasks)

    done_parser = subparsers.add_parser("done", help="Mark a task as done")
    done_parser.add_argument("task_id", help="Task ID to mark done")
    done_parser.add_argument(
        "--input",
        dest="input_file",
        required=True,
        help="Path to a JSON file containing task objects",
    )
    done_parser.set_defaults(func=mark_done)

    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    result = args.func(args)
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
