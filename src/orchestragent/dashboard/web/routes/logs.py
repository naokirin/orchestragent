"""Logs API: read log file content (all logs by default, or single date)."""

import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from orchestragent.dashboard.web.deps import get_state_manager

router = APIRouter()

# execution_YYYYMMDD.log
_EXECUTION_LOG_PATTERN = re.compile(r"^execution_(\d{8})\.log$")


def _get_log_dir():
    import config
    return Path(config.LOG_DIR)


def _collect_all_log_paths(log_dir: Path) -> list[tuple[datetime, Path]]:
    """Collect execution_*.log paths and return (date, path) sorted by date ascending."""
    entries: list[tuple[datetime, Path]] = []
    for p in log_dir.iterdir():
        if not p.is_file():
            continue
        m = _EXECUTION_LOG_PATTERN.match(p.name)
        if not m:
            continue
        try:
            dt = datetime.strptime(m.group(1), "%Y%m%d")
            entries.append((dt, p))
        except ValueError:
            continue
    entries.sort(key=lambda x: x[0])
    return entries


@router.get("/logs")
def get_logs(
    date: str | None = Query(None, description="YYYY-MM-DD; single day only. Omit to get all logs."),
    state=Depends(get_state_manager),
):
    """Return log file content. Without date: all execution_*.log files (chronological). With date: that day only."""
    log_dir = _get_log_dir()
    if date:
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            log_name = f"execution_{dt.strftime('%Y%m%d')}.log"
        except ValueError:
            log_name = f"execution_{datetime.now().strftime('%Y%m%d')}.log"
        log_path = log_dir / log_name
        if not log_path.exists():
            return {"content": "", "path": str(log_path)}
        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
            return {"content": content, "path": str(log_path)}
        except Exception as e:
            return {"content": f"(読込エラー: {e})", "path": str(log_path)}

    # No date: return all execution_*.log in chronological order
    entries = _collect_all_log_paths(log_dir)
    if not entries:
        return {"content": "", "path": "all"}
    parts: list[str] = []
    paths: list[str] = []
    for dt, p in entries:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            paths.append(str(p))
            if text.strip():
                parts.append(f"=== {dt.strftime('%Y-%m-%d')} ({p.name}) ===\n{text}")
            else:
                parts.append(f"=== {dt.strftime('%Y-%m-%d')} ({p.name}) ===\n(空)")
        except Exception as e:
            parts.append(f"=== {dt.strftime('%Y-%m-%d')} ({p.name}) ===\n(読込エラー: {e})")
            paths.append(str(p))
    content = "\n\n".join(parts)
    return {"content": content, "path": "all", "paths": paths}
