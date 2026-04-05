"""Unit tests for the Taskly CLI using typer.testing.

Demonstrates:
- Testing with CliRunner
- Isolation via --data-dir + tmp_path
- Verification of JSON persistence, output, and exit codes
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from taskly.main import app

runner = CliRunner()


def test_version() -> None:
    """Test --version flag (eager global option)."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "taskly 0.1.0" in result.stdout


def test_list_no_tasks(tmp_path: Path) -> None:
    """Test list command with custom --data-dir when no tasks exist."""
    result = runner.invoke(app, ["--data-dir", str(tmp_path), "list"])
    assert result.exit_code == 0
    assert "No tasks found." in result.stdout


def test_add_and_list(tmp_path: Path) -> None:
    """Test adding a task and listing it with custom data directory."""
    # Add a task
    add_result = runner.invoke(
        app,
        ["--data-dir", str(tmp_path), "add", "Write unit tests", "--priority", "high", "--due", "2026-04-15"],
    )
    assert add_result.exit_code == 0
    assert "Task #1 added" in add_result.stdout

    # List tasks
    list_result = runner.invoke(app, ["--data-dir", str(tmp_path), "list"])
    assert list_result.exit_code == 0
    assert "Write unit tests" in list_result.stdout
    assert "HIGH" in list_result.stdout
    assert "2026-04-15" in list_result.stdout


def test_complete_task(tmp_path: Path) -> None:
    """Test marking a task complete."""
    # Add task
    runner.invoke(app, ["--data-dir", str(tmp_path), "add", "Task to complete"])

    # Complete it
    complete_result = runner.invoke(app, ["--data-dir", str(tmp_path), "complete", "1"])
    assert complete_result.exit_code == 0
    assert "Task #1 completed" in complete_result.stdout

    # Verify in list --status completed
    list_result = runner.invoke(app, ["--data-dir", str(tmp_path), "list", "--status", "completed"])
    assert list_result.exit_code == 0
    assert "✅" in list_result.stdout


def test_delete_task(tmp_path: Path) -> None:
    """Test deleting a task (with --force to avoid interactive confirm)."""
    # Add task
    runner.invoke(app, ["--data-dir", str(tmp_path), "add", "Task to delete"])

    # Delete with --force
    delete_result = runner.invoke(app, ["--data-dir", str(tmp_path), "delete", "1", "--force"])
    assert delete_result.exit_code == 0
    assert "Task #1 deleted" in delete_result.stdout

    # Verify gone
    list_result = runner.invoke(app, ["--data-dir", str(tmp_path), "list"])
    assert list_result.exit_code == 0
    assert "No tasks found." in list_result.stdout


# Note: The edit command can also be tested with input= simulation:
# result = runner.invoke(
#     app, ["--data-dir", str(tmp_path), "edit", "1"], input="New desc\nmedium\n\ny\n"
# )
# (Prompt order: description → priority → due → confirm)
