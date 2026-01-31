"""Intent-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional


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
