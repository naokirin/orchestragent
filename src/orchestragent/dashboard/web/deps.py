"""Shared dependencies for web dashboard (config, StateManager)."""

from orchestragent import config
from orchestragent.state.manager import StateManager

_state_manager: StateManager | None = None


def get_state_manager() -> StateManager:
    """Return StateManager instance using config.STATE_DIR."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager(state_dir=config.STATE_DIR)
    return _state_manager
