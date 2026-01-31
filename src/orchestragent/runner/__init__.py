"""Runner layer for main loop and startup logic.

This module provides the main execution loop and startup utilities.
"""

from .startup import (
    check_cursor_cli,
    check_cursor_auth,
    authenticate_cursor,
    print_configuration,
)
from .loop import run_main_loop

__all__ = [
    "check_cursor_cli",
    "check_cursor_auth",
    "authenticate_cursor",
    "print_configuration",
    "run_main_loop",
]
