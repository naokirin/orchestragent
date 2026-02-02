"""Tests for data models."""

import pytest
from datetime import datetime

from orchestragent.models import Status, CheckpointMetadata, ValidationResult
from orchestragent.models.task import (
    Task,
    TaskIndex,
    TaskPriority,
    TaskResult,
    TasksFile,
    TaskStatistics,
    TaskStatus,
    can_transition,
    validate_task_status_transition,
)


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_status_values(self):
        """Test that all expected status values exist."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"

    def test_status_from_string(self):
        """Test creating status from string."""
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("completed") == TaskStatus.COMPLETED


class TestTaskStatusTransition:
    """Tests for task status transition validation (state machine)."""

    def test_can_transition_pending_to_in_progress(self):
        """PENDING -> IN_PROGRESS is allowed."""
        assert can_transition(TaskStatus.PENDING, TaskStatus.IN_PROGRESS) is True

    def test_can_transition_in_progress_to_completed(self):
        """IN_PROGRESS -> COMPLETED is allowed."""
        assert can_transition(TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED) is True

    def test_can_transition_in_progress_to_failed(self):
        """IN_PROGRESS -> FAILED is allowed."""
        assert can_transition(TaskStatus.IN_PROGRESS, TaskStatus.FAILED) is True

    def test_can_transition_in_progress_to_pending(self):
        """IN_PROGRESS -> PENDING (recovery) is allowed."""
        assert can_transition(TaskStatus.IN_PROGRESS, TaskStatus.PENDING) is True

    def test_can_transition_failed_to_pending(self):
        """FAILED -> PENDING (retry) is allowed."""
        assert can_transition(TaskStatus.FAILED, TaskStatus.PENDING) is True

    def test_cannot_transition_completed_to_any(self):
        """COMPLETED is terminal; no transitions allowed."""
        assert can_transition(TaskStatus.COMPLETED, TaskStatus.PENDING) is False
        assert can_transition(TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS) is False
        assert can_transition(TaskStatus.COMPLETED, TaskStatus.FAILED) is False
        assert can_transition(TaskStatus.COMPLETED, TaskStatus.COMPLETED) is True  # no-op

    def test_cannot_transition_pending_to_completed(self):
        """PENDING -> COMPLETED is invalid (skip IN_PROGRESS)."""
        assert can_transition(TaskStatus.PENDING, TaskStatus.COMPLETED) is False

    def test_cannot_transition_failed_to_in_progress(self):
        """FAILED -> IN_PROGRESS is invalid (must go via PENDING)."""
        assert can_transition(TaskStatus.FAILED, TaskStatus.IN_PROGRESS) is False

    def test_validate_same_status_allowed(self):
        """Same status (no-op) does not raise."""
        validate_task_status_transition(TaskStatus.PENDING, TaskStatus.PENDING)
        validate_task_status_transition(TaskStatus.COMPLETED, TaskStatus.COMPLETED)

    def test_validate_invalid_transition_raises(self):
        """Invalid transition raises ValueError with clear message."""
        with pytest.raises(ValueError) as exc_info:
            validate_task_status_transition(TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS)
        assert "Invalid task status transition" in str(exc_info.value)
        assert "completed" in str(exc_info.value)
        assert "in_progress" in str(exc_info.value)

    def test_validate_valid_transition_does_not_raise(self):
        """Valid transitions do not raise."""
        validate_task_status_transition(TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
        validate_task_status_transition(TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED)
        validate_task_status_transition(TaskStatus.FAILED, TaskStatus.PENDING)


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_priority_values(self):
        """Test that all expected priority values exist."""
        assert TaskPriority.LOW.value == "low"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.HIGH.value == "high"

    def test_from_string_valid(self):
        """Test creating priority from valid string."""
        assert TaskPriority.from_string("low") == TaskPriority.LOW
        assert TaskPriority.from_string("HIGH") == TaskPriority.HIGH
        assert TaskPriority.from_string("Medium") == TaskPriority.MEDIUM

    def test_from_string_invalid(self):
        """Test creating priority from invalid string defaults to MEDIUM."""
        assert TaskPriority.from_string("invalid") == TaskPriority.MEDIUM
        assert TaskPriority.from_string("") == TaskPriority.MEDIUM

    def test_to_score(self):
        """Test priority to score conversion."""
        assert TaskPriority.HIGH.to_score() == 3
        assert TaskPriority.MEDIUM.to_score() == 2
        assert TaskPriority.LOW.to_score() == 1


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_default_values(self):
        """Test default values."""
        result = TaskResult()
        assert result.report == ""
        assert result.success is True
        assert result.error_message is None

    def test_to_dict_success(self):
        """Test converting successful result to dict."""
        result = TaskResult(report="Task completed", success=True)
        d = result.to_dict()
        assert d["report"] == "Task completed"
        assert "success" not in d  # success=True is not included

    def test_to_dict_failure(self):
        """Test converting failed result to dict."""
        result = TaskResult(
            report="Task failed",
            success=False,
            error_message="Something went wrong",
        )
        d = result.to_dict()
        assert d["report"] == "Task failed"
        assert d["success"] is False
        assert d["error_message"] == "Something went wrong"

    def test_from_dict(self):
        """Test creating from dict."""
        data = {
            "report": "Test report",
            "success": False,
            "error_message": "Error",
        }
        result = TaskResult.from_dict(data)
        assert result.report == "Test report"
        assert result.success is False
        assert result.error_message == "Error"

    def test_from_dict_defaults(self):
        """Test creating from dict with missing fields."""
        result = TaskResult.from_dict({})
        assert result.report == ""
        assert result.success is True
        assert result.error_message is None


class TestTask:
    """Tests for Task dataclass."""

    def test_create_basic_task(self):
        """Test creating a basic task."""
        task = Task(id="task-001", title="Test Task")
        assert task.id == "task-001"
        assert task.title == "Test Task"
        assert task.description == ""
        assert task.priority == TaskPriority.MEDIUM
        assert task.status == TaskStatus.PENDING
        assert task.created_at is not None

    def test_post_init_priority_conversion(self):
        """Test that string priority is converted to enum."""
        task = Task(id="t1", title="Test", priority="high")  # type: ignore
        assert task.priority == TaskPriority.HIGH

    def test_post_init_status_conversion(self):
        """Test that string status is converted to enum."""
        task = Task(id="t1", title="Test", status="completed")  # type: ignore
        assert task.status == TaskStatus.COMPLETED

    def test_post_init_invalid_status(self):
        """Test that invalid status defaults to PENDING."""
        task = Task(id="t1", title="Test", status="invalid")  # type: ignore
        assert task.status == TaskStatus.PENDING

    def test_to_dict(self, sample_task):
        """Test converting task to dict."""
        d = sample_task.to_dict()
        assert d["id"] == "task-001"
        assert d["title"] == "Test Task"
        assert d["priority"] == "medium"
        assert d["status"] == "pending"
        assert d["files"] == ["src/main.py", "tests/test_main.py"]

    def test_from_dict(self, sample_task_dict):
        """Test creating task from dict."""
        task = Task.from_dict(sample_task_dict)
        assert task.id == "task-001"
        assert task.title == "Test Task"
        assert task.priority == TaskPriority.MEDIUM
        assert task.status == TaskStatus.PENDING
        assert task.estimated_hours == 2.0

    def test_from_dict_with_result(self):
        """Test creating task from dict with result."""
        data = {
            "id": "t1",
            "title": "Task with result",
            "status": "completed",
            "result": {
                "report": "Done",
                "success": True,
            },
        }
        task = Task.from_dict(data)
        assert task.result is not None
        assert task.result.report == "Done"
        assert task.result.success is True

    def test_status_check_methods(self):
        """Test status check methods."""
        pending = Task(id="t1", title="T", status=TaskStatus.PENDING)
        in_progress = Task(id="t2", title="T", status=TaskStatus.IN_PROGRESS)
        completed = Task(id="t3", title="T", status=TaskStatus.COMPLETED)
        failed = Task(id="t4", title="T", status=TaskStatus.FAILED)

        assert pending.is_pending() is True
        assert pending.is_in_progress() is False

        assert in_progress.is_in_progress() is True
        assert in_progress.is_pending() is False

        assert completed.is_completed() is True
        assert completed.is_failed() is False

        assert failed.is_failed() is True
        assert failed.is_completed() is False

    def test_roundtrip_dict_conversion(self, sample_task):
        """Test that to_dict -> from_dict preserves data."""
        d = sample_task.to_dict()
        restored = Task.from_dict(d)

        assert restored.id == sample_task.id
        assert restored.title == sample_task.title
        assert restored.description == sample_task.description
        assert restored.priority == sample_task.priority
        assert restored.status == sample_task.status
        assert restored.files == sample_task.files


class TestTaskIndex:
    """Tests for TaskIndex dataclass."""

    def test_create_basic_index(self):
        """Test creating a basic task index."""
        index = TaskIndex(id="t1", title="Task 1")
        assert index.id == "t1"
        assert index.title == "Task 1"
        assert index.priority == TaskPriority.MEDIUM
        assert index.created_at is not None

    def test_to_dict(self):
        """Test converting to dict."""
        index = TaskIndex(id="t1", title="Task 1", priority=TaskPriority.HIGH)
        d = index.to_dict()
        assert d["id"] == "t1"
        assert d["title"] == "Task 1"
        assert d["priority"] == "high"

    def test_from_dict(self):
        """Test creating from dict."""
        data = {"id": "t1", "title": "Task 1", "priority": "low"}
        index = TaskIndex.from_dict(data)
        assert index.id == "t1"
        assert index.priority == TaskPriority.LOW


class TestTasksFile:
    """Tests for TasksFile dataclass."""

    def test_default_values(self):
        """Test default values."""
        tf = TasksFile()
        assert tf.tasks == []
        assert tf.next_task_id == 1
        assert tf.version == 0

    def test_to_dict(self, sample_tasks_file):
        """Test converting to dict."""
        d = sample_tasks_file.to_dict()
        assert len(d["tasks"]) == 3
        assert d["next_task_id"] == 4
        assert d["version"] == 1

    def test_from_dict(self):
        """Test creating from dict."""
        data = {
            "tasks": [
                {"id": "t1", "title": "Task 1"},
                {"id": "t2", "title": "Task 2"},
            ],
            "next_task_id": 3,
            "version": 2,
        }
        tf = TasksFile.from_dict(data)
        assert len(tf.tasks) == 2
        assert tf.next_task_id == 3
        assert tf.version == 2

    def test_get_task_index(self, sample_tasks_file):
        """Test getting task index by ID."""
        index = sample_tasks_file.get_task_index("task-002")
        assert index is not None
        assert index.title == "Task 2"

        assert sample_tasks_file.get_task_index("nonexistent") is None

    def test_has_task(self, sample_tasks_file):
        """Test checking if task exists."""
        assert sample_tasks_file.has_task("task-001") is True
        assert sample_tasks_file.has_task("nonexistent") is False


class TestTaskStatistics:
    """Tests for TaskStatistics dataclass."""

    def test_default_values(self):
        """Test default values."""
        stats = TaskStatistics()
        assert stats.total == 0
        assert stats.completed == 0
        assert stats.failed == 0
        assert stats.pending == 0
        assert stats.in_progress == 0

    def test_to_dict(self):
        """Test converting to dict."""
        stats = TaskStatistics(total=10, completed=5, failed=1, pending=3, in_progress=1)
        d = stats.to_dict()
        assert d["total"] == 10
        assert d["completed"] == 5
        assert d["failed"] == 1
        assert d["pending"] == 3
        assert d["in_progress"] == 1

    def test_from_tasks(self):
        """Test calculating statistics from task list."""
        tasks = [
            Task(id="t1", title="T1", status=TaskStatus.COMPLETED),
            Task(id="t2", title="T2", status=TaskStatus.COMPLETED),
            Task(id="t3", title="T3", status=TaskStatus.FAILED),
            Task(id="t4", title="T4", status=TaskStatus.PENDING),
            Task(id="t5", title="T5", status=TaskStatus.IN_PROGRESS),
        ]
        stats = TaskStatistics.from_tasks(tasks)

        assert stats.total == 5
        assert stats.completed == 2
        assert stats.failed == 1
        assert stats.pending == 1
        assert stats.in_progress == 1


# ---------------------------------------------------------------------------
# State models (models/state.py): Status, CheckpointMetadata, ValidationResult
# ---------------------------------------------------------------------------


class TestStatus:
    """Tests for Status dataclass (models/state.py)."""

    def test_post_init_sets_last_updated_when_none(self):
        """When last_updated is None, __post_init__ sets current time."""
        s = Status(version=1)
        assert s.last_updated is not None
        assert s.version == 1

    def test_to_dict_includes_current_phase_when_set(self):
        """When current_phase is set, it is included in to_dict."""
        s = Status(last_updated="2025-01-01T00:00:00", version=1, current_phase="planning")
        d = s.to_dict()
        assert d["current_phase"] == "planning"
        assert d["last_updated"] == "2025-01-01T00:00:00"
        assert d["version"] == 1

    def test_to_dict_omits_current_phase_when_empty(self):
        """When current_phase is None/empty, omit from to_dict."""
        s = Status(last_updated="2025-01-01", version=0, current_phase=None)
        d = s.to_dict()
        assert "current_phase" not in d

    def test_from_dict_with_all_keys(self):
        """When all keys given in from_dict, restore correctly."""
        data = {"last_updated": "2025-01-01T12:00:00", "version": 2, "current_phase": "running"}
        s = Status.from_dict(data)
        assert s.last_updated == "2025-01-01T12:00:00"
        assert s.version == 2
        assert s.current_phase == "running"

    def test_from_dict_with_missing_keys_defaults(self):
        """When keys missing in from_dict, use defaults (boundary)."""
        s = Status.from_dict({})
        # last_updated is set to current time in __post_init__
        assert s.last_updated is not None
        assert s.version == 0
        assert s.current_phase is None


class TestCheckpointMetadata:
    """Tests for CheckpointMetadata dataclass."""

    def test_to_dict(self):
        """to_dict includes checkpoint_name, created_at, files."""
        m = CheckpointMetadata(checkpoint_name="cp1", created_at="2025-01-01", files=["a.json", "b.json"])
        d = m.to_dict()
        assert d["checkpoint_name"] == "cp1"
        assert d["created_at"] == "2025-01-01"
        assert d["files"] == ["a.json", "b.json"]

    def test_from_dict_with_missing_keys(self):
        """When keys missing in from_dict, use empty string/list (boundary)."""
        m = CheckpointMetadata.from_dict({})
        assert m.checkpoint_name == ""
        assert m.created_at == ""
        assert m.files == []


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_default_valid_true(self):
        """Default valid=True."""
        r = ValidationResult()
        assert r.valid is True
        assert r.errors == []
        assert r.warnings == []

    def test_add_error_marks_invalid(self):
        """add_error adds error and sets valid=False."""
        r = ValidationResult()
        r.add_error("Something wrong")
        assert r.valid is False
        assert r.errors == ["Something wrong"]

    def test_add_warning_keeps_valid(self):
        """add_warning keeps valid and adds warning only."""
        r = ValidationResult()
        r.add_warning("Minor issue")
        assert r.valid is True
        assert r.warnings == ["Minor issue"]

    def test_to_dict_and_from_dict_roundtrip(self):
        """Roundtrip via to_dict / from_dict."""
        r = ValidationResult(valid=False, errors=["e1"], warnings=["w1"])
        d = r.to_dict()
        r2 = ValidationResult.from_dict(d)
        assert r2.valid is False
        assert r2.errors == ["e1"]
        assert r2.warnings == ["w1"]

    def test_from_dict_missing_keys_defaults(self):
        """When keys missing in from_dict, use defaults (boundary)."""
        r = ValidationResult.from_dict({})
        assert r.valid is True
        assert r.errors == []
        assert r.warnings == []
