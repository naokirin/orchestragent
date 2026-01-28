"""Cursor CLI client implementation."""

import subprocess
import threading
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from .llm_client import LLMClient
from .exceptions import LLMError, LLMTimeoutError, LLMRateLimitError

if TYPE_CHECKING:
    from .logger import AgentLogger


class CursorCLIClient(LLMClient):
    """Client for executing agents via Cursor CLI."""
    
    def __init__(self, project_root: str = ".", output_format: str = "text"):
        """
        Initialize Cursor CLI client.
        
        Args:
            project_root: Project root directory
            output_format: Output format ("text" or "json")
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
    
    def call_agent(
        self, 
        prompt: str, 
        mode: str = "agent", 
        model: Optional[str] = None,
        agent_name: Optional[str] = None,
        logger: Optional["AgentLogger"] = None,
        **kwargs
    ) -> str:
        """
        Execute agent via Cursor CLI.
        
        Args:
            prompt: Prompt string
            mode: Mode ("agent", "plan", "ask")
            model: Model to use (optional)
            agent_name: Name of the agent (optional, for logging)
            logger: Logger instance (optional, for logging command output)
            **kwargs: Other options (e.g., timeout)
        
        Returns:
            Agent output (string)
        """
        cmd = ['agent', '-p', prompt, '--output-format', self.output_format]
        
        if mode != "agent":
            cmd.extend(['--mode', mode])
        
        if model:
            cmd.extend(['--model', model])
        
        timeout = kwargs.get('timeout', 300)  # Default 5 minutes
        command_str = ' '.join(cmd)
        
        # Prepare streaming log if logger is provided
        log_stream = None
        if logger and agent_name:
            try:
                log_stream = logger.start_agent_command_stream(
                    agent_name=agent_name,
                    command=command_str
                )
            except Exception as log_error:
                if logger:
                    logger.warning(f"Failed to start command log stream: {log_error}")
                log_stream = None
        
        try:
            # Start Cursor CLI process with stdout/stderr merged into a single stream
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self.project_root),
                bufsize=1,
            )
        except FileNotFoundError as e:
            # Check if the error is about the working directory or the command
            error_msg = str(e)
            if "No such file or directory" in error_msg and str(self.project_root) in error_msg:
                # The working directory doesn't exist
                raise LLMError(
                    f"Working directory does not exist: {self.project_root}. "
                    f"Please check TARGET_PROJECT or PROJECT_ROOT configuration.",
                    retryable=False,
                    original_error=e
                )
            else:
                # Cursor CLI command not found
                raise LLMError(
                    "Cursor CLI not found. Install with: "
                    "curl https://cursor.com/install -fsS | bash",
                    retryable=False,
                    original_error=e
                )
        except Exception as e:
            # Wrap unexpected errors from process start
            raise LLMError(f"Unexpected error starting Cursor CLI: {e}", retryable=True, original_error=e)
        
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
                    except Exception:
                        # Logging failure should not break main flow
                        pass
        
        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()
        
        try:
            # Wait for process to complete (with timeout)
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as e:
            process.kill()
            if log_stream:
                try:
                    log_stream.write("\n[Cursor CLI timed out]\n")
                except Exception:
                    pass
            raise LLMTimeoutError(timeout, e)
        finally:
            # Ensure reader thread finishes
            reader_thread.join(timeout=5)
            if log_stream:
                try:
                    log_stream.close()
                except Exception:
                    pass
        
        output_text = ''.join(collected_output)
        
        if returncode != 0:
            stderr = output_text or ""
            # Check for rate limit errors
            if "rate limit" in stderr.lower() or "429" in stderr:
                raise LLMRateLimitError(f"Cursor CLI rate limit: {stderr}")
            # Check for timeout-like errors (in message)
            if "timeout" in stderr.lower():
                raise LLMTimeoutError(timeout, RuntimeError(stderr))
            # Other errors are retryable by default
            raise LLMError(f"Cursor CLI error: {stderr}", retryable=True)
        
        return output_text
    
    def call_agent_from_file(
        self, 
        prompt_file: str, 
        mode: str = "agent", 
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Load prompt from file and execute."""
        prompt_path = Path(prompt_file)
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
        
        return self.call_agent(prompt, mode, model, **kwargs)
