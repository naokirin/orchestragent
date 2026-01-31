"""Logs API: read log file content (date query or today)."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from orchestragent.dashboard.web.deps import get_state_manager

router = APIRouter()


def _get_log_dir():
    import config
    return Path(config.LOG_DIR)


@router.get("/logs")
def get_logs(
    date: str | None = Query(None, description="YYYY-MM-DD; default today"),
    state=Depends(get_state_manager),
):
    """Return log file content for the given date (or today)."""
    log_dir = _get_log_dir()
    if date:
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            log_name = f"execution_{dt.strftime('%Y%m%d')}.log"
        except ValueError:
            log_name = f"execution_{datetime.now().strftime('%Y%m%d')}.log"
    else:
        log_name = f"execution_{datetime.now().strftime('%Y%m%d')}.log"
    log_path = log_dir / log_name
    if not log_path.exists():
        return {"content": "", "path": str(log_path)}
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
        return {"content": content, "path": str(log_path)}
    except Exception as e:
        return {"content": f"(読込エラー: {e})", "path": str(log_path)}
