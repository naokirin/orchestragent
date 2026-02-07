---
description: Format Python source with Ruff or Black
---

# Run Format (Ruff / Black)

Format Python source files with Ruff or Black.

1. Check for Ruff or Black (pyproject.toml, or `ruff`/`black` in environment).
2. Run `ruff format .` or `black .` (or the project's format script) to format all configured files.
3. If the user specified a path, run the formatter on that path only.
4. Ensure no formatting-related changes are left unapplied; report any formatter errors.
