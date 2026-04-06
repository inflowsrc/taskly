"""Unit tests for the Taskly CLI using typer.testing.

Clean, reliable tests for core functionality:
- Version flag
- Empty list
- Completing a task (sets finished date)
- Deleting a task
"""

from pathlib import Path

from typer.testing import CliRunner

from taskly.main import app

runner = CliRunner()


def test_version() -> None:
    """Test --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "taskly 0.1.0" in result.stdout


def test_list_no_tasks(tmp_path: Path) -> None:
    """Test list with custom data dir when no tasks exist."""
    result = runner.invoke(app, ["--data-dir", str(tmp_path), "list"])
    assert result.exit_code == 0
    assert "No tasks found." in result.stdout


def test_complete_task(tmp_path: Path) -> None:
    """Test marking a task complete (sets finished date)."""
    runner.invoke(app, ["--data-dir", str(tmp_path), "add", "Task to complete"])
    result = runner.invoke(app, ["--data-dir", str(tmp_path), "complete", "1"])
    assert result.exit_code == 0
    assert "completed on" in result.stdout

    list_result = runner.invoke(app, ["--data-dir", str(tmp_path), "list", "--status", "completed"])
    assert list_result.exit_code == 0
    assert "✅" in list_result.stdout


def test_delete_task(tmp_path: Path) -> None:
    """Test deleting a task with --force."""
    runner.invoke(app, ["--data-dir", str(tmp_path), "add", "Task to delete"])
    result = runner.invoke(app, ["--data-dir", str(tmp_path), "delete", "1", "--force"])
    assert result.exit_code == 0
    assert "Task #1 deleted" in result.stdout
