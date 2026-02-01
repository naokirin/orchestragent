"""Tests for StateManager."""

import json
import pytest
from pathlib import Path

from orchestragent.state.manager import StateManager
from orchestragent.models.task import (
    Task,
    TaskIndex,
    TaskPriority,
    TaskResult,
    TasksFile,
    TaskStatus,
)


class TestStateManagerInit:
    """Tests for StateManager initialization."""

    def test_creates_directories(self, temp_dir):
        """Test that initialization creates required directories."""
        state_dir = temp_dir / "new_state"
        backup_dir = temp_dir / "new_backup"

        manager = StateManager(str(state_dir), str(backup_dir))

        assert state_dir.exists()
        assert backup_dir.exists()
        assert (state_dir / "results").exists()
        assert (state_dir / "checkpoints").exists()
        assert (state_dir / "tasks").exists()

    def test_uses_existing_directories(self, temp_state_dir):
        """Test that initialization works with existing directories."""
        manager = StateManager(str(temp_state_dir))
        assert manager.state_dir == temp_state_dir


class TestStateManagerJsonOperations:
    """Tests for JSON file operations."""

    def test_save_and_load_json(self, state_manager):
        """Test saving and loading JSON data."""
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        state_manager.save_json("test.json", data)
        loaded = state_manager.load_json("test.json")

        assert loaded == data

    def test_load_nonexistent_json(self, state_manager):
        """Test loading non-existent JSON file returns empty dict."""
        result = state_manager.load_json("nonexistent.json")
        assert result == {}

    def test_load_corrupted_json(self, state_manager):
        """Test loading corrupted JSON raises StateCorruptionError."""
        from orchestragent.core.exceptions import StateCorruptionError

        # Write invalid JSON
        filepath = state_manager.state_dir / "corrupted.json"
        filepath.write_text("{ invalid json }")

        with pytest.raises(StateCorruptionError):
            state_manager.load_json("corrupted.json")

    def test_save_json_unicode(self, state_manager):
        """Test saving JSON with unicode characters."""
        data = {"japanese": "日本語", "emoji": "🎉"}

        state_manager.save_json("unicode.json", data)
        loaded = state_manager.load_json("unicode.json")

        assert loaded["japanese"] == "日本語"
        assert loaded["emoji"] == "🎉"


class TestStateManagerTextOperations:
    """Tests for text file operations."""

    def test_save_and_load_text(self, state_manager):
        """Test saving and loading text data."""
        content = "Hello, World!\nLine 2"

        state_manager.save_text("test.txt", content)
        loaded = state_manager.load_text("test.txt")

        assert loaded == content

    def test_load_nonexistent_text(self, state_manager):
        """Test loading non-existent text file returns empty string."""
        result = state_manager.load_text("nonexistent.txt")
        assert result == ""

    def test_save_text_unicode(self, state_manager):
        """Test saving text with unicode characters."""
        content = "日本語テスト\n🎉"

        state_manager.save_text("unicode.txt", content)
        loaded = state_manager.load_text("unicode.txt")

        assert loaded == content


