"""Factory for creating LLM clients."""

from typing import Dict, Any
from .llm_client import LLMClient
from .cursor_cli_client import CursorCLIClient


class LLMClientFactory:
    """Factory for creating LLM clients."""
    
    @staticmethod
    def create(backend: str = "cursor_cli", **kwargs) -> LLMClient:
        """
        Create LLM client based on backend.
        
        Args:
            backend: Backend name
                - "cursor_cli": Cursor CLI (initial implementation)
                - "openai": OpenAI API direct call (Phase 4+)
                - "anthropic": Anthropic API direct call (Phase 4+)
            **kwargs: Backend-specific settings
        
        Returns:
            LLMClient instance
        
        Raises:
            ValueError: If unsupported backend is specified
        """
        if backend == "cursor_cli":
            return CursorCLIClient(
                project_root=kwargs.get("project_root", "."),
                output_format=kwargs.get("output_format", "text")
            )
        # Phase 4以降で追加可能
        # elif backend == "openai":
        #     return OpenAIClient(api_key=kwargs.get("api_key"))
        # elif backend == "anthropic":
        #     return AnthropicClient(api_key=kwargs.get("api_key"))
        else:
            supported = ["cursor_cli"]  # Phase 4以降で拡張
            raise ValueError(
                f"Unknown backend: {backend}. "
                f"Supported backends: {', '.join(supported)}"
            )
