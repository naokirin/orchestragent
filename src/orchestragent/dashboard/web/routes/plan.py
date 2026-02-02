"""Plan API: read state/plan.md content for the dashboard plan tab."""

from fastapi import APIRouter, Depends

from orchestragent.dashboard.web.deps import get_state_manager

router = APIRouter()


@router.get("/plan")
def get_plan(state=Depends(get_state_manager)):
    """Return content of state/plan.md. Empty string if file does not exist."""
    content = state.load_text("plan.md")
    return {"content": content}
