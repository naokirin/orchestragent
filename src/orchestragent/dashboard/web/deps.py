"""Shared dependencies for web dashboard (config, StateManager)."""

import sys
from pathlib import Path

# Ensure project root is on path for config
# src/orchestragent/dashboard/web/deps.py -> 5 levels up = repo root
_repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if _repo_root not in [Path(p).resolve() for p in sys.path]:
    sys.path.insert(0, str(_repo_root))

import config
from orchestragent.state.manager import StateManager

_state_manager: StateManager | None = None


def get_state_manager() -> StateManager:
    """Return StateManager instance using config.STATE_DIR."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager(state_dir=config.STATE_DIR)
    return _state_manager