class TestStateManagerTaskOperations:
    """Tests for task-related operations."""

    def test_add_task_returns_generated_id(self, state_manager, sample_task):
        """Test that add_task generates a new task ID."""
        task_id = state_manager.add_task(sample_task)

        # StateManager auto-generates IDs like task_001, task_002, etc.
        assert task_id.startswith("task_")
        assert task_id == "task_001"

        task_file = state_manager.state_dir / "tasks" / f"{task_id}.json"
        assert task_file.exists()

    def test_add_task_preserves_title(self, state_manager, sample_task):
        """Test that add_task preserves the task title."""
        task_id = state_manager.add_task(sample_task)
        loaded = state_manager.get_task_by_id(task_id)

        assert loaded is not None
        assert loaded.title == sample_task.title

    def test_add_task_resets_status_to_pending(self, state_manager):
        """Test that add_task always sets status to PENDING."""
        task = Task(
            id="will-be-ignored",
            title="Test Task",
            status=TaskStatus.COMPLETED,  # This will be reset
        )
        task_id = state_manager.add_task(task)
        loaded = state_manager.get_task_by_id(task_id)

        assert loaded is not None
        assert loaded.status == TaskStatus.PENDING

    def test_get_task_by_id(self, state_manager, sample_task):
        """Test loading a task by ID."""
        task_id = state_manager.add_task(sample_task)
        loaded = state_manager.get_task_by_id(task_id)

        assert loaded is not None
        assert loaded.id == task_id
        assert loaded.title == sample_task.title
        assert loaded.status == TaskStatus.PENDING

    def test_get_nonexistent_task(self, state_manager):
        """Test loading non-existent task returns None."""
        result = state_manager.get_task_by_id("nonexistent-task")
        assert result is None

    def test_get_all_tasks_from_files(self, state_manager):
        """Test getting all tasks from individual files."""
        # Create multiple tasks
        task_ids = []
        for i, title in enumerate(["Task 1", "Task 2", "Task 3"], 1):
            task = Task(id=f"ignored-{i}", title=title)
            task_id = state_manager.add_task(task)
            task_ids.append(task_id)

        loaded_tasks = state_manager.get_all_tasks_from_files()

        assert len(loaded_tasks) == 3
        loaded_ids = {t.id for t in loaded_tasks}
        assert loaded_ids == set(task_ids)

    def test_get_pending_tasks(self, state_manager):
        """Test getting only pending tasks."""
        # Add tasks (all will be PENDING initially)
        task_ids = []
        for title in ["Task 1", "Task 2", "Task 3", "Task 4"]:
            task_id = state_manager.add_task(Task(id="x", title=title))
            task_ids.append(task_id)

        # Change status of some tasks
        state_manager.assign_task(task_ids[1])  # Task 2 -> IN_PROGRESS
        state_manager.assign_task(task_ids[2])
        state_manager.complete_task(task_ids[2], TaskResult(report="Done"))  # Task 3 -> COMPLETED

        pending = state_manager.get_pending_tasks()

        # Only Task 1 and Task 4 should be pending
        assert len(pending) == 2
        pending_ids = {t.id for t in pending}
        assert pending_ids == {task_ids[0], task_ids[3]}

    def test_task_exists_via_get_task_by_id(self, state_manager, sample_task):
        """Test checking if task exists using get_task_by_id."""
        task_id = state_manager.add_task(sample_task)
        assert state_manager.get_task_by_id(task_id) is not None
        assert state_manager.get_task_by_id("nonexistent") is None


class TestStateManagerTasksIndex:
    """Tests for tasks.json index operations."""

    def test_get_tasks_file(self, state_manager, tasks_json_file):
        """Test loading tasks.json via get_tasks_file."""
        tasks_file = state_manager.get_tasks_file()

        assert tasks_file is not None
        assert len(tasks_file.tasks) == 3

    def test_get_empty_tasks_file(self, state_manager):
        """Test loading non-existent tasks.json returns empty TasksFile."""
        tasks_file = state_manager.get_tasks_file()

        assert tasks_file is not None
        assert len(tasks_file.tasks) == 0
        assert tasks_file.next_task_id == 1

    def test_save_tasks_file_via_save_json(self, state_manager, sample_tasks_file):
        """Test saving tasks.json via save_json."""
        state_manager.save_json("tasks.json", sample_tasks_file.to_dict())

        loaded = state_manager.get_tasks_file()
        assert len(loaded.tasks) == 3
        assert loaded.next_task_id == 4


class TestStateManagerStatistics:
    """Tests for task statistics."""

    def test_get_task_statistics(self, state_manager):
        """Test calculating task statistics."""
        # Add 5 tasks (all start as PENDING)
        task_ids = []
        for i in range(5):
            task_id = state_manager.add_task(Task(id=f"t{i}", title=f"Task {i}"))
            task_ids.append(task_id)

        # Change statuses:
        # Task 0, 1 -> COMPLETED
        state_manager.assign_task(task_ids[0])
        state_manager.complete_task(task_ids[0], TaskResult(report="Done"))
        state_manager.assign_task(task_ids[1])
        state_manager.complete_task(task_ids[1], TaskResult(report="Done"))

        # Task 2 -> FAILED
        state_manager.assign_task(task_ids[2])
        state_manager.fail_task(task_ids[2], "Test error")

        # Task 3 -> PENDING (unchanged)
        # Task 4 -> IN_PROGRESS
        state_manager.assign_task(task_ids[4])

        stats = state_manager.get_task_statistics()

        assert stats.total == 5
        assert stats.completed == 2
        assert stats.failed == 1
        assert stats.pending == 1
        assert stats.in_progress == 1

    def test_get_task_statistics_empty(self, state_manager):
        """Test statistics with no tasks."""
        stats = state_manager.get_task_statistics()

        assert stats.total == 0
        assert stats.completed == 0
        assert stats.failed == 0
        assert stats.pending == 0
        assert stats.in_progress == 0


