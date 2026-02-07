---
description: Run mypy or pyright type checker
---

# Run Typecheck

Run the type checker (mypy or pyright) in check-only mode.

1. Run `mypy src` or `pyright` (or project typecheck script).
2. Parse the output for type errors; fix with minimal changes. Avoid `# type: ignore` or `Any` unless justified.
3. Re-run typecheck to confirm no errors remain.

Output a short summary of any errors fixed.
