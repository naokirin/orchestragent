---
name: python-development
description: General Python development following type hints, PEP 8, and best practices. Use when writing or modifying Python code, adding modules, or defining APIs.
user-invocable: false
---

# Python Development

## When to Use

- Writing new Python code (modules, functions, types, public API).
- Adding or changing type hints and public interfaces.
- Designing or evolving APIs and module boundaries.
- Adding dependencies and updating pyproject.toml or requirements.

## Principles

1. **Types**: Use type hints for public APIs and boundaries. Prefer mypy/pyright; avoid `Any` and `# type: ignore` unless justified.
2. **Style**: Follow PEP 8 and the project's Python style and idiom rules (CLAUDE.md or `.cursor/rules/` .mdc files). Use snake_case for variables and functions; PascalCase for classes.
3. **Layout**: Keep functions and modules focused; prefer small, testable units. Place tests per project convention (`tests/`, `test_*.py`).

## Verification

- `mypy src` or `pyright` (or project typecheck script).
- `pytest` (or project test command).
- `ruff check .` when available (fix or allow with justification).
- `ruff format .` or Black (or rely on the format hook).
