"""Environment detection utilities for the orchestragent system."""

import os


def is_running_in_container() -> bool:
    """
    Check if running in container.

    Returns:
        True if running inside a Docker container, False otherwise.
    """
    # Docker environment detection
    if os.path.exists('/.dockerenv'):
        return True
    # cgroup check
    try:
        with open('/proc/self/cgroup', 'r') as f:
            return 'docker' in f.read()
    except:
        pass
    return False
