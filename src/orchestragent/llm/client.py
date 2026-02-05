"""Abstract base class for LLM clients."""

from abc import ABC, abstractmethod
from typing import Optional

from .backend_config import ModelTier


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
        model_tier: Optional[ModelTier] = None,
        **kwargs
    ) -> str:
        """
        Call agent and get response.

        Args:
            prompt: Prompt string
            mode: Mode ("agent", "plan", "ask")
            model: Model to use (optional, depends on backend)
            model_tier: Model tier for dynamic selection ("light", "standard", "powerful")
                       If provided, overrides model with tier-specific model if configured
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
        model_tier: Optional[ModelTier] = None,
        **kwargs
    ) -> str:
        """
        Load prompt from file and execute.

        Args:
            prompt_file: Path to prompt file
            mode: Mode ("agent", "plan", "ask")
            model: Model to use (optional)
            model_tier: Model tier for dynamic selection ("light", "standard", "powerful")
            **kwargs: Other options

        Returns:
            Agent output (string)
        """
        pass
