"""Tests for custom exceptions."""

import pytest

from orchestragent.core.exceptions import (
    AgentError,
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    StateError,
    StateCorruptionError,
    TaskError,
)


class TestAgentError:
    """Tests for AgentError base exception."""

    def test_basic_creation(self):
        """Test creating basic AgentError."""
        error = AgentError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.retryable is False
        assert error.original_error is None

    def test_retryable_flag(self):
        """Test retryable flag."""
        error = AgentError("Retryable error", retryable=True)
        assert error.retryable is True

    def test_original_error(self):
        """Test original_error attribute."""
        original = ValueError("Original error")
        error = AgentError("Wrapped error", original_error=original)
        assert error.original_error is original

    def test_is_exception(self):
        """Test that AgentError is an Exception."""
        error = AgentError("Test")
        assert isinstance(error, Exception)

    def test_can_be_raised(self):
        """Test that AgentError can be raised and caught."""
        with pytest.raises(AgentError) as exc_info:
            raise AgentError("Test error", retryable=True)
        assert str(exc_info.value) == "Test error"
        assert exc_info.value.retryable is True


class TestLLMError:
    """Tests for LLMError exception."""

    def test_basic_creation(self):
        """Test creating basic LLMError."""
        error = LLMError("LLM call failed")
        assert str(error) == "LLM call failed"
        # LLMError defaults to retryable=True
        assert error.retryable is True

    def test_inherits_from_agent_error(self):
        """Test that LLMError inherits from AgentError."""
        error = LLMError("Test")
        assert isinstance(error, AgentError)

    def test_non_retryable(self):
        """Test creating non-retryable LLMError."""
        error = LLMError("Fatal error", retryable=False)
        assert error.retryable is False

    def test_with_original_error(self):
        """Test LLMError with original error."""
        original = ConnectionError("Connection failed")
        error = LLMError("API error", original_error=original)
        assert error.original_error is original

    def test_can_catch_as_agent_error(self):
        """Test that LLMError can be caught as AgentError."""
        with pytest.raises(AgentError):
            raise LLMError("Test")


class TestLLMTimeoutError:
    """Tests for LLMTimeoutError exception."""

    def test_basic_creation(self):
        """Test creating LLMTimeoutError."""
        error = LLMTimeoutError(timeout=30.0)
        assert "30" in str(error)
        assert "timed out" in str(error).lower()
        assert error.retryable is True

    def test_inherits_from_llm_error(self):
        """Test that LLMTimeoutError inherits from LLMError."""
        error = LLMTimeoutError(timeout=10.0)
        assert isinstance(error, LLMError)
        assert isinstance(error, AgentError)

    def test_with_original_error(self):
        """Test LLMTimeoutError with original error."""
        original = TimeoutError("Socket timeout")
        error = LLMTimeoutError(timeout=60.0, original_error=original)
        assert error.original_error is original


class TestLLMRateLimitError:
    """Tests for LLMRateLimitError exception."""

    def test_default_message(self):
        """Test default message."""
        error = LLMRateLimitError()
        assert "rate limit" in str(error).lower()
        assert error.retryable is True

    def test_custom_message(self):
        """Test custom message."""
        error = LLMRateLimitError(message="Custom rate limit message")
        assert str(error) == "Custom rate limit message"

    def test_inherits_from_llm_error(self):
        """Test that LLMRateLimitError inherits from LLMError."""
        error = LLMRateLimitError()
        assert isinstance(error, LLMError)
        assert isinstance(error, AgentError)

    def test_with_original_error(self):
        """Test with original error."""
        original = Exception("HTTP 429")
        error = LLMRateLimitError(original_error=original)
        assert error.original_error is original


class TestStateError:
    """Tests for StateError exception."""

    def test_basic_creation(self):
        """Test creating basic StateError."""
        error = StateError("State operation failed")
        assert str(error) == "State operation failed"
        # StateError defaults to retryable=False
        assert error.retryable is False

    def test_inherits_from_agent_error(self):
        """Test that StateError inherits from AgentError."""
        error = StateError("Test")
        assert isinstance(error, AgentError)

    def test_retryable(self):
        """Test creating retryable StateError."""
        error = StateError("Retryable state error", retryable=True)
        assert error.retryable is True

    def test_with_original_error(self):
        """Test StateError with original error."""
        original = IOError("File not found")
        error = StateError("Failed to load state", original_error=original)
        assert error.original_error is original


class TestStateCorruptionError:
    """Tests for StateCorruptionError exception."""

    def test_basic_creation(self):
        """Test creating StateCorruptionError."""
        error = StateCorruptionError(filename="tasks.json")
        assert "tasks.json" in str(error)
        assert "corrupt" in str(error).lower()
        assert error.retryable is False

    def test_inherits_from_state_error(self):
        """Test that StateCorruptionError inherits from StateError."""
        error = StateCorruptionError(filename="test.json")
        assert isinstance(error, StateError)
        assert isinstance(error, AgentError)

    def test_with_original_error(self):
        """Test with original error."""
        original = ValueError("Invalid JSON")
        error = StateCorruptionError(filename="data.json", original_error=original)
        assert error.original_error is original


class TestTaskError:
    """Tests for TaskError exception."""

    def test_basic_creation(self):
        """Test creating basic TaskError."""
        error = TaskError(task_id="task-001", message="Task failed")
        assert "task-001" in str(error)
        assert "Task failed" in str(error)
        assert error.task_id == "task-001"
        assert error.retryable is False

    def test_inherits_from_agent_error(self):
        """Test that TaskError inherits from AgentError."""
        error = TaskError(task_id="task-001", message="Test")
        assert isinstance(error, AgentError)

    def test_retryable(self):
        """Test creating retryable TaskError."""
        error = TaskError(
            task_id="task-002", message="Temporary failure", retryable=True
        )
        assert error.retryable is True

    def test_with_original_error(self):
        """Test TaskError with original error."""
        original = RuntimeError("Execution failed")
        error = TaskError(
            task_id="task-003", message="Runtime error", original_error=original
        )
        assert error.original_error is original
        assert error.task_id == "task-003"


class TestExceptionHierarchy:
    """Tests for exception hierarchy and catching."""

    def test_catch_all_as_agent_error(self):
        """Test that all custom exceptions can be caught as AgentError."""
        exceptions = [
            AgentError("agent"),
            LLMError("llm"),
            LLMTimeoutError(timeout=10),
            LLMRateLimitError(),
            StateError("state"),
            StateCorruptionError(filename="test.json"),
            TaskError(task_id="t1", message="task"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except AgentError:
                pass  # Should catch all
            except Exception:
                pytest.fail(f"{type(exc).__name__} was not caught as AgentError")

    def test_llm_errors_caught_as_llm_error(self):
        """Test that LLM-related errors can be caught as LLMError."""
        exceptions = [
            LLMError("llm"),
            LLMTimeoutError(timeout=10),
            LLMRateLimitError(),
        ]

        for exc in exceptions:
            try:
                raise exc
            except LLMError:
                pass  # Should catch all LLM errors
            except Exception:
                pytest.fail(f"{type(exc).__name__} was not caught as LLMError")

    def test_state_errors_caught_as_state_error(self):
        """Test that state-related errors can be caught as StateError."""
        exceptions = [
            StateError("state"),
            StateCorruptionError(filename="test.json"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except StateError:
                pass  # Should catch all state errors
            except Exception:
                pytest.fail(f"{type(exc).__name__} was not caught as StateError")
