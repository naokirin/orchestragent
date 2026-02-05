"""Gemini CLI client implementation."""

import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from .client import LLMClient
from .backend_config import ModelTier
from orchestragent.core.exceptions import LLMError, LLMTimeoutError, LLMRateLimitError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from orchestragent.core.logger import AgentLogger


class GeminiCLIClient(LLMClient):
    """Client for executing agents via Gemini CLI.

    Uses the `gemini` command with `-p` flag for non-interactive mode.
    Note: Gemini CLI does not have mode concepts like Cursor CLI.
    The 'mode' parameter is ignored.
    """

    def __init__(
        self,
        project_root: str = ".",
        output_format: str = "text",
        default_model: Optional[str] = None,
        model_light: Optional[str] = None,
        model_standard: Optional[str] = None,
        model_powerful: Optional[str] = None,
    ):
        """
        Initialize Gemini CLI client.

        Args:
            project_root: Project root directory
            output_format: Output format ("text", "json", or "stream-json")
            default_model: Default model to use (e.g., "gemini-2.5-flash", "gemini-2.5-pro")
            model_light: Model for light tasks (dynamic selection)
            model_standard: Model for standard tasks (dynamic selection)
            model_powerful: Model for powerful tasks (dynamic selection)
        """
        self.project_root = Path(project_root).resolve()
        if not self.project_root.exists():
            raise FileNotFoundError(
                f"Project root directory does not exist: {self.project_root}"
            )
        if not self.project_root.is_dir():
            raise NotADirectoryError(
                f"Project root is not a directory: {self.project_root}"
            )
        self.output_format = output_format
        self.default_model = default_model
        # Dynamic model selection
        self.model_light = model_light
        self.model_standard = model_standard
        self.model_powerful = model_powerful

    def _resolve_model(
        self, model: Optional[str], model_tier: Optional[ModelTier]
    ) -> Optional[str]:
        """
        Resolve the model based on tier.

        Args:
            model: Explicitly specified model (takes precedence)
            model_tier: Model tier for dynamic selection

        Returns:
            Resolved model name, or default_model, or None
        """
        if model:
            return model

        if model_tier:
            tier_models = {
                "light": self.model_light,
                "standard": self.model_standard,
                "powerful": self.model_powerful,
            }
            tier_model = tier_models.get(model_tier)
            if tier_model:
                return tier_model

        return self.default_model

    def call_agent(
        self,
        prompt: str,
        mode: str = "agent",
        model: Optional[str] = None,
        model_tier: Optional[ModelTier] = None,
        agent_name: Optional[str] = None,
        logger: Optional["AgentLogger"] = None,
        **kwargs,
    ) -> str:
        """
        Execute agent via Gemini CLI.

        Command: gemini -p "prompt" -m model --output-format format

        Args:
            prompt: Prompt string
            mode: Mode (ignored - Gemini CLI has no mode concept)
            model: Model to use (e.g., "gemini-2.5-flash", "gemini-2.5-pro")
            model_tier: Model tier for dynamic selection ("light", "standard", "powerful")
            agent_name: Name of the agent (optional, for logging)
            logger: Logger instance (optional, for logging command output)
            **kwargs: Other options (e.g., timeout)

        Returns:
            Agent output (string)
        """
        resolved_model = self._resolve_model(model, model_tier)
        cmd = ["gemini", "-p", prompt, "--output-format", self.output_format]

        if resolved_model:
            cmd.extend(["-m", resolved_model])

        timeout = kwargs.get("timeout", 300)  # Default 5 minutes
        command_str = " ".join(cmd[:4]) + " ..."  # Don't log full prompt

        # Prepare streaming log if logger is provided
        log_stream = None
        if logger and agent_name:
            try:
                log_stream = logger.start_agent_command_stream(
                    agent_name=agent_name, command=command_str
                )
            except Exception as log_error:
                if logger:
                    logger.warning(f"Failed to start command log stream: {log_error}")
                log_stream = None

        try:
            # Start Gemini CLI process with stdout/stderr merged
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self.project_root),
                bufsize=1,
            )
        except FileNotFoundError as e:
            error_msg = str(e)
            if "No such file or directory" in error_msg and str(
                self.project_root
            ) in error_msg:
                raise LLMError(
                    f"Working directory does not exist: {self.project_root}. "
                    f"Please check TARGET_PROJECT or PROJECT_ROOT configuration.",
                    retryable=False,
                    original_error=e,
                )
            else:
                raise LLMError(
                    "Gemini CLI not found. Install from: "
                    "https://github.com/google-gemini/gemini-cli",
                    retryable=False,
                    original_error=e,
                )
        except Exception as e:
            raise LLMError(
                f"Unexpected error starting Gemini CLI: {e}",
                retryable=True,
                original_error=e,
            )

        collected_output = []

        def _reader():
            """Read process output line by line and stream to log."""
            if process.stdout is None:
                return
            for line in process.stdout:
                collected_output.append(line)
                if log_stream:
                    try:
                        log_stream.write(line)
                    except OSError as e:
                        logger.debug("Failed to write to log stream: %s", e)

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as e:
            process.kill()
            if log_stream:
                try:
                    log_stream.write("\n[Gemini CLI timed out]\n")
                except OSError as write_error:
                    logger.debug("Failed to write timeout message: %s", write_error)
            raise LLMTimeoutError(timeout, e)
        finally:
            reader_thread.join(timeout=5)
            if log_stream:
                try:
                    log_stream.close()
                except OSError as close_error:
                    logger.debug("Failed to close log stream: %s", close_error)

        output_text = "".join(collected_output)

        if returncode != 0:
            stderr = output_text or ""
            if "rate limit" in stderr.lower() or "429" in stderr:
                raise LLMRateLimitError(f"Gemini CLI rate limit: {stderr}")
            if "timeout" in stderr.lower():
                raise LLMTimeoutError(timeout, RuntimeError(stderr))
            raise LLMError(f"Gemini CLI error: {stderr}", retryable=True)

        return output_text

    def call_agent_from_file(
        self,
        prompt_file: str,
        mode: str = "agent",
        model: Optional[str] = None,
        model_tier: Optional[ModelTier] = None,
        **kwargs,
    ) -> str:
        """Load prompt from file and execute."""
        prompt_path = Path(prompt_file)
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        return self.call_agent(prompt, mode, model, model_tier=model_tier, **kwargs)
