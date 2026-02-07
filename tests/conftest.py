"""Pytest configuration and shared fixtures."""

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, Optional

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orchestragent.models.task import (
    Task,
    TaskIndex,
    TaskPriority,
    TaskResult,
    TasksFile,
    TaskStatus,
)
from orchestragent.llm.client import LLMClient


# ============================================================================
# Mock Classes
# ============================================================================


class MockLLMClient(LLMClient):
    """Mock LLM client for testing without actual API calls."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """
        Initialize mock client.

        Args:
            responses: Dictionary mapping prompt patterns to responses.
                       If None, returns a default response.
        """
        self.responses = responses or {}
        self.call_history: list[Dict[str, Any]] = []
        self.default_response = '{"status": "ok", "message": "Mock response"}'

    def call_agent(
        self,
        prompt: str,
        mode: str = "agent",
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Mock agent call that records the call and returns configured response."""
        self.call_history.append({
            "prompt": prompt,
            "mode": mode,
            "model": model,
            "kwargs": kwargs,
        })

        # Check for matching response pattern
        for pattern, response in self.responses.items():
            if pattern in prompt:
                return response

        return self.default_response

    def call_agent_from_file(
        self,
        prompt_file: str,
        mode: str = "agent",
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Mock agent call from file."""
        prompt = f"[From file: {prompt_file}]"
        return self.call_agent(prompt, mode, model, **kwargs)

    def set_response(self, pattern: str, response: str) -> None:
        """Set a response for a specific prompt pattern."""
        self.responses[pattern] = response

    def get_last_call(self) -> Optional[Dict[str, Any]]:
        """Get the most recent call."""
        return self.call_history[-1] if self.call_history else None

    def reset(self) -> None:
        """Reset call history and responses."""
        self.call_history.clear()
        self.responses.clear()


# ============================================================================
# Fixtures: Temporary Directories
# ============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_state_dir(temp_dir: Path) -> Path:
    """Create a temporary state directory structure."""
    state_dir = temp_dir / "state"
    state_dir.mkdir()
    (state_dir / "tasks").mkdir()
    (state_dir / "results").mkdir()
    (state_dir / "checkpoints").mkdir()
    (state_dir / "backups").mkdir()
    return state_dir


# ============================================================================
# Fixtures: State Manager
# ============================================================================


@pytest.fixture
def state_manager(temp_state_dir: Path):
    """Create a StateManager with temporary directory."""
    from orchestragent.state.manager import StateManager

    return StateManager(
        state_dir=str(temp_state_dir),
        backup_dir=str(temp_state_dir / "backups"),
    )


# ============================================================================
# Fixtures: Mock LLM Client
# ============================================================================


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """Create a mock LLM client."""
    return MockLLMClient()


# ============================================================================
# Fixtures: Sample Data
# ============================================================================


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        id="task-001",
        title="Test Task",
        description="A test task for unit testing",
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.PENDING,
        files=["src/main.py", "tests/test_main.py"],
        dependencies=[],
        estimated_hours=2.0,
    )


@pytest.fixture
def sample_task_dict() -> Dict[str, Any]:
    """Create a sample task dictionary."""
    return {
        "id": "task-001",
        "title": "Test Task",
        "description": "A test task for unit testing",
        "priority": "medium",
        "status": "pending",
        "files": ["src/main.py", "tests/test_main.py"],
        "dependencies": [],
        "estimated_hours": 2.0,
    }


@pytest.fixture
def sample_tasks_file() -> TasksFile:
    """Create a sample tasks file structure."""
    return TasksFile(
        tasks=[
            TaskIndex(id="task-001", title="Task 1", priority=TaskPriority.HIGH),
            TaskIndex(id="task-002", title="Task 2", priority=TaskPriority.MEDIUM),
            TaskIndex(id="task-003", title="Task 3", priority=TaskPriority.LOW),
        ],
        next_task_id=4,
        version=1,
    )


@pytest.fixture
def sample_completed_task() -> Task:
    """Create a sample completed task."""
    return Task(
        id="task-002",
        title="Completed Task",
        description="A completed task",
        priority=TaskPriority.HIGH,
        status=TaskStatus.COMPLETED,
        result=TaskResult(
            report="Task completed successfully",
            success=True,
        ),
    )


@pytest.fixture
def sample_failed_task() -> Task:
    """Create a sample failed task."""
    return Task(
        id="task-003",
        title="Failed Task",
        description="A failed task",
        priority=TaskPriority.LOW,
        status=TaskStatus.FAILED,
        error="Test error message",
        result=TaskResult(
            report="Task failed",
            success=False,
            error_message="Test error message",
        ),
    )


# ============================================================================
# Fixtures: JSON Files
# ============================================================================


@pytest.fixture
def tasks_json_file(temp_state_dir: Path, sample_tasks_file: TasksFile) -> Path:
    """Create a tasks.json file in the temporary state directory."""
    tasks_file = temp_state_dir / "tasks.json"
    with open(tasks_file, "w", encoding="utf-8") as f:
        json.dump(sample_tasks_file.to_dict(), f, indent=2)
    return tasks_file


@pytest.fixture
def task_file(temp_state_dir: Path, sample_task: Task) -> Path:
    """Create an individual task file."""
    task_file = temp_state_dir / "tasks" / f"{sample_task.id}.json"
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(sample_task.to_dict(), f, indent=2)
    return task_file


# ============================================================================
# Fixtures: Environment
# ============================================================================


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables for testing."""
    env_vars_to_clear = [
        "ORCHESTRAGENT_STATE_DIR",
        "ORCHESTRAGENT_LOG_LEVEL",
        "ORCHESTRAGENT_DEBUG",
    ]
    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def mock_config(monkeypatch, temp_state_dir: Path):
    """Mock configuration for testing."""
    monkeypatch.setattr("orchestragent.config.STATE_DIR", str(temp_state_dir))
    monkeypatch.setattr("orchestragent.config.LOG_DIR", str(temp_state_dir / "logs"))


# ============================================================================
# Helper Functions
# ============================================================================


def create_task_with_status(
    task_id: str,
    status: TaskStatus,
    title: str = "Test Task",
) -> Task:
    """Helper to create a task with specific status."""
    return Task(
        id=task_id,
        title=title,
        description=f"Task with status {status.value}",
        status=status,
    )


def assert_task_equal(task1: Task, task2: Task, ignore_timestamps: bool = True) -> None:
    """Assert two tasks are equal, optionally ignoring timestamps."""
    assert task1.id == task2.id
    assert task1.title == task2.title
    assert task1.description == task2.description
    assert task1.priority == task2.priority
    assert task1.status == task2.status
    assert task1.files == task2.files
    assert task1.dependencies == task2.dependencies

    if not ignore_timestamps:
        assert task1.created_at == task2.created_at
        assert task1.updated_at == task2.updated_at
