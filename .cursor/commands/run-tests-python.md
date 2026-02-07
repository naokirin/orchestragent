# Run Tests and Fix Failures

Run the pytest suite and fix any failures using the **python-tester** agent.

- Determine the test layout from the project (e.g. `tests/`, `test_*.py`, `pytest.ini` or `pyproject.toml`).
- If the user specified a path or pattern, run tests for that scope: `pytest path/to/test_file.py` or `pytest -k "pattern"`.
- Otherwise run the full suite: `pytest`.
- Fix failures and re-run until the relevant tests pass.
