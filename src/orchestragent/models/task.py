"""Task-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(str, Enum):
    """Task priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @classmethod
    def from_string(cls, value: str) -> "TaskPriority":
        """Create from string, defaulting to MEDIUM if invalid."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.MEDIUM

    def to_score(self) -> int:
        """Convert priority to numeric score (higher is better)."""
        score_map = {
            TaskPriority.HIGH: 3,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 1,
        }
        return score_map.get(self, 2)


@dataclass
class TaskResult:
    """Task execution result."""
    report: str = ""
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"report": self.report}
        if not self.success:
            result["success"] = self.success
        if self.error_message:
            result["error_message"] = self.error_message
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskResult":
        """Create from dictionary."""
        return cls(
            report=data.get("report", ""),
            success=data.get("success", True),
            error_message=data.get("error_message"),
        )


@dataclass
class Task:
    """Full task data model."""
    id: str
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    assigned_to: Optional[str] = None
    result: Optional[TaskResult] = None
    result_file: Optional[str] = None
    error: Optional[str] = None
    files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_hours: float = 0.0
    recovered_at: Optional[str] = None
    recovery_reason: Optional[str] = None

    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.priority, str):
            self.priority = TaskPriority.from_string(self.priority)
        if isinstance(self.status, str):
            try:
                self.status = TaskStatus(self.status)
            except ValueError:
                self.status = TaskStatus.PENDING
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value if isinstance(self.priority, TaskPriority) else self.priority,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "created_at": self.created_at,
        }

        # Only include optional fields if they have values
        if self.updated_at:
            data["updated_at"] = self.updated_at
        if self.started_at:
            data["started_at"] = self.started_at
        if self.completed_at:
            data["completed_at"] = self.completed_at
        if self.failed_at:
            data["failed_at"] = self.failed_at
        if self.assigned_to:
            data["assigned_to"] = self.assigned_to
        if self.result:
            data["result"] = self.result.to_dict() if isinstance(self.result, TaskResult) else self.result
        if self.result_file:
            data["result_file"] = self.result_file
        if self.error:
            data["error"] = self.error
        if self.files:
            data["files"] = self.files
        if self.dependencies:
            data["dependencies"] = self.dependencies
        if self.estimated_hours:
            data["estimated_hours"] = self.estimated_hours
        if self.recovered_at:
            data["recovered_at"] = self.recovered_at
        if self.recovery_reason:
            data["recovery_reason"] = self.recovery_reason

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from dictionary."""
        result_data = data.get("result")
        result = None
        if result_data:
            if isinstance(result_data, dict):
                result = TaskResult.from_dict(result_data)
            else:
                result = result_data

        return cls(
            id=data.get("id", ""),
            title=data.get("title", "No title"),
            description=data.get("description", ""),
            priority=TaskPriority.from_string(data.get("priority", "medium")),
            status=TaskStatus(data.get("status", "pending")),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            failed_at=data.get("failed_at"),
            assigned_to=data.get("assigned_to"),
            result=result,
            result_file=data.get("result_file"),
            error=data.get("error"),
            files=data.get("files", []),
            dependencies=data.get("dependencies", []),
            estimated_hours=data.get("estimated_hours", 0.0),
            recovered_at=data.get("recovered_at"),
            recovery_reason=data.get("recovery_reason"),
        )

    def is_pending(self) -> bool:
        """Check if task is pending."""
        return self.status == TaskStatus.PENDING

    def is_in_progress(self) -> bool:
        """Check if task is in progress."""
        return self.status == TaskStatus.IN_PROGRESS

    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.status == TaskStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if task is failed."""
        return self.status == TaskStatus.FAILED


@dataclass
class TaskIndex:
    """Lightweight task index entry for tasks.json."""
    id: str
    title: str
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: Optional[str] = None

    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.priority, str):
            self.priority = TaskPriority.from_string(self.priority)
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority.value if isinstance(self.priority, TaskPriority) else self.priority,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskIndex":
        """Create TaskIndex from dictionary."""
        return cls(
            id=data.get("id", ""),
            title=data.get("title", "No title"),
            priority=TaskPriority.from_string(data.get("priority", "medium")),
            created_at=data.get("created_at"),
        )


@dataclass
class TasksFile:
    """Structure for tasks.json file."""
    tasks: List[TaskIndex] = field(default_factory=list)
    next_task_id: int = 1
    version: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tasks": [t.to_dict() for t in self.tasks],
            "next_task_id": self.next_task_id,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TasksFile":
        """Create TasksFile from dictionary."""
        tasks_data = data.get("tasks", [])
        tasks = [TaskIndex.from_dict(t) for t in tasks_data]
        return cls(
            tasks=tasks,
            next_task_id=data.get("next_task_id", 1),
            version=data.get("version", 0),
        )

    def get_task_index(self, task_id: str) -> Optional[TaskIndex]:
        """Get task index entry by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def has_task(self, task_id: str) -> bool:
        """Check if task exists in index."""
        return any(t.id == task_id for t in self.tasks)


@dataclass
class TaskStatistics:
    """Task execution statistics."""
    total: int = 0
    completed: int = 0
    failed: int = 0
    pending: int = 0
    in_progress: int = 0

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "pending": self.pending,
            "in_progress": self.in_progress,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "TaskStatistics":
        """Create TaskStatistics from dictionary."""
        return cls(
            total=data.get("total", 0),
            completed=data.get("completed", 0),
            failed=data.get("failed", 0),
            pending=data.get("pending", 0),
            in_progress=data.get("in_progress", 0),
        )

    @classmethod
    def from_tasks(cls, tasks: List[Task]) -> "TaskStatistics":
        """Calculate statistics from task list."""
        return cls(
            total=len(tasks),
            completed=len([t for t in tasks if t.is_completed()]),
            failed=len([t for t in tasks if t.is_failed()]),
            pending=len([t for t in tasks if t.is_pending()]),
            in_progress=len([t for t in tasks if t.is_in_progress()]),
        )