class TestStateManagerTaskLifecycle:
    """Tests for task lifecycle operations."""

    def test_assign_task(self, state_manager, sample_task):
        """Test assigning a task."""
        task_id = state_manager.add_task(sample_task)
        state_manager.assign_task(task_id, "worker-1")

        task = state_manager.get_task_by_id(task_id)
        assert task is not None
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.assigned_to == "worker-1"
        assert task.started_at is not None

    def test_complete_task(self, state_manager, sample_task):
        """Test completing a task."""
        task_id = state_manager.add_task(sample_task)
        state_manager.assign_task(task_id)

        result = TaskResult(report="Task completed successfully", success=True)
        state_manager.complete_task(task_id, result)

        task = state_manager.get_task_by_id(task_id)
        assert task is not None
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None

    def test_fail_task(self, state_manager, sample_task):
        """Test failing a task."""
        task_id = state_manager.add_task(sample_task)
        state_manager.assign_task(task_id)

        state_manager.fail_task(task_id, "Test error message")

        task = state_manager.get_task_by_id(task_id)
        assert task is not None
        assert task.status == TaskStatus.FAILED
        assert task.error == "Test error message"
        assert task.failed_at is not None

    def test_update_task(self, state_manager, sample_task):
        """Test updating task fields."""
        task_id = state_manager.add_task(sample_task)

        state_manager.update_task(task_id, {
            "description": "Updated description",
            "priority": "high",
        })

        task = state_manager.get_task_by_id(task_id)
        assert task is not None
        assert task.description == "Updated description"
        assert task.priority == TaskPriority.HIGH

    def test_sequential_task_ids(self, state_manager):
        """Test that task IDs are generated sequentially."""
        id1 = state_manager.add_task(Task(id="x", title="Task 1"))
        id2 = state_manager.add_task(Task(id="x", title="Task 2"))
        id3 = state_manager.add_task(Task(id="x", title="Task 3"))

        assert id1 == "task_001"
        assert id2 == "task_002"
        assert id3 == "task_003"


class TestStateManagerTaskStatusTransition:
    """Tests for task status transition validation in StateManager."""

    def test_update_task_invalid_status_transition_raises(self, state_manager, sample_task):
        """Invalid status transition via update_task raises ValueError."""
        task_id = state_manager.add_task(sample_task)
        state_manager.assign_task(task_id)
        state_manager.complete_task(task_id, TaskResult(report="Done"))
        # COMPLETED -> IN_PROGRESS is invalid
        with pytest.raises(ValueError) as exc_info:
            state_manager.update_task(task_id, {"status": TaskStatus.IN_PROGRESS.value})
        assert "Invalid task status transition" in str(exc_info.value)
        assert "completed" in str(exc_info.value).lower()
        assert "in_progress" in str(exc_info.value).lower()
        # Task should remain COMPLETED (update was rejected)
        task = state_manager.get_task_by_id(task_id)
        assert task is not None
        assert task.status == TaskStatus.COMPLETED

    def test_update_task_same_status_allowed(self, state_manager, sample_task):
        """Same status update (no-op) is allowed."""
        task_id = state_manager.add_task(sample_task)
        state_manager.assign_task(task_id)
        # IN_PROGRESS -> IN_PROGRESS (e.g. only updating other fields) is allowed
        state_manager.update_task(task_id, {"status": TaskStatus.IN_PROGRESS.value, "description": "Updated"})
        task = state_manager.get_task_by_id(task_id)
        assert task is not None
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.description == "Updated"

    def test_recover_in_progress_tasks_valid_transition(self, state_manager, sample_task):
        """IN_PROGRESS -> PENDING (recovery) is valid and works."""
        task_id = state_manager.add_task(sample_task)
        state_manager.assign_task(task_id)
        assert state_manager.get_task_by_id(task_id).status == TaskStatus.IN_PROGRESS
        recovered = state_manager.recover_in_progress_tasks()
        assert task_id in recovered
        task = state_manager.get_task_by_id(task_id)
        assert task is not None
        assert task.status == TaskStatus.PENDING

    def test_complete_task_invalid_transition_no_file_written(self, state_manager, sample_task):
        """complete_task validates transition BEFORE writing result file."""
        task_id = state_manager.add_task(sample_task)
        # Task is PENDING, cannot directly transition to COMPLETED
        result_file_path = state_manager.state_dir / "results" / f"{task_id}.md"

        with pytest.raises(ValueError) as exc_info:
            state_manager.complete_task(task_id, TaskResult(report="Should not be written"))

        assert "Invalid task status transition" in str(exc_info.value)
        # Result file should NOT exist since validation failed before file write
        assert not result_file_path.exists()
        # Task should remain PENDING
        task = state_manager.get_task_by_id(task_id)
        assert task is not None
        assert task.status == TaskStatus.PENDING
