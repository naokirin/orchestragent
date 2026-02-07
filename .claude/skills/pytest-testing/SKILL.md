---
name: pytest-testing
description: Adding or fixing tests with pytest. Use when writing tests, fixing failing tests, or improving test structure and coverage.
user-invocable: false
---

# pytest Testing

## When to Use

- Adding tests for new or existing modules (unit or integration).
- Fixing failing tests (determine whether the failure is in implementation or test; fix minimally).
- Improving test structure (fixtures, naming, setup) or readability.

## Principles

1. **Layout**: Place tests per project convention: `tests/` or `test_*.py`. Use clear test names and `assert` or pytest idioms.
2. **Assertions**: Prefer plain `assert` or pytest helpers. Keep expected values clear. Use `pytest.raises` for exception tests.
3. **Setup**: Use fixtures for shared setup; mock only when necessary; prefer real dependencies for integration-style tests when fast enough.
4. **Verification**: Run pytest to verify. Do not change behaviour beyond what is needed to fix the failure.
