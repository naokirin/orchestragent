# orchestragent Project

Python project implementing a planner–worker style autonomous agent system (Planner / Worker / Judge). See [README.md](./README.md) and [docs/dev/](./docs/dev/) for details.

---

## Principles (Python)

- **Type hints**: Use type annotations for public APIs, parameters, and return types. Prefer mypy or pyright for static checking; avoid `# type: ignore` unless justified.
- **PEP 8 and tooling**: Follow PEP 8; use Ruff (or Black + Ruff lint) for formatting and linting. Prefer project config in `pyproject.toml`.
- **Single responsibility**: Keep functions and modules focused; prefer small, testable units. Use composition over large classes.

---

## Project Layout

| Path | Purpose |
|------|---------|
| `src/orchestragent/` | Application code (agents, LLM, state, dashboard, etc.) |
| `tests/` | Unit and integration tests (pytest) |
| `docs/dev/` | Developer docs: design, requirements, prompt contracts |
| `docs/adr/` | Architecture Decision Records (ADR) |
| `prompts/` | Agent prompts (planner, worker, judge, plan_judge, etc.) |
| `state/`, `logs/` | Runtime state and logs (file-based) |
| `pyproject.toml` | Project config and dependencies; Ruff/mypy config here or elsewhere |
| `requirements.txt`, `requirements-dev.txt` | Runtime and dev dependencies |

Entry point: `main.py` (main loop). Web dashboard: `python -m orchestragent.dashboard.web`.

---

## Tooling and Style

- **Style**: Follow `.cursor/rules/` (python-core, python-style, python-idioms). Prefer Ruff.
- **Format**: `ruff format .` (run before commit; use `.claude/hooks/` format hook if available).
- **Lint**: `ruff check .` (use `--fix` when needed). `/run-lint-python` when available.
- **Typecheck**: `mypy src` or `pyright`. `/run-typecheck-python` when available.
- **Tests**: `pytest`. Keep tests in `tests/`. `/run-tests-python` when available.

CI (`.github/workflows/ci.yml`) runs `ruff check`, `ruff format --check`, and `pytest`.

---

## Verification (after changes)

After code changes, verify with:

- **Typecheck**: `mypy src` or `pyright`
- **Tests**: `pytest` (optionally with path or `-k` pattern)
- **Lint**: `ruff check .` (optionally `--fix`)
- **Format**: `ruff format .`

---

## Workflows

### General Python development

When adding or changing code, types, or APIs: follow the principles and `.cursor/rules/`; use type hints; run typecheck, tests, and lint after changes.

### Refactoring

When simplifying or applying style/idiom rules: preserve observable behaviour; rely on existing tests; prefer small steps; after refactor run typecheck, tests, and lint to confirm no new failures.

### Adding or fixing tests

Place tests in `tests/` with clear names and pytest idioms. Run `pytest` after changes to verify.

### Project-specific

- **Agents, loop, state**: When touching `src/orchestragent/agents/`, `runner/`, or `state/`, see [docs/dev/ARCHITECTURE_DESIGN.md](./docs/dev/ARCHITECTURE_DESIGN.md) and [docs/dev/PLANNING.md](./docs/dev/PLANNING.md).
- **Prompt changes**: Align with `prompts/` and the input/output contract in [docs/dev/PROMPT_CONTRACT.md](./docs/dev/PROMPT_CONTRACT.md).
- **Dashboard (TUI/Web)**: `src/orchestragent/dashboard/`. See [docs/dev/WEB_DASHBOARD_PLAN.md](./docs/dev/WEB_DASHBOARD_PLAN.md).
- **Docker and execution environment**: See [README.md](./README.md) quick start and [docs/dev/EXECUTION_ENVIRONMENT.md](./docs/dev/EXECUTION_ENVIRONMENT.md).

---

## Code review

When reviewing Python code, check: type hints and no unnecessary `Any`; PEP 8 and naming (snake_case); error handling and exceptions; test coverage and clarity. Categorize feedback as **Critical** (must fix), **Warning** (should fix), or **Suggestion** (optional).

---

## Reference

- [PEP 8](https://peps.python.org/pep-0008/)
- [Ruff](https://docs.astral.sh/ruff/)
- [pytest](https://docs.pytest.org/)
- [mypy](https://mypy-lang.org/) / [Pyright](https://microsoft.github.io/pyright/)
