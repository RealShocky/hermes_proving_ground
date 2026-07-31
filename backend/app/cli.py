from __future__ import annotations

import argparse
import json
import sys

from app.tasks import Task


def create_task(args: argparse.Namespace) -> None:
    """Create a task and print it as JSON."""
    task = Task(title=args.title, status=args.status)
    json.dump(task.to_dict(), sys.stdout)
    sys.stdout.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="hpg",
        description="Hermes Proving Ground CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create", help="Create a new task")
    create_parser.add_argument("title", help="Task title")
    create_parser.add_argument(
        "--status",
        default="todo",
        help="Task status (default: todo)",
    )
    create_parser.set_defaults(func=create_task)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.command is None:
        parse_args(["--help"])
        sys.exit(1)
    args.func(args)
