"""Taskly - Professional todo-list CLI built with Typer.

Fully typed for basedpyright "recommended" mode.
- Added 'started' field (date task was created)
- 'Completed' column only shown when viewing completed or all tasks
- Default sorting: due date (earliest first) then priority (HIGH → LOW)
"""

from __future__ import annotations

import json
from datetime import date
from enum import Enum
from importlib.metadata import PackageNotFoundError, version as get_package_version
from pathlib import Path
from typing import Annotated, Any, TypedDict, cast

import typer
from rich.console import Console
from rich.table import Table

# Single source of truth for version
try:
    __version__ = get_package_version("taskly")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

app = typer.Typer(
    name="taskly",
    help="Taskly — your terminal todo manager",
    rich_markup_mode="rich",
    add_completion=True,
)

console = Console()


class Priority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Status(str, Enum):
    """Task status filter options."""

    PENDING = "pending"
    COMPLETED = "completed"
    ALL = "all"


class SortBy(str, Enum):
    """Available sort options for the list command."""

    DUE = "due"
    FINISHED = "finished"
    PRIORITY = "priority"


class Task(TypedDict):
    """Typed structure for a single task."""

    id: int
    description: str
    priority: str
    due: str | None
    started: str          # Date task was added (YYYY-MM-DD)
    completed: bool
    finished: str | None  # Date task was completed (YYYY-MM-DD)


class DataDirContext(TypedDict):
    """Type for ctx.obj (used by every command)."""

    data_dir: Path


def get_db_path(ctx: typer.Context) -> Path:
    """Return path to the JSON database using data_dir from ctx.obj."""
    context_data: DataDirContext = cast(DataDirContext, ctx.obj)
    app_dir: Path = context_data["data_dir"]
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir / "tasks.json"


def load_tasks(ctx: typer.Context) -> list[Task]:
    """Load tasks from the JSON database. Returns empty list if file doesn't exist.
    Old tasks are automatically migrated with default values.
    """
    db_path = get_db_path(ctx)
    if not db_path.exists():
        return []
    with db_path.open(encoding="utf-8") as f:
        raw_tasks: list[dict[str, Any]] = json.load(f)

    # Migrate old tasks (backward compatibility)
    migrated: list[Task] = []
    today = date.today().isoformat()
    for t in raw_tasks:
        task: Task = cast(Task, {
            "id": t["id"],
            "description": t["description"],
            "priority": t["priority"],
            "due": t.get("due"),
            "started": t.get("started", today),           # migrate old tasks
            "completed": t.get("completed", False),
            "finished": t.get("finished"),
        })
        migrated.append(task)
    return migrated


def save_tasks(ctx: typer.Context, tasks: list[Task]) -> None:
    """Save tasks to the JSON database."""
    db_path = get_db_path(ctx)
    with db_path.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


def get_next_id(tasks: list[Task]) -> int:
    """Return the next available task ID."""
    if not tasks:
        return 1
    return max(t["id"] for t in tasks) + 1


def find_task(tasks: list[Task], task_id: int) -> Task | None:
    """Find a task by ID. Returns None if not found."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None


def priority_key(task: Task) -> int:
    """Return numeric priority for sorting: HIGH=3, MEDIUM=2, LOW=1."""
    order = {"high": 3, "medium": 2, "low": 1}
    return order.get(task["priority"], 0)


def _date_key(date_str: str | None) -> date | None:
    """Safely convert ISO date string to date object."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None


def due_key(task: Task) -> tuple[int, date | None]:
    """Sort key for due: None values last, then earliest date first."""
    d = _date_key(task["due"])
    return (1 if d is None else 0, d)


def started_key(task: Task) -> date:
    """Sort key for started date (always present)."""
    return _date_key(task["started"]) or date.min   # fallback, should never happen


def finished_key(task: Task) -> tuple[int, date | None]:
    """Sort key for finished: None values last."""
    d = _date_key(task["finished"])
    return (1 if d is None else 0, d)


