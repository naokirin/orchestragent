"""Settings API: project, LLM, loop config and environment info (read-only, safe fields only)."""

import sys
from fastapi import APIRouter, Depends

from orchestragent.dashboard.web.deps import get_state_manager

router = APIRouter()


@router.get("/settings")
def get_settings(state=Depends(get_state_manager)):
    """Return settings and environment info (no secrets)."""
    import config
    from orchestragent.core.environment import is_running_in_container
    from orchestragent.runner.startup import check_cursor_cli

    is_container = is_running_in_container()
    cursor_available = check_cursor_cli()

    return {
        "project": {
            "project_root": str(config.PROJECT_ROOT),
            "project_goal": config.AGENT_CONFIG.get("project_goal", "未設定"),
            "target_project": str(config.TARGET_PROJECT) if config.TARGET_PROJECT else None,
            "state_dir": config.STATE_DIR,
            "log_dir": config.LOG_DIR,
            "log_level": config.LOG_LEVEL,
        },
        "llm": {
            "backend": config.LLM_BACKEND,
            "output_format": config.LLM_OUTPUT_FORMAT,
            "default_model": config.LLM_MODEL or "(未設定)",
        },
        "models": {
            "planner_model": config.PLANNER_MODEL or "(デフォルト)",
            "worker_model": config.WORKER_MODEL or "(デフォルト)",
            "judge_model": config.JUDGE_MODEL or "(デフォルト)",
            "model_selection_enabled": config.MODEL_SELECTION_ENABLED,
            "worker_model_light": config.WORKER_MODEL_LIGHT or "(デフォルト)",
            "worker_model_standard": config.WORKER_MODEL_STANDARD or "(デフォルト)",
            "worker_model_powerful": config.WORKER_MODEL_POWERFUL or "(デフォルト)",
            "complexity_threshold_light": config.MODEL_COMPLEXITY_THRESHOLD_LIGHT,
            "complexity_threshold_powerful": config.MODEL_COMPLEXITY_THRESHOLD_POWERFUL,
        },
        "loop": {
            "wait_time_seconds": config.WAIT_TIME_SECONDS,
            "max_iterations": config.MAX_ITERATIONS,
            "max_retries": config.MAX_RETRIES,
            "enable_parallel_execution": config.ENABLE_PARALLEL_EXECUTION,
            "max_parallel_workers": config.MAX_PARALLEL_WORKERS if config.ENABLE_PARALLEL_EXECUTION else None,
        },
        "environment": {
            "running_in_container": is_container,
            "cursor_cli_available": cursor_available,
            "python_version": sys.version.split()[0],
        },
    }
