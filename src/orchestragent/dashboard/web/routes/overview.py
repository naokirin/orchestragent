"""Overview API: project goal, status, task statistics."""

from fastapi import APIRouter, Depends

from orchestragent.dashboard.web.deps import get_state_manager

router = APIRouter()


@router.get("/overview")
def get_overview(state=Depends(get_state_manager)):
    """Return overview data: project_goal, status (iteration, should_continue, reason), task_statistics."""
    from orchestragent import config
    status = state.get_status()
    stats = state.get_task_statistics()
    total = stats.total
    completion_rate = (stats.completed / total * 100) if total > 0 else 0
    return {
        "project_goal": config.AGENT_CONFIG.get("project_goal", "未設定"),
        "status": {
            "current_iteration": status.get("current_iteration", 0),
            "max_iterations": getattr(config, "MAX_ITERATIONS", 100),
            "should_continue": status.get("should_continue", True),
            "reason": status.get("reason", "N/A"),
            "last_updated": status.get("last_updated"),
        },
        "task_statistics": {
            "total": stats.total,
            "completed": stats.completed,
            "failed": stats.failed,
            "pending": stats.pending,
            "in_progress": stats.in_progress,
            "completion_rate_percent": round(completion_rate, 1),
        },
    }
