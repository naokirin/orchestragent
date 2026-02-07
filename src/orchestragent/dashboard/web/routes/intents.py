"""Intents API: list and intent detail with optional diff (read-only)."""

from fastapi import APIRouter, Depends, HTTPException

from orchestragent.dashboard.web.deps import get_state_manager

router = APIRouter()


def _get_intent_manager():
    from orchestragent import config
    from orchestragent.tracking.intent_manager import IntentManager

    return IntentManager(state_dir=config.STATE_DIR)


def _get_adr_manager():
    from orchestragent import config
    from orchestragent.tracking.adr_manager import ADRManager

    return ADRManager(adr_dir=getattr(config, "ADR_DIR", "docs/adr"))


def _get_git_helper():
    from orchestragent import config
    from orchestragent.tracking.git_helper import GitHelper

    return GitHelper(repo_path=str(config.WORKING_DIR) if config.WORKING_DIR else ".")


@router.get("/intents")
def list_intents(state=Depends(get_state_manager)):
    """Return list of intents with task_id, goal_display, commit_count, related_adr."""
    intent_mgr = _get_intent_manager()
    intents = intent_mgr.get_all_intents()
    out = []
    for i in intents:
        task_id = i.get("task_id", "N/A")
        goal = (i.get("intent") or {}).get("goal", "") or "No goal"
        goal_display = goal[:35] + "..." if len(goal) > 35 else goal
        commits = i.get("commits", [])
        related_adr = i.get("related_adr") or "-"
        out.append(
            {
                "task_id": task_id,
                "goal_display": goal_display,
                "commit_count": len(commits),
                "related_adr": related_adr,
            }
        )
    return {"intents": out}


@router.get("/intents/{task_id}")
def get_intent(task_id: str, state=Depends(get_state_manager)):
    """Return intent detail and optional diff text for commits."""
    intent_mgr = _get_intent_manager()
    intent_data = intent_mgr.get_intent(task_id)
    if not intent_data:
        raise HTTPException(status_code=404, detail="Intent not found")
    intent_inner = intent_data.get("intent") or {}
    commits = intent_data.get("commits", [])
    git = _get_git_helper()
    diff_parts = []
    for c in commits:
        h = c.get("hash")
        if not h:
            continue
        info = git.get_commit_info(h)
        if info:
            diff_parts.append(
                f"Commit: {info.get('hash', h)[:7]}\n{info.get('message', '')}\n"
            )
        diff_text = git.get_commit_diff(h)
        if diff_text:
            diff_parts.append(diff_text[:2000])
            diff_parts.append("\n")
    return {
        "task_id": intent_data.get("task_id"),
        "created_at": intent_data.get("created_at"),
        "updated_at": intent_data.get("updated_at"),
        "intent": {
            "goal": intent_inner.get("goal"),
            "rationale": intent_inner.get("rationale"),
            "expected_change": intent_inner.get("expected_change", []),
            "non_goals": intent_inner.get("non_goals", []),
            "risk": intent_inner.get("risk", []),
        },
        "commits": [
            {"hash": c.get("hash"), "message": c.get("message")} for c in commits
        ],
        "related_adr": intent_data.get("related_adr"),
        "diff_text": "\n".join(diff_parts) if diff_parts else None,
    }