def version_callback(value: bool) -> None:
    """Print version and exit when --version is used."""
    if value:
        typer.echo(f"taskly {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
    data_dir: Annotated[
        Path | None,
        typer.Option(
            "--data-dir",
            help="Custom directory for tasks.json storage (defaults to user app dir)",
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
) -> None:
    """Taskly CLI entry point with global --data-dir support."""
    ctx.obj = {"data_dir": data_dir or Path(typer.get_app_dir("taskly"))}


@app.command()
def add(
    ctx: typer.Context,
    description: Annotated[str, typer.Argument(help="Task description")],
    priority: Annotated[
        Priority,
        typer.Option(
            "--priority",
            "-p",
            help="Task priority",
            case_sensitive=False,
        ),
    ] = Priority.MEDIUM,
    due: Annotated[
        str | None,
        typer.Option(
            "--due",
            "-d",
            help="Due date in YYYY-MM-DD format",
        ),
    ] = None,
) -> None:
    """Add a new task. Automatically records today's date as 'started'."""
    tasks = load_tasks(ctx)
    task_id = get_next_id(tasks)

    if due:
        try:
            date.fromisoformat(due)
        except ValueError:
            typer.secho("Error: --due must be in YYYY-MM-DD format", fg=typer.colors.RED)
            raise typer.Exit(1) from None

    today = date.today().isoformat()

    task: Task = {
        "id": task_id,
        "description": description,
        "priority": priority.value,
        "due": due,
        "started": today,
        "completed": False,
        "finished": None,
    }

    tasks.append(task)
    save_tasks(ctx, tasks)

    typer.secho(f"✅ Task #{task_id} added (started {today})", fg=typer.colors.GREEN)


@app.command()
def list(
    ctx: typer.Context,
    status: Annotated[
        Status,
        typer.Option(
            "--status",
            "-s",
            help="Filter by status",
            case_sensitive=False,
        ),
    ] = Status.PENDING,
    priority: Annotated[
        Priority | None,
        typer.Option(
            "--priority",
            "-p",
            help="Filter by priority",
        ),
    ] = None,
    sort_by: Annotated[
        SortBy | None,
        typer.Option(
            "--sort",
            help="Sort tasks by: due, finished, or priority (HIGH to LOW)",
            case_sensitive=False,
        ),
    ] = None,
) -> None:
    """List tasks with optional filters and sorting.
    
    Default sort: due date (earliest first) then priority (HIGH → LOW).
    'Completed' column only shown when viewing completed or all tasks.
    """
    tasks = load_tasks(ctx)

    # Apply filters
    filtered: list[Task] = []
    for t in tasks:
        if status != Status.ALL:
            if (status == Status.PENDING) != (not t["completed"]):
                continue
        if priority and t["priority"] != priority.value:
            continue
        filtered.append(t)

    if not filtered:
        typer.echo("No tasks found.")
        return

    # Default sorting: due date → priority (HIGH to LOW)
    if sort_by is None:
        # Primary: due, Secondary: priority
        filtered.sort(key=lambda t: (due_key(t), priority_key(t)))
    elif sort_by == SortBy.DUE:
        filtered.sort(key=due_key)
    elif sort_by == SortBy.FINISHED:
        filtered.sort(key=finished_key, reverse=True)
    elif sort_by == SortBy.PRIORITY:
        filtered.sort(key=priority_key, reverse=True)

    # Build table
    table = Table(title="Taskly — Your Tasks", show_header=True)
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Priority", justify="center")
    table.add_column("Due", justify="center")
    table.add_column("Started", justify="center")

    # Only show "Completed" column when relevant
    show_completed_column = status in (Status.COMPLETED, Status.ALL)
    if show_completed_column:
        table.add_column("Completed", justify="center")

    table.add_column("Status", justify="center")

    priority_colors = {"low": "blue", "medium": "yellow", "high": "red"}

    for t in filtered:
        status_icon = "✅" if t["completed"] else "⏳"
        prio_color = priority_colors.get(t["priority"], "")
        due_str = t["due"] or "—"
        started_str = t["started"]
        completed_str = t.get("finished") or "—" if show_completed_column else None

        row = [
            str(t["id"]),
            t["description"],
            f"[{prio_color}]{t['priority'].upper()}[/{prio_color}]",
            due_str,
            started_str,
        ]

        if show_completed_column:
            row.append(completed_str)

        row.append(status_icon)
        table.add_row(*row)

    console.print(table)


@app.command()
def complete(
    ctx: typer.Context,
    task_id: Annotated[int, typer.Argument(help="ID of the task to mark complete")],
) -> None:
    """Mark a task as completed and record today's date in 'finished'."""
    tasks = load_tasks(ctx)
    task = find_task(tasks, task_id)
    if task is None:
        typer.secho(f"❌ Task #{task_id} not found", fg=typer.colors.RED)
        raise typer.Exit(1)

    if task["completed"]:
        typer.secho(f"Task #{task_id} is already completed.", fg=typer.colors.YELLOW)
        return

    today = date.today().isoformat()
    task["completed"] = True
    task["finished"] = today
    save_tasks(ctx, tasks)
    typer.secho(f"✅ Task #{task_id} completed on {today}", fg=typer.colors.GREEN)


@app.command()
def edit(
    ctx: typer.Context,
    task_id: Annotated[int, typer.Argument(help="ID of the task to edit")],
) -> None:
    """Interactively edit an existing task."""
    tasks = load_tasks(ctx)
    task = find_task(tasks, task_id)
    if task is None:
        typer.secho(f"❌ Task #{task_id} not found", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Editing task #{task_id}: {task['description']}", fg=typer.colors.CYAN)

    new_description = typer.prompt("Description", default=task["description"], show_default=True)
    task["description"] = new_description

    new_priority = typer.prompt("Priority", default=task["priority"], type=Priority, show_default=True)
    task["priority"] = new_priority.value

    current_due = task["due"] or ""
    new_due = typer.prompt("Due date (YYYY-MM-DD or leave empty)", default=current_due, show_default=True)
    if new_due.strip() == "":
        task["due"] = None
    else:
        try:
            date.fromisoformat(new_due.strip())
            task["due"] = new_due.strip()
        except ValueError:
            typer.secho("Warning: Invalid due date format. Keeping previous value.", fg=typer.colors.YELLOW)

    current_completed = task["completed"]
    new_completed = typer.confirm("Mark as completed?", default=current_completed)

    if new_completed and not current_completed:
        today = date.today().isoformat()
        task["finished"] = today
        typer.secho(f"Task marked completed on {today}", fg=typer.colors.GREEN)
    elif not new_completed and current_completed:
        task["finished"] = None

    task["completed"] = new_completed

    save_tasks(ctx, tasks)
    typer.secho(f"✅ Task #{task_id} updated successfully", fg=typer.colors.GREEN)


@app.command()
def delete(
    ctx: typer.Context,
    task_id: Annotated[int, typer.Argument(help="ID of the task to delete")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation"),
    ] = False,
) -> None:
    """Delete a task (with confirmation unless --force is used)."""
    tasks = load_tasks(ctx)
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            if not force:
                confirm = typer.confirm(f"Delete task '{task['description']}'?")
                if not confirm:
                    typer.echo("Operation cancelled.")
                    return
            del tasks[i]
            save_tasks(ctx, tasks)
            typer.secho(f"🗑️  Task #{task_id} deleted", fg=typer.colors.GREEN)
            return

    typer.secho(f"❌ Task #{task_id} not found", fg=typer.colors.RED)
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
