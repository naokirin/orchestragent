"""Backend configuration for LLM clients."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class BackendConfig:
    """Configuration for a single LLM backend."""

    name: str  # "cursor_cli", "claude_code_cli", "gemini_cli"
    model: Optional[str] = None  # Model to use for this backend
    output_format: str = "text"
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "model": self.model,
            "output_format": self.output_format,
            "enabled": self.enabled,
        }


@dataclass
class AgentBackendConfig:
    """
    Per-agent backend configuration with fallback priority.

    Example:
        AgentBackendConfig(
            backends=[
                BackendConfig(name="claude_code_cli", model="opus"),
                BackendConfig(name="cursor_cli", model="auto"),
            ]
        )

    This means: try Claude Code CLI with opus first,
    fall back to Cursor CLI with auto model if it fails.
    """

    backends: List[BackendConfig] = field(default_factory=list)

    @classmethod
    def from_string(cls, config_str: str) -> "AgentBackendConfig":
        """
        Parse from comma-separated string format.

        Format: "backend1:model1,backend2:model2,..."
        Example: "claude_code_cli:opus,cursor_cli:auto,gemini_cli:gemini-2.5-pro"

        If no model specified: "cursor_cli,gemini_cli"

        Args:
            config_str: Configuration string

        Returns:
            AgentBackendConfig instance
        """
        backends = []
        for part in config_str.split(","):
            part = part.strip()
            if not part:
                continue

            if ":" in part:
                name, model = part.split(":", 1)
                backends.append(
                    BackendConfig(name=name.strip(), model=model.strip() or None)
                )
            else:
                backends.append(BackendConfig(name=part))

        return cls(backends=backends)

    @classmethod
    def single(cls, name: str, model: Optional[str] = None) -> "AgentBackendConfig":
        """Create config with a single backend (no fallback)."""
        return cls(backends=[BackendConfig(name=name, model=model)])

    def is_empty(self) -> bool:
        """Check if no backends are configured."""
        return len(self.backends) == 0


@dataclass
class LLMBackendSettings:
    """
    Complete LLM backend settings for all agents.

    Supports:
    1. Global default backend (backward compatible)
    2. Per-agent backend configuration with fallback
    """

    default_backend: str = "cursor_cli"
    default_model: Optional[str] = None
    output_format: str = "text"
    project_root: str = "."

    # Per-backend default models
    cursor_cli_model: Optional[str] = None
    claude_code_cli_model: Optional[str] = None
    gemini_cli_model: Optional[str] = None

    # Per-agent overrides (None = use default)
    planner_backends: Optional[AgentBackendConfig] = None
    worker_backends: Optional[AgentBackendConfig] = None
    judge_backends: Optional[AgentBackendConfig] = None

    def get_backend_model(self, backend_name: str) -> Optional[str]:
        """Get the default model for a specific backend."""
        models = {
            "cursor_cli": self.cursor_cli_model,
            "claude_code_cli": self.claude_code_cli_model,
            "gemini_cli": self.gemini_cli_model,
        }
        return models.get(backend_name)

    def get_agent_config(
        self, agent_type: str, agent_model: Optional[str] = None
    ) -> AgentBackendConfig:
        """
        Get backend config for an agent type.

        Args:
            agent_type: "planner", "worker", or "judge"
            agent_model: Agent-specific model from existing config (e.g., PLANNER_MODEL)

        Returns:
            AgentBackendConfig for the agent
        """
        agent_configs = {
            "planner": self.planner_backends,
            "worker": self.worker_backends,
            "judge": self.judge_backends,
        }

        agent_config = agent_configs.get(agent_type)

        if agent_config and not agent_config.is_empty():
            # Apply model fallback for backends without explicit model
            resolved_backends = []
            for backend in agent_config.backends:
                if backend.model is None:
                    # Fallback order: backend-specific -> agent-specific -> global
                    resolved_model = (
                        self.get_backend_model(backend.name)
                        or agent_model
                        or self.default_model
                    )
                    resolved_backends.append(
                        BackendConfig(
                            name=backend.name,
                            model=resolved_model,
                            output_format=backend.output_format,
                            enabled=backend.enabled,
                        )
                    )
                else:
                    resolved_backends.append(backend)
            return AgentBackendConfig(backends=resolved_backends)

        # Fall back to default backend with model fallback
        resolved_model = (
            self.get_backend_model(self.default_backend)
            or agent_model
            or self.default_model
        )
        return AgentBackendConfig.single(name=self.default_backend, model=resolved_model)
