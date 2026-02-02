"""Configuration for the agent system."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path for package imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load environment variables
load_dotenv()

# Import from new package structure
from orchestragent.core.environment import is_running_in_container


# Project root
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", ".")).resolve()

# Target project (optional) - this is the host-side path
TARGET_PROJECT = os.getenv("TARGET_PROJECT", None)
if TARGET_PROJECT:
    TARGET_PROJECT = Path(TARGET_PROJECT).resolve()

def _env_or_default(name: str, default: str | None) -> str | None:
    """
    Get environment variable value or default, treating empty string as unset.
    
    This ensures that when docker-compose passes empty env vars like
    PLANNER_MODEL="", we still correctly fall back to LLM_MODEL.
    """
    value = os.getenv(name, None)
    if value is None or value == "":
        return default
    return value


# LLM Configuration
LLM_BACKEND = os.getenv("LLM_BACKEND", "cursor_cli")
LLM_OUTPUT_FORMAT = os.getenv("LLM_OUTPUT_FORMAT", "text")
LLM_MODEL = os.getenv("LLM_MODEL", None)  # None = use Cursor CLI default

# Agent-specific Model Configuration
# Each agent can have its own default model
# Falls back to LLM_MODEL if not set or empty, then to None (use Cursor CLI default)
PLANNER_MODEL = _env_or_default("PLANNER_MODEL", LLM_MODEL)
WORKER_MODEL = _env_or_default("WORKER_MODEL", LLM_MODEL)  # Default model for workers
JUDGE_MODEL = _env_or_default("JUDGE_MODEL", LLM_MODEL)

# Dynamic Model Selection for Workers
# These models are used when dynamic selection is enabled
WORKER_MODEL_LIGHT = os.getenv("WORKER_MODEL_LIGHT", WORKER_MODEL)  # For simple tasks
WORKER_MODEL_STANDARD = os.getenv("WORKER_MODEL_STANDARD", WORKER_MODEL)  # For standard tasks
WORKER_MODEL_POWERFUL = os.getenv("WORKER_MODEL_POWERFUL", WORKER_MODEL)  # For complex tasks

# Model Selection Configuration
MODEL_SELECTION_ENABLED = os.getenv("MODEL_SELECTION_ENABLED", "false").lower() == "true"
MODEL_COMPLEXITY_THRESHOLD_LIGHT = float(os.getenv("MODEL_COMPLEXITY_THRESHOLD_LIGHT", "10.0"))
MODEL_COMPLEXITY_THRESHOLD_POWERFUL = float(os.getenv("MODEL_COMPLEXITY_THRESHOLD_POWERFUL", "30.0"))

# Agent Configuration
# Determine working directory:
# - In container: Use PROJECT_ROOT (which should be /target when TARGET_PROJECT is set)
# - On host: Use TARGET_PROJECT if set, otherwise PROJECT_ROOT
if is_running_in_container():
    # In container, always use PROJECT_ROOT (which is set to /target in docker-compose)
    WORKING_DIR = PROJECT_ROOT
else:
    # On host, use TARGET_PROJECT if set, otherwise PROJECT_ROOT
    WORKING_DIR = TARGET_PROJECT if TARGET_PROJECT else PROJECT_ROOT

# Default prompts directory (orchestragent repo root when config.py lives there)
_DEFAULT_PROMPTS_DIR = Path(__file__).parent / "prompts"
# System-only templates (context / output format); not user-overridable by path
SYSTEM_PROMPTS_DIR = _DEFAULT_PROMPTS_DIR / "system"


def resolve_prompt_path(env_key: str, default_filename: str) -> str:
    """
    プロンプトファイルのパスを解決する。
    優先順位: 1) 環境変数  2) 対象プロジェクトの prompts/  3) デフォルト（repo 内 prompts/）
    ユーザーは環境変数または対象プロジェクトに prompts/<name>.md を置くことで
    各エージェントのプロンプトをカスタマイズできる。入出力の契約は PROMPT_CONTRACT に従うこと。
    """
    env_val = os.getenv(env_key)
    if env_val:
        p = Path(env_val)
        if p.is_absolute() and p.exists():
            return str(p)
        if p.is_absolute():
            return env_val
        # Relative: try WORKING_DIR first (project-specific)
        candidate = WORKING_DIR / p
        if candidate.exists():
            return str(candidate.resolve())
        # Fallback: resolve against cwd
        return str(Path(env_val).resolve())
    # Project-specific: WORKING_DIR/prompts/<default_filename>
    project_prompt = Path(WORKING_DIR) / "prompts" / default_filename
    if project_prompt.exists():
        return str(project_prompt.resolve())
    # Default: repo prompts/
    default_path = _DEFAULT_PROMPTS_DIR / default_filename
    return str(default_path.resolve() if default_path.exists() else str(default_path))


AGENT_CONFIG = {
    "project_root": str(WORKING_DIR),
    "project_goal": os.getenv("PROJECT_GOAL", "プロジェクトの目標を設定してください"),
    "mode": "plan",  # For planner
    "model": LLM_MODEL,
    "prompt_template": resolve_prompt_path("PROMPT_PLANNER", "planner.md"),
    "prompt_template_worker": resolve_prompt_path("PROMPT_WORKER", "worker.md"),
    "prompt_template_judge": resolve_prompt_path("PROMPT_JUDGE", "judge.md"),
    "prompt_template_plan_judge": resolve_prompt_path("PROMPT_PLAN_JUDGE", "plan_judge.md"),
    "system_prompts_dir": str(SYSTEM_PROMPTS_DIR),
}

# State / Log Configuration
# コンテナ内では常に /workspace/state, /workspace/logs に固定。
# ホストで実行する場合はカレントディレクトリ基準の state, logs を絶対パスに解決する。
if is_running_in_container():
    STATE_DIR = "/workspace/state"
    LOG_DIR = "/workspace/logs"
else:
    STATE_DIR = str(Path("state").resolve())
    LOG_DIR = str(Path("logs").resolve())

# チェックポイント: 最新以外を .tar.gz に圧縮してディスク使用量を削減（長時間稼働向け）
COMPRESS_OLD_CHECKPOINTS = os.getenv("COMPRESS_OLD_CHECKPOINTS", "true").lower() == "true"

# ADR (Architecture Decision Records) Configuration
# コンテナ内では常に /workspace/docs/adr に固定。ホストではカレント基準の docs/adr を絶対パスに解決。
if is_running_in_container():
    ADR_DIR = "/workspace/docs/adr"
else:
    ADR_DIR = str(Path("docs/adr").resolve())

# ダッシュボード表示用: state / logs / adr のホスト側パス。
# コンテナ内では HOST_STATE_DIR / HOST_LOG_DIR / HOST_ADR_DIR が compose から渡されていればそれを表示、
# 未設定ならコンテナ内パス（STATE_DIR 等）を表示。ホスト実行時は STATE_DIR 等＝ホストパスをそのまま表示。
def _display_dir(env_key: str, fallback: str) -> str:
    host_path = os.getenv(env_key)
    if host_path:
        return host_path
    return fallback


if is_running_in_container():
    DISPLAY_STATE_DIR = _display_dir("HOST_STATE_DIR", STATE_DIR)
    DISPLAY_LOG_DIR = _display_dir("HOST_LOG_DIR", LOG_DIR)
    DISPLAY_ADR_DIR = _display_dir("HOST_ADR_DIR", ADR_DIR)
else:
    DISPLAY_STATE_DIR = STATE_DIR
    DISPLAY_LOG_DIR = LOG_DIR
    DISPLAY_ADR_DIR = ADR_DIR

# Git configuration (used by agents for commits)
GIT_USER_NAME = os.getenv("GIT_USER_NAME", "")
GIT_USER_EMAIL = os.getenv("GIT_USER_EMAIL", "")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FSYNC = os.getenv("LOG_FSYNC", "false").lower() == "true"

# Main Loop Configuration
WAIT_TIME_SECONDS = int(os.getenv("WAIT_TIME_SECONDS", "60"))  # Wait time between agent runs (in seconds)
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "100"))  # Maximum iterations

# Error Handling Configuration
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))  # Maximum retries for retryable errors

# Parallel Execution Configuration
MAX_PARALLEL_WORKERS = int(os.getenv("MAX_PARALLEL_WORKERS", "3"))  # Maximum parallel workers
ENABLE_PARALLEL_EXECUTION = os.getenv("ENABLE_PARALLEL_EXECUTION", "true").lower() == "true"  # Enable parallel execution

# Planning Review Configuration
# 1イテレーション内で Planner ↔ Plan_Judge を何回まで往復するかの最大回数。
# この回数を超えても Plan_Judge が「revise」を返す場合は、計画の収束に失敗したとみなし、
# イテレーション数が残っていてもエージェントシステム全体を失敗として終了させる。
MAX_PLAN_REVISIONS = int(os.getenv("MAX_PLAN_REVISIONS", "3"))
