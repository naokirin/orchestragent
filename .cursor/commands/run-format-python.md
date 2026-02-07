# Run Format (Ruff / Black)

Format Python source files with Ruff or Black.

1. Run `ruff format .` or `black .` (or project format script) to format all configured files.
2. If the user specified a path, run the formatter on that path only.
3. Ensure no formatting-related changes are left unapplied; report any formatter errors.
