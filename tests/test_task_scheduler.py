"""Tests for TaskScheduler class."""

import pytest
from unittest.mock import MagicMock, patch

from orchestragent.scheduler.task_scheduler import TaskScheduler
from orchestragent.models import Task, TaskStatus, TaskPriority


class TestTaskScheduler:
    """Tests for TaskScheduler class."""

    @pytest.fixture
    def mock_state_manager(self):
        """Create a mock state manager."""
        return MagicMock()

    @pytest.fixture
    def mock_file_lock_manager(self):
        """Create a mock file lock manager."""
        manager = MagicMock()
        manager.is_locked.return_value = False
        return manager

    @pytest.fixture
    def scheduler(self, mock_state_manager, mock_file_lock_manager):
        """Create a TaskScheduler with mocks."""
        return TaskScheduler(mock_state_manager, mock_file_lock_manager)

    def test_init(self, mock_state_manager, mock_file_lock_manager):
        """Test TaskScheduler initialization."""
        scheduler = TaskScheduler(mock_state_manager, mock_file_lock_manager)
        assert scheduler.state_manager is mock_state_manager
        assert scheduler.file_lock_manager is mock_file_lock_manager


class TestGetParallelizableTasks:
    """Tests for get_parallelizable_tasks method."""

    @pytest.fixture
    def scheduler(self):
        mock_state_manager = MagicMock()
        mock_file_lock_manager = MagicMock()
        mock_file_lock_manager.is_locked.return_value = False
        return TaskScheduler(mock_state_manager, mock_file_lock_manager)

    def test_no_pending_tasks(self, scheduler):
        """Test with no pending tasks."""
        scheduler.state_manager.get_pending_tasks.return_value = []
        result = scheduler.get_parallelizable_tasks()
        assert result == []

    def test_single_pending_task(self, scheduler):
        """Test with single pending task."""
        task = Task(id="task-001", title="Test Task", status=TaskStatus.PENDING)
        scheduler.state_manager.get_pending_tasks.return_value = [task]

        result = scheduler.get_parallelizable_tasks()

        assert len(result) == 1
        assert result[0].id == "task-001"

    def test_max_workers_limit(self, scheduler):
        """Test that max_workers limits returned tasks."""
        tasks = [
            Task(id=f"task-{i:03d}", title=f"Task {i}", status=TaskStatus.PENDING)
            for i in range(10)
        ]
        scheduler.state_manager.get_pending_tasks.return_value = tasks

        result = scheduler.get_parallelizable_tasks(max_workers=3)

        assert len(result) <= 3

    def test_priority_ordering(self, scheduler):
        """Test that tasks are sorted by priority."""
        tasks = [
            Task(id="task-001", title="Low", priority=TaskPriority.LOW),
            Task(id="task-002", title="High", priority=TaskPriority.HIGH),
            Task(id="task-003", title="Medium", priority=TaskPriority.MEDIUM),
        ]
        scheduler.state_manager.get_pending_tasks.return_value = tasks

        result = scheduler.get_parallelizable_tasks(max_workers=3)

        # High priority should be first
        assert result[0].priority == TaskPriority.HIGH

    def test_file_conflict_avoidance(self, scheduler):
        """Test that conflicting tasks are not selected."""
        task1 = Task(
            id="task-001",
            title="Edit main.py",
            files=["src/main.py"],
            priority=TaskPriority.HIGH
        )
        task2 = Task(
            id="task-002",
            title="Also edit main.py",
            files=["src/main.py"],
            priority=TaskPriority.MEDIUM
        )
        task3 = Task(
            id="task-003",
            title="Edit other.py",
            files=["src/other.py"],
            priority=TaskPriority.LOW
        )
        scheduler.state_manager.get_pending_tasks.return_value = [task1, task2, task3]

        result = scheduler.get_parallelizable_tasks(max_workers=3)

        # task1 and task2 conflict, so only one should be selected
        task_ids = [t.id for t in result]
        assert "task-001" in task_ids  # Higher priority
        assert "task-003" in task_ids  # No conflict
        assert "task-002" not in task_ids  # Conflicts with task-001


