# Run Lint (Ruff)

Run Ruff linter and fix auto-fixable issues.

1. Check whether the project uses Ruff (`pyproject.toml` [tool.ruff] or `ruff.toml`).
2. If the user specified files or directories, run Ruff on that scope; otherwise run on the whole project.
3. Fix auto-fixable offenses with `ruff check --fix .`; fix others manually.
4. Re-run Ruff to confirm offenses are resolved. Run tests/typecheck if needed.
