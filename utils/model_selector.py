"""Model selection utilities for dynamic model selection based on task complexity."""

from typing import Dict, Any, Optional


class ModelSelector:
    """Selects appropriate model based on task complexity."""
    
    def __init__(
        self,
        enabled: bool = False,
        threshold_light: float = 10.0,
        threshold_powerful: float = 30.0,
        model_light: Optional[str] = None,
        model_standard: Optional[str] = None,
        model_powerful: Optional[str] = None,
        model_default: Optional[str] = None
    ):
        """
        Initialize model selector.
        
        Args:
            enabled: Whether dynamic model selection is enabled
            threshold_light: Complexity threshold for light model (below this)
            threshold_powerful: Complexity threshold for powerful model (above this)
            model_light: Model to use for simple tasks
            model_standard: Model to use for standard tasks
            model_powerful: Model to use for complex tasks
            model_default: Default model to use when selection is disabled or no match
        """
        self.enabled = enabled
        self.threshold_light = threshold_light
        self.threshold_powerful = threshold_powerful
        self.model_light = model_light
        self.model_standard = model_standard
        self.model_powerful = model_powerful
        self.model_default = model_default
    
    def calculate_complexity_score(self, task: Dict[str, Any]) -> float:
        """
        Calculate complexity score for a task.
        
        Args:
            task: Task dictionary with description, files, estimated_hours, priority
        
        Returns:
            Complexity score (higher = more complex)
        """
        # Description length (normalized)
        description = task.get("description", "")
        description_length = len(description) if description else 0
        description_score = description_length / 1000.0
        
        # Number of related files
        files = task.get("files", [])
        file_count = len(files) if files else 0
        file_score = file_count * 2.0
        
        # Estimated hours
        estimated_hours = task.get("estimated_hours", 0)
        if isinstance(estimated_hours, (int, float)):
            hours_score = float(estimated_hours) * 5.0
        else:
            hours_score = 0.0
        
        # Priority score
        priority = task.get("priority", "medium")
        priority_map = {"high": 3, "medium": 2, "low": 1}
        priority_score = float(priority_map.get(priority.lower(), 2))
        
        # Total complexity score
        complexity_score = description_score + file_score + hours_score + priority_score
        
        return complexity_score
    
    def select_model(self, task: Dict[str, Any]) -> Optional[str]:
        """
        Select appropriate model for a task based on complexity.
        
        Args:
            task: Task dictionary
        
        Returns:
            Selected model name, or None to use default
        """
        # If selection is disabled, use default
        if not self.enabled:
            return self.model_default
        
        # Calculate complexity score
        complexity_score = self.calculate_complexity_score(task)
        
        # Select model based on complexity
        if complexity_score < self.threshold_light:
            # Simple task - use light model
            selected_model = self.model_light or self.model_default
        elif complexity_score >= self.threshold_powerful:
            # Complex task - use powerful model
            selected_model = self.model_powerful or self.model_default
        else:
            # Standard task - use standard model
            selected_model = self.model_standard or self.model_default
        
        return selected_model
    
    def get_complexity_category(self, task: Dict[str, Any]) -> str:
        """
        Get complexity category for a task (for logging/debugging).
        
        Args:
            task: Task dictionary
        
        Returns:
            Category name: "light", "standard", or "powerful"
        """
        if not self.enabled:
            return "default"
        
        complexity_score = self.calculate_complexity_score(task)
        
        if complexity_score < self.threshold_light:
            return "light"
        elif complexity_score >= self.threshold_powerful:
            return "powerful"
        else:
            return "standard"
