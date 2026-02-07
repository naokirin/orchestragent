# Claude Code Configuration for Python

This directory is a Claude Code configuration template for Python projects. Copy it along with `CLAUDE.md` to the root of a Python project to use it.

This template is provided alongside a Cursor configuration (`.cursor`) in the same repo; use the one that matches your editor. Content is kept in sync where applicable.

## Prerequisites

- **Python 3.x**: Ensure Python and pip (or uv/poetry) are available.
- **Ruff** (optional): Add for lint and format; used by `/run-lint-python`, `/run-format-python`, and the format hook. See the repo root **README.md** (section “Introducing Ruff and type checking”) for install and pyproject.toml config.
- **pytest** (optional): Add for tests; used by `/run-tests-python`.
- **mypy or pyright** (optional): Add for type checking; used by `/run-typecheck-python`.
- **jq** or **python3** (optional): Used by the format hook to parse JSON. If neither is available, the hook skips formatting.

## Structure

| Directory / file | Description |
|------------------|-------------|
| **CLAUDE.md** | Project instructions: principles, layout, tooling, verification, workflows, code review |
| **.claude/agents/** | Custom sub-agents (python-tester, python-code-reviewer) |
| **.claude/skills/** | Skills for Python development, refactoring, and testing (auto-loaded when relevant) |
| **.claude/commands/** | Slash commands run from chat with `/` |
| **.claude/hooks/** | Hook scripts (e.g. Ruff format after file edit) |
| **.claude/settings.json** | Hook configuration |

## Usage

1. Copy `CLAUDE.md` and `.claude/` into your Python project root.
   ```bash
   cp python/CLAUDE.md /path/to/your/python_project/CLAUDE.md
   cp -r python/.claude /path/to/your/python_project/.claude
   ```
2. Make the hook script executable.
   ```bash
   chmod +x .claude/hooks/format-python.sh
   ```
3. Open the project with Claude Code. Commands, skills, and agents load automatically. Use `/` to see available commands.

## Commands

Slash commands triggered manually with `/` in chat.

| Command | Description | Sub-agent |
|---------|-------------|-----------|
| `/run-tests-python` | Run pytest and fix failures | `python-tester` |
| `/code-review-python` | Review Python code for style, types, and maintainability | `python-code-reviewer` |
| `/run-lint-python` | Run Ruff linter and fix auto-fixable issues | — |
| `/run-format-python` | Format code with Ruff or Black | — |
| `/run-typecheck-python` | Run mypy or pyright | — |

Commands with a sub-agent run in a forked context (`context: fork`) for isolation.

## Sub-agents

Custom sub-agents that Claude delegates to automatically based on task description, or explicitly via commands.

| Agent | Description | Tools | Model |
|-------|-------------|-------|-------|
| **python-tester** | Runs pytest, identifies failures, and fixes code or tests | Read, Edit, Write, Bash, Grep, Glob | sonnet |
| **python-code-reviewer** | Reviews code for types, PEP 8, idioms, and maintainability | Read, Grep, Glob, Bash | sonnet |

Sub-agent files are in `.claude/agents/`. See [Sub-agents documentation](https://code.claude.com/docs/sub-agents).

## Skills

Background knowledge that Claude auto-loads when working on relevant tasks. These are not user-invocable (`user-invocable: false`); Claude loads them automatically based on context.

| Skill | Auto-loaded when |
|-------|-----------------|
| **python-development** | Writing or modifying Python code, adding modules, types, APIs |
| **python-refactor** | Simplifying code, applying style/idiom rules, improving types |
| **pytest-testing** | Adding or fixing tests (unit, integration) |

Skill files are in `.claude/skills/<name>/SKILL.md`. See [Skills documentation](https://code.claude.com/docs/skills).

## Hooks

| Event | Matcher | Script | Description |
|-------|---------|--------|-------------|
| PostToolUse | `Edit\|Write` | `format-python.sh` | Runs Ruff (or Black) format on `.py` files after edit/write. No-op if formatter is not available. |

Hook configuration is in `.claude/settings.json`. See [Hooks documentation](https://code.claude.com/docs/hooks-guide).

## CLAUDE.md and verification

`CLAUDE.md` is kept short and focuses on principles, directory layout, tooling, **verification** (run typecheck, tests, and lint after changes), workflows, and code review categories. Detailed style lives in the linked references and in `.cursor/rules/` if you use Cursor too. After code changes, the agent should run typecheck, tests, and lint to verify; use `/run-typecheck-python`, `/run-tests-python`, and `/run-lint-python` when appropriate.

## Comparison with Cursor Configuration

| Cursor concept | Claude Code equivalent |
|----------------|------------------------|
| Rules (`.mdc` files) | `CLAUDE.md` (consolidated) |
| Commands | `.claude/commands/*.md` (with YAML frontmatter) |
| Agents | `.claude/agents/*.md` (custom sub-agents) |
| Skills | `.claude/skills/<name>/SKILL.md` |
| Hooks (`hooks.json` + scripts) | `.claude/settings.json` + `.claude/hooks/` |
