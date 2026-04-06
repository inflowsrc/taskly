"""Taskly - Professional todo-list CLI built with Typer.
"""

from __future__ import annotations

import json
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, TypedDict, cast

import typer
from rich.console import Console
from rich.table import Table

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


class Task(TypedDict):
    """Typed structure for a single task."""

    id: int
    description: str
    priority: str
    due: str | None
    completed: bool
    finished: str | None   # New: date when task was marked completed (YYYY-MM-DD)


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
    Old tasks without 'finished' key are automatically upgraded.
    """
    db_path = get_db_path(ctx)
    if not db_path.exists():
        return []
    with db_path.open(encoding="utf-8") as f:
        raw_tasks: list[dict[str, Any]] = json.load(f)

    # Migrate old tasks (backward compatibility)
    migrated: list[Task] = []
    for t in raw_tasks:
        task: Task = cast(Task, {
            "id": t["id"],
            "description": t["description"],
            "priority": t["priority"],
            "due": t.get("due"),
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


def version_callback(value: bool) -> None:
    """Print version and exit when --version is used."""
    if value:
        typer.echo("taskly 0.1.0")
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
    """Add a new task."""
    tasks = load_tasks(ctx)
    task_id = get_next_id(tasks)

    if due:
        try:
            date.fromisoformat(due)
        except ValueError:
            typer.secho("Error: --due must be in YYYY-MM-DD format", fg=typer.colors.RED)
            raise typer.Exit(1) from None

    task: Task = {
        "id": task_id,
        "description": description,
        "priority": priority.value,
        "due": due,
        "completed": False,
        "finished": None,
    }

    tasks.append(task)
    save_tasks(ctx, tasks)

    typer.secho(f"✅ Task #{task_id} added", fg=typer.colors.GREEN)


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
) -> None:
    """List tasks with optional filters. Use --status completed to show completed tasks."""
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

    table = Table(title="Taskly — Your Tasks", show_header=True)
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Priority", justify="center")
    table.add_column("Due", justify="center")
    table.add_column("Finished", justify="center")
    table.add_column("Status", justify="center")

    priority_colors = {"low": "blue", "medium": "yellow", "high": "red"}

    for t in filtered:
        status_icon = "✅" if t["completed"] else "⏳"
        prio_color = priority_colors.get(t["priority"], "")
        due_str = t["due"] or "—"
        finished_str = t["finished"] or "—"

        table.add_row(
            str(t["id"]),
            t["description"],
            f"[{prio_color}]{t['priority'].upper()}[/{prio_color}]",
            due_str,
            finished_str,
            status_icon,
        )

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
    """Interactively edit an existing task (description, priority, due date, or status)."""
    tasks = load_tasks(ctx)
    task = find_task(tasks, task_id)
    if task is None:
        typer.secho(f"❌ Task #{task_id} not found", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Editing task #{task_id}: {task['description']}", fg=typer.colors.CYAN)

    # Edit description
    new_description = typer.prompt(
        "Description",
        default=task["description"],
        show_default=True,
    )
    task["description"] = new_description

    # Edit priority
    new_priority = typer.prompt(
        "Priority",
        default=task["priority"],
        type=Priority,
        show_default=True,
    )
    task["priority"] = new_priority.value

    # Edit due date
    current_due = task["due"] or ""
    new_due = typer.prompt(
        "Due date (YYYY-MM-DD or leave empty)",
        default=current_due,
        show_default=True,
    )
    if new_due.strip() == "":
        task["due"] = None
    else:
        try:
            date.fromisoformat(new_due.strip())
            task["due"] = new_due.strip()
        except ValueError:
            typer.secho("Warning: Invalid due date format. Keeping previous value.", fg=typer.colors.YELLOW)

    # Edit completion status
    current_completed = task["completed"]
    new_completed = typer.confirm("Mark as completed?", default=current_completed)

    if new_completed and not current_completed:
        # Newly completed → record today's date
        today = date.today().isoformat()
        task["finished"] = today
        typer.secho(f"Task marked completed on {today}", fg=typer.colors.GREEN)
    elif not new_completed and current_completed:
        # Un-completed → clear finished date
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
