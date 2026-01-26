"""Custom exceptions for the agent system."""

from typing import Optional


class AgentError(Exception):
    """Base exception for agent system errors."""
    
    def __init__(self, message: str, retryable: bool = False, original_error: Optional[Exception] = None):
        """
        Initialize agent error.
        
        Args:
            message: Error message
            retryable: Whether this error is retryable
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.retryable = retryable
        self.original_error = original_error


class LLMError(AgentError):
    """Error related to LLM API calls."""
    
    def __init__(self, message: str, retryable: bool = True, original_error: Optional[Exception] = None):
        super().__init__(message, retryable=retryable, original_error=original_error)


class LLMTimeoutError(LLMError):
    """Timeout error for LLM API calls."""
    
    def __init__(self, timeout: float, original_error: Optional[Exception] = None):
        message = f"LLM API call timed out after {timeout} seconds"
        super().__init__(message, retryable=True, original_error=original_error)


class LLMRateLimitError(LLMError):
    """Rate limit error for LLM API calls."""
    
    def __init__(self, message: str = "Rate limit exceeded", original_error: Optional[Exception] = None):
        super().__init__(message, retryable=True, original_error=original_error)


class StateError(AgentError):
    """Error related to state management."""
    
    def __init__(self, message: str, retryable: bool = False, original_error: Optional[Exception] = None):
        super().__init__(message, retryable=retryable, original_error=original_error)


class StateCorruptionError(StateError):
    """Error when state file is corrupted."""
    
    def __init__(self, filename: str, original_error: Optional[Exception] = None):
        message = f"State file corrupted: {filename}"
        super().__init__(message, retryable=False, original_error=original_error)


class TaskError(AgentError):
    """Error related to task execution."""
    
    def __init__(self, task_id: str, message: str, retryable: bool = False, original_error: Optional[Exception] = None):
        full_message = f"Task {task_id}: {message}"
        super().__init__(full_message, retryable=retryable, original_error=original_error)
        self.task_id = task_id