class TestFilterReadyTasks:
    """Tests for _filter_ready_tasks method."""

    @pytest.fixture
    def scheduler(self):
        mock_state_manager = MagicMock()
        mock_file_lock_manager = MagicMock()
        return TaskScheduler(mock_state_manager, mock_file_lock_manager)

    def test_no_dependencies(self, scheduler):
        """Test task with no dependencies is ready."""
        task = Task(id="task-001", title="No deps", dependencies=[])

        result = scheduler._filter_ready_tasks([task])

        assert len(result) == 1

    def test_all_dependencies_completed(self, scheduler):
        """Test task with all completed dependencies is ready."""
        task = Task(
            id="task-002",
            title="Has deps",
            dependencies=["task-001"]
        )
        dep_task = Task(id="task-001", title="Dep", status=TaskStatus.COMPLETED)
        scheduler.state_manager.get_task_by_id.return_value = dep_task

        result = scheduler._filter_ready_tasks([task])

        assert len(result) == 1

    def test_incomplete_dependencies(self, scheduler):
        """Test task with incomplete dependencies is not ready."""
        task = Task(
            id="task-002",
            title="Has deps",
            dependencies=["task-001"]
        )
        dep_task = Task(id="task-001", title="Dep", status=TaskStatus.PENDING)
        scheduler.state_manager.get_task_by_id.return_value = dep_task

        result = scheduler._filter_ready_tasks([task])

        assert len(result) == 0

    def test_missing_dependency(self, scheduler):
        """Test task with missing dependency is not ready."""
        task = Task(
            id="task-002",
            title="Has deps",
            dependencies=["task-001"]
        )
        scheduler.state_manager.get_task_by_id.return_value = None

        result = scheduler._filter_ready_tasks([task])

        assert len(result) == 0


class TestExtractTaskFiles:
    """Tests for _extract_task_files method."""

    @pytest.fixture
    def scheduler(self):
        mock_state_manager = MagicMock()
        mock_file_lock_manager = MagicMock()
        return TaskScheduler(mock_state_manager, mock_file_lock_manager)

    def test_extract_from_files_field(self, scheduler):
        """Test extraction from explicit files field."""
        task = Task(
            id="task-001",
            title="Test",
            files=["src/main.py", "tests/test_main.py"]
        )

        result = scheduler._extract_task_files(task)

        assert "src/main.py" in result
        assert "tests/test_main.py" in result

    def test_extract_from_description_explicit(self, scheduler):
        """Test extraction from description with explicit file mentions."""
        task = Task(
            id="task-001",
            title="Test",
            description="Modify file: src/utils.py and file: tests/test_utils.py"
        )

        result = scheduler._extract_task_files(task)

        assert "src/utils.py" in result
        assert "tests/test_utils.py" in result

    def test_extract_from_description_quoted(self, scheduler):
        """Test extraction from description with quoted files."""
        task = Task(
            id="task-001",
            title="Test",
            description='Update "src/config.json" and `src/settings.yaml`'
        )

        result = scheduler._extract_task_files(task)

        assert "src/config.json" in result
        assert "src/settings.yaml" in result

    def test_extract_from_description_common_pattern(self, scheduler):
        """Test extraction from description with common file patterns."""
        task = Task(
            id="task-001",
            title="Test",
            description="Fix bug in src/app.py causing issues"
        )

        result = scheduler._extract_task_files(task)

        assert "src/app.py" in result

    def test_extract_deduplicates(self, scheduler):
        """Test that duplicate files are removed."""
        task = Task(
            id="task-001",
            title="Test",
            files=["src/main.py"],
            description="Update src/main.py with new features"
        )

        result = scheduler._extract_task_files(task)

        # Should only have one entry for src/main.py
        assert result.count("src/main.py") == 1


class TestCanTasksRunParallel:
    """Tests for can_tasks_run_parallel method."""

    @pytest.fixture
    def scheduler(self):
        mock_state_manager = MagicMock()
        mock_file_lock_manager = MagicMock()
        return TaskScheduler(mock_state_manager, mock_file_lock_manager)

    def test_no_conflict(self, scheduler):
        """Test tasks with no overlap can run in parallel."""
        task1 = Task(id="task-001", title="Task 1", files=["file1.py"])
        task2 = Task(id="task-002", title="Task 2", files=["file2.py"])

        result = scheduler.can_tasks_run_parallel(task1, task2)

        assert result is True

    def test_file_conflict(self, scheduler):
        """Test tasks with file overlap cannot run in parallel."""
        task1 = Task(id="task-001", title="Task 1", files=["shared.py"])
        task2 = Task(id="task-002", title="Task 2", files=["shared.py"])

        result = scheduler.can_tasks_run_parallel(task1, task2)

        assert result is False

    def test_dependency_conflict(self, scheduler):
        """Test tasks with dependency cannot run in parallel."""
        task1 = Task(id="task-001", title="Task 1")
        task2 = Task(id="task-002", title="Task 2", dependencies=["task-001"])

        result = scheduler.can_tasks_run_parallel(task1, task2)

        assert result is False

    def test_reverse_dependency_conflict(self, scheduler):
        """Test tasks with reverse dependency cannot run in parallel."""
        task1 = Task(id="task-001", title="Task 1", dependencies=["task-002"])
        task2 = Task(id="task-002", title="Task 2")

        result = scheduler.can_tasks_run_parallel(task1, task2)

        assert result is False

    def test_no_files_no_dependencies(self, scheduler):
        """Test tasks with no files and no dependencies can run in parallel."""
        task1 = Task(id="task-001", title="Task 1")
        task2 = Task(id="task-002", title="Task 2")

        result = scheduler.can_tasks_run_parallel(task1, task2)

        assert result is True


