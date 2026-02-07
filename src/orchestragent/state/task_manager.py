"""Task CRUD and plan/status operations (delegates file I/O to FileManager)."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from orchestragent.models import (
    Task,
    TaskIndex,
    TasksFile,
    TaskStatistics,
    TaskStatus,
    TaskPriority,
    TaskResult,
    validate_task_status_transition,
)

from .file_manager import FileManager


class TaskManager:
    """Handles task CRUD, plan, and status (uses FileManager for I/O)."""

    def __init__(self, file_manager: FileManager) -> None:
        """
        Initialize TaskManager.

        Args:
            file_manager: FileManager for reading/writing state files.
        """
        self._file = file_manager

    @property
    def state_dir(self) -> Path:
        """State directory (for compatibility with code that uses state_manager.state_dir)."""
        return self._file.state_dir

    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return self._file.load_json("status.json")

    def update_status(self, **kwargs: Any) -> None:
        """Update status with given fields."""

        def update(data: Dict[str, Any]) -> Dict[str, Any]:
            data.update(kwargs)
            data["last_updated"] = datetime.now().isoformat()
            return data

        self._file.update_json("status.json", update)

    def get_tasks(self) -> Dict[str, Any]:
        """Get current tasks index as dictionary (read-only)."""
        return self._file.load_json("tasks.json")

    def get_tasks_file(self) -> TasksFile:
        """Get current tasks index as TasksFile object (read-only)."""
        data = self._file.load_json("tasks.json")
        return TasksFile.from_dict(data)

    def sync_tasks_index(self) -> None:
        """
        Rebuild tasks.json from individual task files (state/tasks/*.json).
        Ensures the index always reflects the current set of tasks so that
        PlanJudge and other consumers see up-to-date task list.
        """
        tasks_dir = self._file.state_dir / "tasks"
        if not tasks_dir.exists():
            self._file.save_json(
                "tasks.json",
                {"tasks": [], "next_task_id": 1, "version": 0},
            )
            return

        index_entries: List[Dict[str, Any]] = []
        max_num = 0
        for path in sorted(tasks_dir.glob("task_*.json")):
            task_id = path.stem
            try:
                num = int(task_id.replace("task_", ""), 10)
                if num > max_num:
                    max_num = num
            except ValueError:
                continue
            data = self._file.load_json(f"tasks/{task_id}.json")
            if not isinstance(data, dict):
                continue
            index_entries.append(
                TaskIndex(
                    id=task_id,
                    title=data.get("title", "No title"),
                    priority=TaskPriority.from_string(data.get("priority", "medium")),
                    created_at=data.get("created_at"),
                ).to_dict()
            )

        index_entries.sort(key=lambda e: e["id"])
        current = self._file.load_json("tasks.json")
        version = current.get("version", 0) + 1
        self._file.save_json(
            "tasks.json",
            {
                "tasks": index_entries,
                "next_task_id": max_num + 1,
                "version": version,
            },
        )

    def _load_task_state(self, task_id: str) -> Dict[str, Any]:
        """Load individual task state from its file."""
        data = self._file.load_json(f"tasks/{task_id}.json")
        return data if isinstance(data, dict) else {}

    def _save_task_state(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Save individual task state to its file (with fsync)."""
        self._file.save_json(f"tasks/{task_id}.json", task_data, sync=True)

    def add_task(self, task: Union[Task, Dict[str, Any]]) -> str:
        """
        Add a new task (index + individual file).

        Args:
            task: Task object or dict.

        Returns:
            Generated task ID.
        """
        task_dict = task.to_dict() if isinstance(task, Task) else task.copy()

        def update(data: Dict[str, Any]) -> Dict[str, Any]:
            if "tasks" not in data:
                data["tasks"] = []
            if "next_task_id" not in data:
                data["next_task_id"] = 1

            task_id = f"task_{data['next_task_id']:03d}"
            task_dict["id"] = task_id
            task_dict["status"] = TaskStatus.PENDING.value
            task_dict["created_at"] = datetime.now().isoformat()

            index_entry = TaskIndex(
                id=task_id,
                title=task_dict.get("title", "No title"),
                priority=TaskPriority.from_string(task_dict.get("priority", "medium")),
                created_at=task_dict["created_at"],
            )
            data["tasks"].append(index_entry.to_dict())
            data["next_task_id"] += 1
            return data

        self._file.update_json("tasks.json", update)
        task_id = str(task_dict["id"])
        self._save_task_state(task_id, task_dict)
        return task_id

    def get_plan(self) -> str:
        """Get current plan."""
        return self._file.load_text("plan.md")

    def save_plan(self, plan: str) -> None:
        """Save plan."""
        self._file.save_text("plan.md", plan)

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get task by ID (from individual file; index used only to verify existence)."""
        tasks_file = self.get_tasks_file()
        task_index = tasks_file.get_task_index(task_id)
        if not task_index:
            return None

        task_state = self._load_task_state(task_id)
        if not task_state:
            return Task(
                id=task_index.id,
                title=task_index.title,
                priority=task_index.priority,
                created_at=task_index.created_at,
            )
        return Task.from_dict(task_state)

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks."""
        tasks_file = self.get_tasks_file()
        pending: List[Task] = []
        for task_index in tasks_file.tasks:
            task = self.get_task_by_id(task_index.id)
            if task and task.is_pending():
                pending.append(task)
        return pending

    def get_all_tasks_from_files(self) -> List[Task]:
        """Get all tasks from individual files (source of truth for status)."""
        tasks_file = self.get_tasks_file()
        all_tasks: List[Task] = []
        for task_index in tasks_file.tasks:
            task = self.get_task_by_id(task_index.id)
            if task:
                all_tasks.append(task)
            else:
                all_tasks.append(
                    Task(
                        id=task_index.id,
                        title=task_index.title,
                        priority=task_index.priority,
                        created_at=task_index.created_at,
                    )
                )
        return all_tasks

    def get_task_statistics(self) -> TaskStatistics:
        """Get task statistics from current task states."""
        all_tasks = self.get_all_tasks_from_files()
        return TaskStatistics.from_tasks(all_tasks)

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> None:
        """Update task fields (individual file only; validates status transition)."""
        task_state = self._load_task_state(task_id)

        if "status" in updates:
            current_status = TaskStatus(
                task_state.get("status", TaskStatus.PENDING.value)
            )
            new_status = (
                TaskStatus(updates["status"])
                if isinstance(updates["status"], str)
                else updates["status"]
            )
            validate_task_status_transition(current_status, new_status)

        task_state.update(updates)
        if "status" in updates:
            task_state["updated_at"] = datetime.now().isoformat()
        self._save_task_state(task_id, task_state)

    def assign_task(self, task_id: str, worker_id: str = "worker") -> None:
        """Assign task to worker."""
        self.update_task(
            task_id,
            {
                "status": TaskStatus.IN_PROGRESS.value,
                "assigned_to": worker_id,
                "started_at": datetime.now().isoformat(),
            },
        )

    def complete_task(
        self, task_id: str, result: Union[TaskResult, Dict[str, Any]]
    ) -> None:
        """Mark task as completed with result (validates transition before writing)."""
        task_state = self._load_task_state(task_id)
        current_status = TaskStatus(task_state.get("status", TaskStatus.PENDING.value))
        validate_task_status_transition(current_status, TaskStatus.COMPLETED)

        result_dict = result.to_dict() if isinstance(result, TaskResult) else result
        result_file = f"results/{task_id}.md"
        self._file.save_text(result_file, result_dict.get("report", ""))

        self.update_task(
            task_id,
            {
                "status": TaskStatus.COMPLETED.value,
                "completed_at": datetime.now().isoformat(),
                "result_file": result_file,
                "result": result_dict,
            },
        )

    def fail_task(self, task_id: str, error: str) -> None:
        """Mark task as failed."""
        self.update_task(
            task_id,
            {
                "status": TaskStatus.FAILED.value,
                "failed_at": datetime.now().isoformat(),
                "error": error,
            },
        )

    def recover_in_progress_tasks(self) -> List[str]:
        """Reset tasks stuck in in_progress to pending (e.g. after restart)."""
        recovered: List[str] = []
        for task in self.get_all_tasks_from_files():
            if task.is_in_progress():
                self.update_task(
                    task.id,
                    {
                        "status": TaskStatus.PENDING.value,
                        "recovered_at": datetime.now().isoformat(),
                        "recovery_reason": "System restart - task was in_progress",
                    },
                )
                recovered.append(task.id)
        return recovered
