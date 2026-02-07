"""Model selection utilities for dynamic model selection based on task complexity."""

from typing import Dict, Any, Optional, Union

from orchestragent.models import Task, TaskPriority
from .backend_config import ModelTier


class ModelSelector:
    """Selects appropriate model tier based on task complexity.

    Note: This class now returns model tiers ("light", "standard", "powerful")
    instead of explicit model names. The LLM client resolves the actual model
    based on the tier and per-backend configuration.
    """

    def __init__(
        self,
        enabled: bool = False,
        threshold_light: float = 10.0,
        threshold_powerful: float = 30.0,
    ):
        """
        Initialize model selector.

        Args:
            enabled: Whether dynamic model selection is enabled
            threshold_light: Complexity threshold for light model (below this)
            threshold_powerful: Complexity threshold for powerful model (above this)
        """
        self.enabled = enabled
        self.threshold_light = threshold_light
        self.threshold_powerful = threshold_powerful

    def calculate_complexity_score(self, task: Union[Task, Dict[str, Any]]) -> float:
        """
        Calculate complexity score for a task.

        Args:
            task: Task object or dictionary with description, files, estimated_hours, priority

        Returns:
            Complexity score (higher = more complex)
        """
        # Handle both Task objects and dictionaries
        if isinstance(task, Task):
            description = task.description
            files = task.files
            estimated_hours = task.estimated_hours
            priority = task.priority
        else:
            description = task.get("description", "")
            files = task.get("files", [])
            estimated_hours = task.get("estimated_hours", 0)
            priority = TaskPriority.from_string(task.get("priority", "medium"))

        # Description length (normalized)
        description_length = len(description) if description else 0
        description_score = description_length / 1000.0

        # Number of related files
        file_count = len(files) if files else 0
        file_score = file_count * 2.0

        # Estimated hours
        if isinstance(estimated_hours, (int, float)):
            hours_score = float(estimated_hours) * 5.0
        else:
            hours_score = 0.0

        # Priority score
        priority_score = float(priority.to_score())

        # Total complexity score
        complexity_score = description_score + file_score + hours_score + priority_score

        return complexity_score

    def select_model(self, task: Union[Task, Dict[str, Any]]) -> Optional[str]:
        """
        Deprecated: Use select_model_tier() instead.

        This method is kept for backward compatibility but now returns None.
        The LLM client handles model resolution based on tier and backend config.

        Args:
            task: Task object or dictionary

        Returns:
            None (use select_model_tier for tier-based selection)
        """
        return None

    def select_model_tier(self, task: Union[Task, Dict[str, Any]]) -> Optional[ModelTier]:
        """
        Select the model tier for a task based on complexity.

        This method returns the tier ("light", "standard", "powerful") rather than
        the model name itself. The client will then resolve the actual model
        based on the tier and backend configuration.

        Args:
            task: Task object or dictionary

        Returns:
            Model tier ("light", "standard", "powerful"), or None if selection is disabled
        """
        if not self.enabled:
            return None

        complexity_score = self.calculate_complexity_score(task)

        if complexity_score < self.threshold_light:
            return "light"
        elif complexity_score >= self.threshold_powerful:
            return "powerful"
        else:
            return "standard"

    def get_complexity_category(self, task: Union[Task, Dict[str, Any]]) -> str:
        """
        Get complexity category for a task (for logging/debugging).

        Args:
            task: Task object or dictionary

        Returns:
            Category name: "light", "standard", "powerful", or "default"
        """
        tier = self.select_model_tier(task)
        return tier if tier else "default"
