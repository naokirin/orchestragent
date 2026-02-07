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


def _env_or_none(name: str) -> str | None:
    """Get environment variable value, treating empty string as None."""
    value = os.getenv(name, None)
    if value is None or value == "":
        return None
    return value


# ===========================================
# LLM Backend Configuration
# ===========================================
# Default backend (used when *_BACKENDS is not set)
LLM_BACKEND = os.getenv("LLM_BACKEND", "cursor_cli")
LLM_OUTPUT_FORMAT = os.getenv("LLM_OUTPUT_FORMAT", "text")

# Per-agent backend configuration (priority order with fallback)
# Format: "backend1:model1,backend2:model2,..."
# Example: "claude_code_cli:opus,cursor_cli" (Cursor CLI uses its default model)
PLANNER_BACKENDS = os.getenv("PLANNER_BACKENDS", "")
WORKER_BACKENDS = os.getenv("WORKER_BACKENDS", "")
JUDGE_BACKENDS = os.getenv("JUDGE_BACKENDS", "")

# Per-backend default models
# Used when model is not specified in *_BACKENDS
CURSOR_CLI_MODEL = _env_or_none("CURSOR_CLI_MODEL")
CLAUDE_CODE_CLI_MODEL = _env_or_none("CLAUDE_CODE_CLI_MODEL")
GEMINI_CLI_MODEL = _env_or_none("GEMINI_CLI_MODEL")

# Backend availability check (skip unavailable backends in fallback)
CHECK_BACKEND_AVAILABILITY = os.getenv("CHECK_BACKEND_AVAILABILITY", "true").lower() == "true"

# ===========================================
# Dynamic Model Selection (Worker only)
# ===========================================
# When enabled, Worker selects model tier based on task complexity
MODEL_SELECTION_ENABLED = os.getenv("MODEL_SELECTION_ENABLED", "false").lower() == "true"
MODEL_COMPLEXITY_THRESHOLD_LIGHT = float(os.getenv("MODEL_COMPLEXITY_THRESHOLD_LIGHT", "10.0"))
MODEL_COMPLEXITY_THRESHOLD_POWERFUL = float(os.getenv("MODEL_COMPLEXITY_THRESHOLD_POWERFUL", "30.0"))

# Per-backend dynamic models (falls back to *_CLI_MODEL if not set)
CURSOR_CLI_MODEL_LIGHT = _env_or_none("CURSOR_CLI_MODEL_LIGHT") or CURSOR_CLI_MODEL
CURSOR_CLI_MODEL_STANDARD = _env_or_none("CURSOR_CLI_MODEL_STANDARD") or CURSOR_CLI_MODEL
CURSOR_CLI_MODEL_POWERFUL = _env_or_none("CURSOR_CLI_MODEL_POWERFUL") or CURSOR_CLI_MODEL

CLAUDE_CODE_CLI_MODEL_LIGHT = _env_or_none("CLAUDE_CODE_CLI_MODEL_LIGHT") or CLAUDE_CODE_CLI_MODEL
CLAUDE_CODE_CLI_MODEL_STANDARD = _env_or_none("CLAUDE_CODE_CLI_MODEL_STANDARD") or CLAUDE_CODE_CLI_MODEL
CLAUDE_CODE_CLI_MODEL_POWERFUL = _env_or_none("CLAUDE_CODE_CLI_MODEL_POWERFUL") or CLAUDE_CODE_CLI_MODEL

GEMINI_CLI_MODEL_LIGHT = _env_or_none("GEMINI_CLI_MODEL_LIGHT") or GEMINI_CLI_MODEL
GEMINI_CLI_MODEL_STANDARD = _env_or_none("GEMINI_CLI_MODEL_STANDARD") or GEMINI_CLI_MODEL
GEMINI_CLI_MODEL_POWERFUL = _env_or_none("GEMINI_CLI_MODEL_POWERFUL") or GEMINI_CLI_MODEL

# ===========================================
# Agent Configuration
# ===========================================
# Determine working directory:
# - In container: Use PROJECT_ROOT (which should be /target when TARGET_PROJECT is set)
# - On host: Use TARGET_PROJECT if set, otherwise PROJECT_ROOT
if is_running_in_container():
    WORKING_DIR = PROJECT_ROOT
else:
    WORKING_DIR = TARGET_PROJECT if TARGET_PROJECT else PROJECT_ROOT

# Default prompts directory (orchestragent repo root when config.py lives there)
_DEFAULT_PROMPTS_DIR = Path(__file__).parent / "prompts"
# System-only templates (context / output format); not user-overridable by path
SYSTEM_PROMPTS_DIR = _DEFAULT_PROMPTS_DIR / "system"


