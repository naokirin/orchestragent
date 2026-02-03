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

# Per-agent backend configuration with fallback
# Format: "backend1:model1,backend2:model2,..."
# Example: "claude_code_cli:opus,cursor_cli:claude-3-5-sonnet"
# If model is omitted, falls back to backend-specific -> agent-specific -> global model
PLANNER_BACKENDS = os.getenv("PLANNER_BACKENDS", "")
WORKER_BACKENDS = os.getenv("WORKER_BACKENDS", "")
JUDGE_BACKENDS = os.getenv("JUDGE_BACKENDS", "")

# Per-backend default models (used when not specified in *_BACKENDS)
CURSOR_CLI_MODEL = _env_or_default("CURSOR_CLI_MODEL", None)
CLAUDE_CODE_CLI_MODEL = _env_or_default("CLAUDE_CODE_CLI_MODEL", None)
GEMINI_CLI_MODEL = _env_or_default("GEMINI_CLI_MODEL", None)

# Backend availability check (skip unavailable backends in fallback)
CHECK_BACKEND_AVAILABILITY = os.getenv("CHECK_BACKEND_AVAILABILITY", "true").lower() == "true"

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
    Resolve prompt file path. Priority: 1) env var  2) target project prompts/  3) default (repo prompts/).
    Users can customize agent prompts via env var or prompts/<name>.md in the target project.
    Input/output contract must follow PROMPT_CONTRACT.
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
    "prompt_template_finalize": resolve_prompt_path("PROMPT_PLANNER_FINALIZE", "planner_finalize.md"),
    "prompt_template_worker": resolve_prompt_path("PROMPT_WORKER", "worker.md"),
    "prompt_template_judge": resolve_prompt_path("PROMPT_JUDGE", "judge.md"),
    "prompt_template_plan_judge": resolve_prompt_path("PROMPT_PLAN_JUDGE", "plan_judge.md"),
    "system_prompts_dir": str(SYSTEM_PROMPTS_DIR),
}

# State / Log Configuration
# In container: fixed to /workspace/state, /workspace/logs.
# On host: resolve state, logs relative to cwd to absolute paths.
if is_running_in_container():
    STATE_DIR = "/workspace/state"
    LOG_DIR = "/workspace/logs"
else:
    STATE_DIR = str(Path("state").resolve())
    LOG_DIR = str(Path("logs").resolve())

# Checkpoints: compress older than latest to .tar.gz to reduce disk usage (for long runs)
COMPRESS_OLD_CHECKPOINTS = os.getenv("COMPRESS_OLD_CHECKPOINTS", "true").lower() == "true"

# ADR (Architecture Decision Records) Configuration
# In container: fixed to /workspace/docs/adr. On host: resolve docs/adr relative to cwd.
if is_running_in_container():
    ADR_DIR = "/workspace/docs/adr"
else:
    ADR_DIR = str(Path("docs/adr").resolve())

# For dashboard display: host paths for state / logs / adr.
# In container: show HOST_STATE_DIR etc. from compose if set, else container paths. On host: use STATE_DIR etc. as-is.
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
# Maximum number of Planner ↔ Plan_Judge rounds per iteration.
# If Plan_Judge keeps returning "revise" beyond this count, treat as plan convergence failure and exit the agent system.
MAX_PLAN_REVISIONS = int(os.getenv("MAX_PLAN_REVISIONS", "3"))
