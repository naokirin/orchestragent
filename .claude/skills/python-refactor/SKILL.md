---
name: python-refactor
description: Refactoring Python code while preserving behaviour. Use when simplifying code, applying style/idiom rules, or improving structure.
user-invocable: false
---

# Python Refactor

## When to Use

- Simplifying code or removing duplication.
- Applying project style or idiom rules (naming, types, error handling).
- Improving structure (extracting functions, splitting modules) without changing behaviour.

## Principles

1. **Preserve behaviour**: Do not change observable behaviour; rely on existing tests.
2. **Small steps**: Prefer incremental changes; run typecheck, tests, and lint after each logical step.
3. **Verification**: After refactor, run typecheck, tests, and lint and confirm no new failures. Use `/run-typecheck-python`, `/run-tests-python`, `/run-lint-python` when available.
