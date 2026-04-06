# Taskly

A clean, professional todo-list CLI built with **Typer** and **Rich**.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- Add, list, complete, edit, and delete tasks
- Persistent storage with automatic migration
- Rich colored output and beautiful tables
- Priority levels (High, Medium, Low)
- Due dates and automatic "Started" tracking
- "Completed" date recorded when tasks are finished
- Flexible filtering (`--status`, `--priority`)
- Smart default sorting: **due date** (earliest first) then **priority** (HIGH → LOW)
- Global `--data-dir` option for custom storage location
- Full type safety with `basedpyright` (recommended mode)

## Installation

### Using uv (recommended)

```bash
# Clone the repository
git clone https://github.com/inflowsrc/taskly.git
cd taskly

# Install as an editable global tool
uv tool install --editable .
```

Now you can run taskly from any terminal.

## Verify Installation

```bash
taskly --version
taskly --help
```

## Quick Start

```bash
# Add a task
taskly add "Finish project proposal" --priority high --due 2026-04-15

# List pending tasks (default view)
taskly list

# List all tasks with sorting
taskly list --status all --sort due

# Mark a task as complete
taskly complete 1

# Edit a task interactively
taskly edit 2

# Delete a task
taskly delete 3 --force
```

## Available Commands

| Command       | Description           |
| ------------- | --------------------- |
| add           | Add a new task        |
| list          | List tasks (supports filtering and sorting) |
| complete <id> | Mark a task as completed  |
| edit <id>     | Interactively edit a task |
| delete <id>   | Delete a task |
| version       | Show the installed version    |
| --version, -V | Show version and exit     |
| --data-dir PATH   | Use custom directory for tasks.json   |

## List Command Options

```bash
taskly list --status [pending|completed|all]
taskly list --priority [high|medium|low]
taskly list --sort [due|finished|priority]
```

Default behavior: Shows pending tasks, sorted by due date then priority.

## Project Structure

```text
taskly/
├── pyproject.toml
├── LICENSE
├── README.md
├── src/
│   └── taskly/
│       ├── __init__.py
│       └── main.py
└── tests/
    └── test_taskly.py
```

## Development

```bash
# Install dependencies (including dev)
uv sync

# Run tests
uv run pytest -v

# Type checking
uv run basedpyright src/taskly

# Run locally without global install
uv run taskly --help
```

## License

This project is licensed under the MIT License - see LICENSE.md for details.
