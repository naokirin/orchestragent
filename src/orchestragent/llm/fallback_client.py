"""Fallback LLM client implementation."""

import logging
from pathlib import Path
from typing import List, Optional, Tuple, TYPE_CHECKING

from .client import LLMClient
from orchestragent.core.exceptions import LLMError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from orchestragent.core.logger import AgentLogger


class FallbackLLMClient(LLMClient):
    """
    Wrapper that tries multiple LLM clients in order until one succeeds.

    Useful for resilience: if primary backend is unavailable,
    automatically falls back to secondary/tertiary backends.
    """

    def __init__(
        self,
        clients: List[Tuple[str, LLMClient]],
        retry_on_errors: bool = True,
    ):
        """
        Initialize FallbackLLMClient.

        Args:
            clients: List of (backend_name, client) tuples in priority order
            retry_on_errors: Whether to try next client on retryable errors
        """
        if not clients:
            raise ValueError("At least one client must be provided")
        self.clients = clients
        self.retry_on_errors = retry_on_errors
        self._last_successful_backend: Optional[str] = None

    def call_agent(
        self,
        prompt: str,
        mode: str = "agent",
        model: Optional[str] = None,
        agent_name: Optional[str] = None,
        logger_instance: Optional["AgentLogger"] = None,
        **kwargs,
    ) -> str:
        """
        Try each client in order until one succeeds.

        Args:
            prompt: Prompt string
            mode: Mode ("agent", "plan", "ask")
            model: Model to use (optional, backend may override)
            agent_name: Name of the agent (optional, for logging)
            logger_instance: Logger instance (optional)
            **kwargs: Other options (e.g., timeout)

        Returns:
            Agent output (string)

        Raises:
            LLMError: If all clients fail
        """
        errors: List[Tuple[str, Exception]] = []

        for backend_name, client in self.clients:
            try:
                logger.debug(f"Trying backend: {backend_name}")

                result = client.call_agent(
                    prompt=prompt,
                    mode=mode,
                    model=model,
                    agent_name=agent_name,
                    logger=logger_instance,
                    **kwargs,
                )

                self._last_successful_backend = backend_name
                logger.debug(f"Backend {backend_name} succeeded")
                return result

            except LLMError as e:
                errors.append((backend_name, e))
                logger.warning(
                    f"Backend {backend_name} failed: {e}. Trying next backend..."
                )

                # If error is not retryable and we don't retry on errors, raise immediately
                if not self.retry_on_errors and not e.retryable:
                    raise

                continue

            except Exception as e:
                # Unexpected errors - wrap and continue
                errors.append((backend_name, e))
                logger.warning(
                    f"Backend {backend_name} failed with unexpected error: {e}. "
                    f"Trying next backend..."
                )
                continue

        # All backends failed
        error_summary = "; ".join(f"{name}: {err}" for name, err in errors)
        raise LLMError(f"All backends failed: {error_summary}", retryable=False)

    def call_agent_from_file(
        self,
        prompt_file: str,
        mode: str = "agent",
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Load prompt from file and delegate to call_agent."""
        prompt_path = Path(prompt_file)
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        return self.call_agent(prompt, mode, model, **kwargs)

    @property
    def last_successful_backend(self) -> Optional[str]:
        """Return the name of the last backend that succeeded."""
        return self._last_successful_backend

    @property
    def backend_names(self) -> List[str]:
        """Return list of backend names in priority order."""
        return [name for name, _ in self.clients]
