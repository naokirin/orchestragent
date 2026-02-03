"""Factory for creating LLM clients."""

import logging
import subprocess
from typing import List, Optional, Tuple

from .client import LLMClient
from .cursor_cli import CursorCLIClient
from .claude_code_cli import ClaudeCodeCLIClient
from .gemini_cli import GeminiCLIClient
from .fallback_client import FallbackLLMClient
from .backend_config import AgentBackendConfig, LLMBackendSettings

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """Factory for creating LLM clients."""

    SUPPORTED_BACKENDS = ["cursor_cli", "claude_code_cli", "gemini_cli"]

    @staticmethod
    def create(
        backend: str = "cursor_cli",
        project_root: str = ".",
        output_format: str = "text",
        model: Optional[str] = None,
        **kwargs,
    ) -> LLMClient:
        """
        Create a single LLM client for a backend.

        Backward compatible with existing code.

        Args:
            backend: Backend name
                - "cursor_cli": Cursor CLI
                - "claude_code_cli": Claude Code CLI
                - "gemini_cli": Gemini CLI
            project_root: Project root directory
            output_format: Output format ("text", "json", "stream-json")
            model: Default model for the backend
            **kwargs: Backend-specific settings

        Returns:
            LLMClient instance

        Raises:
            ValueError: If unsupported backend is specified
        """
        if backend == "cursor_cli":
            return CursorCLIClient(
                project_root=project_root,
                output_format=output_format,
            )
        elif backend == "claude_code_cli":
            return ClaudeCodeCLIClient(
                project_root=project_root,
                output_format=output_format,
                default_model=model,
            )
        elif backend == "gemini_cli":
            return GeminiCLIClient(
                project_root=project_root,
                output_format=output_format,
                default_model=model,
            )
        else:
            raise ValueError(
                f"Unknown backend: {backend}. "
                f"Supported: {', '.join(LLMClientFactory.SUPPORTED_BACKENDS)}"
            )

    @staticmethod
    def create_with_fallback(
        agent_config: AgentBackendConfig,
        project_root: str = ".",
        output_format: str = "text",
        check_availability: bool = True,
    ) -> LLMClient:
        """
        Create an LLM client with fallback support.

        Args:
            agent_config: Backend configuration with priority order
            project_root: Project root directory
            output_format: Output format for all backends
            check_availability: Skip unavailable backends

        Returns:
            FallbackLLMClient if multiple backends, single client otherwise

        Raises:
            ValueError: If no available backends
        """
        clients: List[Tuple[str, LLMClient]] = []

        for backend_cfg in agent_config.backends:
            if not backend_cfg.enabled:
                continue

            # Check availability if requested
            if check_availability:
                if not LLMClientFactory.is_backend_available(backend_cfg.name):
                    logger.warning(
                        f"Backend {backend_cfg.name} is not available, skipping"
                    )
                    continue

            try:
                client = LLMClientFactory.create(
                    backend=backend_cfg.name,
                    project_root=project_root,
                    output_format=backend_cfg.output_format or output_format,
                    model=backend_cfg.model,
                )
                clients.append((backend_cfg.name, client))
            except Exception as e:
                logger.warning(
                    f"Failed to initialize backend {backend_cfg.name}: {e}, skipping"
                )
                continue

        if not clients:
            configured = [b.name for b in agent_config.backends]
            raise ValueError(
                f"No available backends. Configured: {configured}. "
                f"Supported: {LLMClientFactory.SUPPORTED_BACKENDS}"
            )

        if len(clients) == 1:
            # Single client, no need for fallback wrapper
            return clients[0][1]

        return FallbackLLMClient(clients=clients)

    @staticmethod
    def is_backend_available(backend: str) -> bool:
        """
        Check if a backend CLI is available on the system.

        Args:
            backend: Backend name

        Returns:
            True if the backend CLI is available
        """
        commands = {
            "cursor_cli": ["agent", "--version"],
            "claude_code_cli": ["claude", "--version"],
            "gemini_cli": ["gemini", "--version"],
        }

        cmd = commands.get(backend)
        if not cmd:
            return False

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def create_for_agent(
        agent_type: str,
        settings: LLMBackendSettings,
        agent_model: Optional[str] = None,
        check_availability: bool = True,
    ) -> LLMClient:
        """
        Create an LLM client for a specific agent type.

        Args:
            agent_type: "planner", "worker", or "judge"
            settings: Complete backend settings
            agent_model: Agent-specific model (e.g., PLANNER_MODEL from config)
            check_availability: Skip unavailable backends

        Returns:
            Configured LLMClient (possibly with fallback)
        """
        agent_config = settings.get_agent_config(agent_type, agent_model)

        return LLMClientFactory.create_with_fallback(
            agent_config=agent_config,
            project_root=settings.project_root,
            output_format=settings.output_format,
            check_availability=check_availability,
        )
