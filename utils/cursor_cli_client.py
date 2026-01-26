"""Cursor CLI client implementation."""

import subprocess
from pathlib import Path
from typing import Optional
from .llm_client import LLMClient
from .exceptions import LLMError, LLMTimeoutError, LLMRateLimitError


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
        **kwargs
    ) -> str:
        """Execute agent via Cursor CLI."""
        cmd = ['agent', '-p', prompt, '--output-format', self.output_format]
        
        if mode != "agent":
            cmd.extend(['--mode', mode])
        
        if model:
            cmd.extend(['--model', model])
        
        timeout = kwargs.get('timeout', 300)  # Default 5 minutes
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=timeout
            )
            
            if result.returncode != 0:
                stderr = result.stderr or ""
                # Check for rate limit errors
                if "rate limit" in stderr.lower() or "429" in stderr:
                    raise LLMRateLimitError(f"Cursor CLI rate limit: {stderr}")
                # Check for timeout-like errors
                if "timeout" in stderr.lower():
                    raise LLMTimeoutError(timeout, RuntimeError(stderr))
                # Other errors are retryable by default
                raise LLMError(f"Cursor CLI error: {stderr}", retryable=True)
            
            return result.stdout
        except subprocess.TimeoutExpired as e:
            raise LLMTimeoutError(timeout, e)
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
        except (LLMError, LLMTimeoutError, LLMRateLimitError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise LLMError(f"Unexpected error in Cursor CLI: {e}", retryable=True, original_error=e)
    
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
