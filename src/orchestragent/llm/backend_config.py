"""Backend configuration for LLM clients."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# Model tier types for dynamic model selection
ModelTier = str  # "light", "standard", "powerful"


@dataclass
class BackendConfig:
    """Configuration for a single LLM backend."""

    name: str  # "cursor_cli", "claude_code_cli", "gemini_cli"
    model: Optional[str] = None  # Default model to use for this backend
    output_format: str = "text"
    enabled: bool = True
    # Dynamic model selection models (per-backend)
    model_light: Optional[str] = None
    model_standard: Optional[str] = None
    model_powerful: Optional[str] = None

    def get_model_for_tier(self, tier: Optional[ModelTier] = None) -> Optional[str]:
        """
        Get the model for a specific complexity tier.

        Args:
            tier: "light", "standard", "powerful", or None (use default model)

        Returns:
            Model name for the tier, or default model if tier not specified
        """
        if tier is None:
            return self.model

        tier_models = {
            "light": self.model_light,
            "standard": self.model_standard,
            "powerful": self.model_powerful,
        }
        # Fall back to default model if tier-specific model not set
        return tier_models.get(tier) or self.model

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "model": self.model,
            "output_format": self.output_format,
            "enabled": self.enabled,
            "model_light": self.model_light,
            "model_standard": self.model_standard,
            "model_powerful": self.model_powerful,
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
class BackendDynamicModels:
    """Dynamic model selection models for a specific backend."""

    model_light: Optional[str] = None
    model_standard: Optional[str] = None
    model_powerful: Optional[str] = None


@dataclass
class LLMBackendSettings:
    """
    Complete LLM backend settings for all agents.

    Supports:
    1. Global default backend (backward compatible)
    2. Per-agent backend configuration with fallback
    3. Per-backend dynamic model selection
    """

    default_backend: str = "cursor_cli"
    default_model: Optional[str] = None
    output_format: str = "text"
    project_root: str = "."

    # Per-backend default models
    cursor_cli_model: Optional[str] = None
    claude_code_cli_model: Optional[str] = None
    gemini_cli_model: Optional[str] = None

    # Per-backend dynamic model selection
    cursor_cli_dynamic_models: Optional[BackendDynamicModels] = None
    claude_code_cli_dynamic_models: Optional[BackendDynamicModels] = None
    gemini_cli_dynamic_models: Optional[BackendDynamicModels] = None

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

    def get_backend_dynamic_models(self, backend_name: str) -> Optional[BackendDynamicModels]:
        """Get the dynamic model settings for a specific backend."""
        dynamic_models = {
            "cursor_cli": self.cursor_cli_dynamic_models,
            "claude_code_cli": self.claude_code_cli_dynamic_models,
            "gemini_cli": self.gemini_cli_dynamic_models,
        }
        return dynamic_models.get(backend_name)

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
                # Get dynamic models for this backend
                dynamic_models = self.get_backend_dynamic_models(backend.name)

                if backend.model is None:
                    # Fallback order: backend-specific -> agent-specific -> global
                    resolved_model = (
                        self.get_backend_model(backend.name)
                        or agent_model
                        or self.default_model
                    )
                else:
                    resolved_model = backend.model

                # Apply dynamic models if available
                model_light = None
                model_standard = None
                model_powerful = None
                if dynamic_models:
                    model_light = dynamic_models.model_light
                    model_standard = dynamic_models.model_standard
                    model_powerful = dynamic_models.model_powerful

                resolved_backends.append(
                    BackendConfig(
                        name=backend.name,
                        model=resolved_model,
                        output_format=backend.output_format,
                        enabled=backend.enabled,
                        model_light=model_light,
                        model_standard=model_standard,
                        model_powerful=model_powerful,
                    )
                )
            return AgentBackendConfig(backends=resolved_backends)

        # Fall back to default backend with model fallback
        resolved_model = (
            self.get_backend_model(self.default_backend)
            or agent_model
            or self.default_model
        )
        # Get dynamic models for default backend
        dynamic_models = self.get_backend_dynamic_models(self.default_backend)
        model_light = dynamic_models.model_light if dynamic_models else None
        model_standard = dynamic_models.model_standard if dynamic_models else None
        model_powerful = dynamic_models.model_powerful if dynamic_models else None

        return AgentBackendConfig(
            backends=[
                BackendConfig(
                    name=self.default_backend,
                    model=resolved_model,
                    model_light=model_light,
                    model_standard=model_standard,
                    model_powerful=model_powerful,
                )
            ]
        )
