"""Data models for the agent system using dataclasses."""

from dataclasses import dataclass, field, asdict
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

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get attribute by key (for backward compatibility with dict interface).

        Args:
            key: Attribute name
            default: Default value if attribute not found

        Returns:
            Attribute value or default
        """
        if hasattr(self, key):
            value = getattr(self, key)
            # Convert enum values to their string representation
            if isinstance(value, TaskStatus):
                return value.value
            if isinstance(value, TaskPriority):
                return value.value
            if isinstance(value, TaskResult):
                return value.to_dict()
            return value
        return default

    def __getitem__(self, key: str) -> Any:
        """Support dict-like access: task['id']."""
        value = self.get(key)
        if value is None and not hasattr(self, key):
            raise KeyError(key)
        return value

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator: 'id' in task."""
        return hasattr(self, key) and getattr(self, key) is not None


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


@dataclass
class CheckpointMetadata:
    """Checkpoint metadata."""
    checkpoint_name: str
    created_at: str
    files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "checkpoint_name": self.checkpoint_name,
            "created_at": self.created_at,
            "files": self.files,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointMetadata":
        """Create CheckpointMetadata from dictionary."""
        return cls(
            checkpoint_name=data.get("checkpoint_name", ""),
            created_at=data.get("created_at", ""),
            files=data.get("files", []),
        )


@dataclass
class ValidationResult:
    """State validation result."""
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationResult":
        """Create ValidationResult from dictionary."""
        return cls(
            valid=data.get("valid", True),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
        )

    def add_error(self, error: str) -> None:
        """Add an error and mark as invalid."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning."""
        self.warnings.append(warning)


@dataclass
class Status:
    """System status data."""
    last_updated: Optional[str] = None
    version: int = 0
    current_phase: Optional[str] = None

    def __post_init__(self):
        """Post-initialization processing."""
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "last_updated": self.last_updated,
            "version": self.version,
        }
        if self.current_phase:
            data["current_phase"] = self.current_phase
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Status":
        """Create Status from dictionary."""
        return cls(
            last_updated=data.get("last_updated"),
            version=data.get("version", 0),
            current_phase=data.get("current_phase"),
        )


@dataclass
class Commit:
    """Git commit information."""
    hash: str
    message: str
    timestamp: Optional[str] = None

    def __post_init__(self):
        """Post-initialization processing."""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hash": self.hash,
            "message": self.message,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Commit":
        """Create Commit from dictionary."""
        return cls(
            hash=data.get("hash", ""),
            message=data.get("message", ""),
            timestamp=data.get("timestamp"),
        )


@dataclass
class IntentData:
    """Intent goal and rationale data."""
    goal: str = ""
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "goal": self.goal,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntentData":
        """Create IntentData from dictionary."""
        return cls(
            goal=data.get("goal", ""),
            rationale=data.get("rationale", ""),
        )


@dataclass
class Intent:
    """Full Intent data model."""
    task_id: str
    intent: IntentData = field(default_factory=IntentData)
    commits: List[Commit] = field(default_factory=list)
    related_adr: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.intent, dict):
            self.intent = IntentData.from_dict(self.intent)
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "task_id": self.task_id,
            "intent": self.intent.to_dict() if isinstance(self.intent, IntentData) else self.intent,
            "commits": [c.to_dict() if isinstance(c, Commit) else c for c in self.commits],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.related_adr:
            data["related_adr"] = self.related_adr
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Intent":
        """Create Intent from dictionary."""
        intent_data = data.get("intent", {})
        if isinstance(intent_data, dict):
            intent = IntentData.from_dict(intent_data)
        else:
            intent = IntentData()

        commits_data = data.get("commits", [])
        commits = [Commit.from_dict(c) if isinstance(c, dict) else c for c in commits_data]

        return cls(
            task_id=data.get("task_id", "unknown"),
            intent=intent,
            commits=commits,
            related_adr=data.get("related_adr"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def add_commit(self, commit_hash: str, message: str) -> bool:
        """Add a commit if not already present."""
        existing_hashes = [c.hash for c in self.commits]
        if commit_hash in existing_hashes:
            return False

        self.commits.append(Commit(hash=commit_hash, message=message))
        self.updated_at = datetime.now().isoformat()
        return True
