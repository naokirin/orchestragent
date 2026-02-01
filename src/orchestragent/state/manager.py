"""State management utilities for the agent system."""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from orchestragent.models import (
    Task,
    TasksFile,
    TaskStatistics,
    TaskResult,
    CheckpointMetadata,
    ValidationResult,
)

from .file_manager import FileManager
from .task_manager import TaskManager
from .checkpoint_manager import CheckpointManager
from .validation_manager import ValidationManager


class StateManager:
    """
    Facade for state persistence: composes FileManager, TaskManager,
    CheckpointManager, and ValidationManager. Keeps the same public API
    for backward compatibility.
    """

    def __init__(
        self,
        state_dir: str = "state",
        backup_dir: str = "state/backups",
    ) -> None:
        """
        Initialize StateManager.

        Args:
            state_dir: Directory path for state files.
            backup_dir: Directory path for backups.
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        (self.state_dir / "results").mkdir(exist_ok=True)
        (self.state_dir / "checkpoints").mkdir(exist_ok=True)
        (self.state_dir / "tasks").mkdir(exist_ok=True)

        self._file = FileManager(self.state_dir)
        self._task = TaskManager(self._file)
        self._checkpoint = CheckpointManager(self.state_dir, self.backup_dir)
        self._validation = ValidationManager(
            self.state_dir, self._file, self._checkpoint
        )

    # --- File I/O (delegate to FileManager) ---

    def load_json(self, filename: str) -> Dict[str, Any]:
        """Load JSON file from state directory."""
        return self._file.load_json(filename)

    def save_json(self, filename: str, data: Dict[str, Any]) -> None:
        """Save dictionary to JSON file in state directory."""
        self._file.save_json(filename, data)

    def load_text(self, filename: str) -> str:
        """Load text file from state directory."""
        return self._file.load_text(filename)

    def save_text(self, filename: str, content: str) -> None:
        """Save string to text file in state directory."""
        self._file.save_text(filename, content)

    def update_json(
        self,
        filename: str,
        update_func: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Update JSON file using a function (optimistic concurrency)."""
        return self._file.update_json(filename, update_func)

    # --- Status / Tasks / Plan (delegate to TaskManager) ---

    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return self._task.get_status()

    def update_status(self, **kwargs: Any) -> None:
        """Update status with given fields."""
        self._task.update_status(**kwargs)

    def get_tasks(self) -> Dict[str, Any]:
        """Get current tasks index as dictionary (read-only)."""
        return self._task.get_tasks()

    def get_tasks_file(self) -> TasksFile:
        """Get current tasks index as TasksFile object (read-only)."""
        return self._task.get_tasks_file()

    def get_plan(self) -> str:
        """Get current plan."""
        return self._task.get_plan()

    def save_plan(self, plan: str) -> None:
        """Save plan."""
        self._task.save_plan(plan)

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks."""
        return self._task.get_pending_tasks()

    def get_all_tasks_from_files(self) -> List[Task]:
        """Get all tasks from individual files (source of truth)."""
        return self._task.get_all_tasks_from_files()

    def get_task_statistics(self) -> TaskStatistics:
        """Get task statistics from current task states."""
        return self._task.get_task_statistics()

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get task by ID (from individual file)."""
        return self._task.get_task_by_id(task_id)

    def add_task(self, task: Union[Task, Dict[str, Any]]) -> str:
        """Add a new task (index + individual file)."""
        return self._task.add_task(task)

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> None:
        """Update task with given fields (validates status transition)."""
        self._task.update_task(task_id, updates)

    def assign_task(self, task_id: str, worker_id: str = "worker") -> None:
        """Assign task to worker."""
        self._task.assign_task(task_id, worker_id)

    def complete_task(
        self, task_id: str, result: Union[TaskResult, Dict[str, Any]]
    ) -> None:
        """Mark task as completed with result."""
        self._task.complete_task(task_id, result)

    def fail_task(self, task_id: str, error: str) -> None:
        """Mark task as failed."""
        self._task.fail_task(task_id, error)

    def recover_in_progress_tasks(self) -> List[str]:
        """Reset tasks stuck in in_progress to pending."""
        return self._task.recover_in_progress_tasks()

    # --- Checkpoint / Backup (delegate to CheckpointManager) ---

    def create_checkpoint(self, checkpoint_name: Optional[str] = None) -> str:
        """Create a checkpoint of current state."""
        return self._checkpoint.create_checkpoint(checkpoint_name)

    def restore_checkpoint(self, checkpoint_name: str) -> None:
        """Restore state from a checkpoint."""
        self._checkpoint.restore_checkpoint(checkpoint_name)

    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """Create a backup of current state."""
        return self._checkpoint.create_backup(backup_name)

    def list_checkpoints(self) -> List[CheckpointMetadata]:
        """List all available checkpoints (newest first)."""
        return self._checkpoint.list_checkpoints()

    # --- Validation / Recovery (delegate to ValidationManager) ---

    def validate_state(self) -> ValidationResult:
        """Validate state files for integrity."""
        return self._validation.validate_state()

    def recover_from_corruption(self) -> bool:
        """Attempt to recover from state corruption."""
        return self._validation.recover_from_corruption()
