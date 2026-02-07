# Cursor Configuration for Python

This directory is a Cursor configuration template for Python projects. Copy it to the root of a Python project to use it. It is provided alongside a Claude Code configuration (`.claude` + `CLAUDE.md`) in the same repo; use the one that matches your editor.

## Structure

| Path | Description |
|------|-------------|
| **rules/** | Always-applied and glob-based rules (python-core, python-style, python-idioms, pytest-style) |
| **skills/** | Skills for Python development, refactoring, and testing (auto-loaded when relevant) |
| **commands/** | Slash commands: run-tests-python, run-lint-python, run-format-python, run-typecheck-python, code-review-python |
| **agents/** | Agent descriptions for python-tester and python-code-reviewer |
| **hooks/** | format-python.sh runs after editing .py files |
| **hooks.json** | Hook configuration (afterFileEdit → format-python.sh) |

## Usage

1. Copy `.cursor/` to your Python project root.
2. Make the hook executable: `chmod +x .cursor/hooks/format-python.sh`
3. Rules, skills, commands, and agents load automatically in Cursor.

## Prerequisites

- **Python 3.x**: Ensure Python and pip (or uv/poetry) are available.
- **Ruff** (optional): Add for lint and format; used by `/run-lint-python`, `/run-format-python`, and the format hook. See the repo root **README.md** (section “Introducing Ruff and type checking”) for install and pyproject.toml config.
- **pytest** (optional): Add for tests; used by `/run-tests-python`.
- **mypy or pyright** (optional): Add for type checking; used by `/run-typecheck-python`.
- **jq** or **python3** (optional): Used by the format hook to parse JSON. If neither is available, the hook skips formatting.
