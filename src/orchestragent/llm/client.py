"""Abstract base class for LLM clients."""

from abc import ABC, abstractmethod
from typing import Optional


class LLMClient(ABC):
    """Abstract base class for LLM clients.

    This interface allows switching between different backends
    (Cursor CLI, OpenAI API, Anthropic API, etc.).
    """

    @abstractmethod
    def call_agent(
        self,
        prompt: str,
        mode: str = "agent",
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Call agent and get response.

        Args:
            prompt: Prompt string
            mode: Mode ("agent", "plan", "ask")
            model: Model to use (optional, depends on backend)
            **kwargs: Other options

        Returns:
            Agent output (string)

        Raises:
            RuntimeError: If agent call fails
        """
        pass

    @abstractmethod
    def call_agent_from_file(
        self,
        prompt_file: str,
        mode: str = "agent",
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Load prompt from file and execute.

        Args:
            prompt_file: Path to prompt file
            mode: Mode ("agent", "plan", "ask")
            model: Model to use (optional)
            **kwargs: Other options

        Returns:
            Agent output (string)
        """
        pass
