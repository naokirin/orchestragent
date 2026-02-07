"""Logs API: read log file content (all logs by default, or single date)."""

import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from orchestragent.dashboard.web.deps import get_state_manager

router = APIRouter()

# execution_YYYYMMDD.log
_EXECUTION_LOG_PATTERN = re.compile(r"^execution_(\d{8})\.log$")
# agent_{agent_name}_{timestamp}_{thread_id}.log
_AGENT_LOG_PATTERN = re.compile(r"^agent_(.+?)_(\d{8}_\d{6})_(\d+)\.log$")

# エージェント名マッピング（表示名 -> ログファイル名パターン）
_AGENT_TYPES = ["Planner", "Plan_Judge", "Worker", "Judge"]


def _get_log_dir():
    from orchestragent import config

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
    date: str | None = Query(
        None, description="YYYY-MM-DD; single day only. Omit to get all logs."
    ),
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
            parts.append(
                f"=== {dt.strftime('%Y-%m-%d')} ({p.name}) ===\n(読込エラー: {e})"
            )
            paths.append(str(p))
    content = "\n\n".join(parts)
    return {"content": content, "path": "all", "paths": paths}


def _collect_agent_log_paths(log_dir: Path) -> dict[str, list[tuple[str, Path]]]:
    """Collect agent log paths grouped by agent type.

    Returns dict mapping agent_type -> list of (timestamp, path) sorted by timestamp descending.
    """
    result: dict[str, list[tuple[str, Path]]] = {agent: [] for agent in _AGENT_TYPES}

    for p in log_dir.iterdir():
        if not p.is_file():
            continue
        m = _AGENT_LOG_PATTERN.match(p.name)
        if not m:
            continue
        agent_name = m.group(1)
        timestamp = m.group(2)

        # マッチするエージェントタイプを探す
        for agent_type in _AGENT_TYPES:
            if agent_name == agent_type or agent_name.startswith(f"{agent_type}-"):
                result[agent_type].append((timestamp, p))
                break

    # タイムスタンプ降順でソート
    for agent_type in result:
        result[agent_type].sort(key=lambda x: x[0], reverse=True)

    return result


@router.get("/agent-logs")
def get_agent_logs_summary(state=Depends(get_state_manager)):
    """Return summary of agent logs: agent types and their execution counts."""
    log_dir = _get_log_dir()
    agent_logs = _collect_agent_log_paths(log_dir)

    agents = []
    for agent_type in _AGENT_TYPES:
        logs = agent_logs.get(agent_type, [])
        agents.append(
            {
                "name": agent_type,
                "execution_count": len(logs),
                "log_files": [{"timestamp": ts, "filename": p.name} for ts, p in logs],
            }
        )

    return {"agents": agents}


@router.get("/agent-logs/{agent_name}")
def get_agent_log_files(agent_name: str, state=Depends(get_state_manager)):
    """Return list of log files for a specific agent."""
    log_dir = _get_log_dir()
    agent_logs = _collect_agent_log_paths(log_dir)

    if agent_name not in agent_logs:
        return {
            "agent_name": agent_name,
            "log_files": [],
            "error": "Unknown agent type",
        }

    logs = agent_logs[agent_name]
    return {
        "agent_name": agent_name,
        "execution_count": len(logs),
        "log_files": [{"timestamp": ts, "filename": p.name} for ts, p in logs],
    }


@router.get("/agent-logs/{agent_name}/{filename}")
def get_agent_log_content(
    agent_name: str, filename: str, state=Depends(get_state_manager)
):
    """Return content of a specific agent log file."""
    log_dir = _get_log_dir()
    log_path = log_dir / filename

    # セキュリティ: ファイル名が期待パターンに一致するか確認
    if not _AGENT_LOG_PATTERN.match(filename):
        return {"content": "", "error": "Invalid filename pattern"}

    if not log_path.exists():
        return {"content": "", "path": str(log_path), "error": "File not found"}

    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
        return {"content": content, "path": str(log_path), "filename": filename}
    except Exception as e:
        return {"content": f"(読込エラー: {e})", "path": str(log_path), "error": str(e)}
