"""Configuration for the agent system."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def is_running_in_container():
    """Check if running in container."""
    # Docker environment detection
    if os.path.exists('/.dockerenv'):
        return True
    # cgroup check
    try:
        with open('/proc/self/cgroup', 'r') as f:
            return 'docker' in f.read()
    except:
        pass
    return False


# Project root
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", ".")).resolve()

# Target project (optional) - this is the host-side path
TARGET_PROJECT = os.getenv("TARGET_PROJECT", None)
if TARGET_PROJECT:
    TARGET_PROJECT = Path(TARGET_PROJECT).resolve()

# LLM Configuration
LLM_BACKEND = os.getenv("LLM_BACKEND", "cursor_cli")
LLM_OUTPUT_FORMAT = os.getenv("LLM_OUTPUT_FORMAT", "text")
LLM_MODEL = os.getenv("LLM_MODEL", None)  # None = use default

# Agent-specific Model Configuration
# Each agent can have its own default model
# Falls back to LLM_MODEL if not set, then to None (use Cursor CLI default)
PLANNER_MODEL = os.getenv("PLANNER_MODEL", LLM_MODEL)
WORKER_MODEL = os.getenv("WORKER_MODEL", LLM_MODEL)  # Default model for workers
JUDGE_MODEL = os.getenv("JUDGE_MODEL", LLM_MODEL)

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

AGENT_CONFIG = {
    "project_root": str(WORKING_DIR),
    "project_goal": os.getenv("PROJECT_GOAL", "プロジェクトの目標を設定してください"),
    "mode": "plan",  # For planner
    "model": LLM_MODEL,
    "prompt_template": "prompts/planner.md"
}

# State Configuration
STATE_DIR = os.getenv("STATE_DIR", "state")

# Logging Configuration
LOG_DIR = os.getenv("LOG_DIR", "logs")
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
