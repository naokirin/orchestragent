"""Tasks API: list and task detail (read-only)."""

from fastapi import APIRouter, Depends, HTTPException

from orchestragent.dashboard.web.deps import get_state_manager

router = APIRouter()


@router.get("/tasks")
def list_tasks(state=Depends(get_state_manager)):
    """Return list of tasks with id, title, status, priority."""
    all_tasks = state.get_all_tasks_from_files()
    return {
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                "priority": t.priority.value if hasattr(t.priority, "value") else str(t.priority),
            }
            for t in all_tasks
        ]
    }


@router.get("/tasks/{task_id}")
def get_task(task_id: str, state=Depends(get_state_manager)):
    """Return full task detail by id."""
    task = state.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    d = task.to_dict()
    # Ensure result is serializable
    if d.get("result") and hasattr(d["result"], "to_dict"):
        d["result"] = d["result"].to_dict()
    return d