def resolve_prompt_path(env_key: str, default_filename: str) -> str:
    """
    Resolve prompt file path. Priority: 1) env var  2) target project prompts/  3) default (repo prompts/).
    """
    env_val = os.getenv(env_key)
    if env_val:
        p = Path(env_val)
        if p.is_absolute() and p.exists():
            return str(p)
        if p.is_absolute():
            return env_val
        candidate = WORKING_DIR / p
        if candidate.exists():
            return str(candidate.resolve())
        return str(Path(env_val).resolve())
    project_prompt = Path(WORKING_DIR) / "prompts" / default_filename
    if project_prompt.exists():
        return str(project_prompt.resolve())
    default_path = _DEFAULT_PROMPTS_DIR / default_filename
    return str(default_path.resolve() if default_path.exists() else str(default_path))


AGENT_CONFIG = {
    "project_root": str(WORKING_DIR),
    "project_goal": os.getenv("PROJECT_GOAL", "プロジェクトの目標を設定してください"),
    "mode": "plan",  # For planner
    "prompt_template": resolve_prompt_path("PROMPT_PLANNER", "planner.md"),
    "prompt_template_finalize": resolve_prompt_path("PROMPT_PLANNER_FINALIZE", "planner_finalize.md"),
    "prompt_template_worker": resolve_prompt_path("PROMPT_WORKER", "worker.md"),
    "prompt_template_judge": resolve_prompt_path("PROMPT_JUDGE", "judge.md"),
    "prompt_template_plan_judge": resolve_prompt_path("PROMPT_PLAN_JUDGE", "plan_judge.md"),
    "system_prompts_dir": str(SYSTEM_PROMPTS_DIR),
}

# ===========================================
# State / Log Configuration
# ===========================================
if is_running_in_container():
    STATE_DIR = "/workspace/state"
    LOG_DIR = "/workspace/logs"
else:
    STATE_DIR = str(Path("state").resolve())
    LOG_DIR = str(Path("logs").resolve())

# Checkpoints: compress older than latest to .tar.gz to reduce disk usage
COMPRESS_OLD_CHECKPOINTS = os.getenv("COMPRESS_OLD_CHECKPOINTS", "true").lower() == "true"

# ADR (Architecture Decision Records) Configuration
if is_running_in_container():
    ADR_DIR = "/workspace/docs/adr"
else:
    ADR_DIR = str(Path("docs/adr").resolve())

# For dashboard display: host paths for state / logs / adr
def _display_dir(env_key: str, fallback: str) -> str:
    host_path = os.getenv(env_key)
    return host_path if host_path else fallback


if is_running_in_container():
    DISPLAY_STATE_DIR = _display_dir("HOST_STATE_DIR", STATE_DIR)
    DISPLAY_LOG_DIR = _display_dir("HOST_LOG_DIR", LOG_DIR)
    DISPLAY_ADR_DIR = _display_dir("HOST_ADR_DIR", ADR_DIR)
else:
    DISPLAY_STATE_DIR = STATE_DIR
    DISPLAY_LOG_DIR = LOG_DIR
    DISPLAY_ADR_DIR = ADR_DIR

# ===========================================
# Git Configuration
# ===========================================
GIT_USER_NAME = os.getenv("GIT_USER_NAME", "")
GIT_USER_EMAIL = os.getenv("GIT_USER_EMAIL", "")

# ===========================================
# Logging Configuration
# ===========================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FSYNC = os.getenv("LOG_FSYNC", "false").lower() == "true"

# ===========================================
# Main Loop Configuration
# ===========================================
WAIT_TIME_SECONDS = int(os.getenv("WAIT_TIME_SECONDS", "60"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "100"))

# ===========================================
# Error Handling Configuration
# ===========================================
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# ===========================================
# Parallel Execution Configuration
# ===========================================
MAX_PARALLEL_WORKERS = int(os.getenv("MAX_PARALLEL_WORKERS", "3"))
ENABLE_PARALLEL_EXECUTION = os.getenv("ENABLE_PARALLEL_EXECUTION", "true").lower() == "true"

# ===========================================
# Planning Review Configuration
# ===========================================
MAX_PLAN_REVISIONS = int(os.getenv("MAX_PLAN_REVISIONS", "3"))

# Plan_Judge: score がこの値未満のときは accept を revise に上書きする（0.0 = 無効、LLM の decision をそのまま使用）
PLAN_JUDGE_ACCEPT_THRESHOLD = float(os.getenv("PLAN_JUDGE_ACCEPT_THRESHOLD", "0.0"))
