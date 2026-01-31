"""State-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional


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
