"""Logging utilities for the agent system."""

import json
import logging
import os
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler
import traceback


class AgentLogger:
    """Logger for agent execution."""
    
    def __init__(
        self,
        log_dir: str = "logs",
        log_level: str = "INFO",
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        sync: bool = False,
    ):
        """
        Initialize logger.
        
        Args:
            log_dir: Directory for log files
            log_level: Log level (DEBUG, INFO, WARNING, ERROR)
            max_bytes: Maximum size of log file before rotation (default: 10MB)
            backup_count: Number of backup files to keep (default: 5)
        """
        self.log_dir = Path(log_dir)
        # If True, force flush and fsync after each write to JSONL logs.
        # Useful when logs need to be visible in (near) real-time on host volumes.
        self.sync = sync
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Python logging with rotation
        log_file = self.log_dir / f"execution_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Use RotatingFileHandler for log rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        
        # Setup logger
        self.logger = logging.getLogger("agent_system")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Prevent duplicate logs
        self.logger.propagate = False

    def _flush_and_sync(self, file_obj) -> None:
        """Ensure log contents are flushed to disk when sync is enabled."""
        if not self.sync:
            return
        try:
            file_obj.flush()
            os.fsync(file_obj.fileno())
        except OSError:
            # In some environments (e.g. special filesystems), fsync may not be supported.
            # We ignore such errors to avoid breaking logging entirely.
            pass
    
    def log_agent_run(
        self,
        agent_name: str,
        iteration: int,
        prompt: str,
        response: str,
        duration: float,
        **kwargs
    ) -> None:
        """
        Log agent execution.
        
        Args:
            agent_name: Name of the agent
            iteration: Iteration number
            prompt: Prompt used
            response: Response received
            duration: Duration in seconds
            **kwargs: Additional metadata
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent': agent_name,
            'iteration': iteration,
            'prompt_length': len(prompt),
            'response_length': len(response),
            'duration_seconds': round(duration, 3),
            **kwargs
        }
        
        # Log to JSON file
        log_file = self.log_dir / f"execution_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            self._flush_and_sync(f)
        
        # Log to standard logger
        self.logger.info(
            f"[{agent_name}] Iteration {iteration} completed in {duration:.2f}s "
            f"(prompt: {len(prompt)} chars, response: {len(response)} chars)"
        )
    
    def log_error_with_traceback(
        self,
        agent_name: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log error with full traceback and context.
        
        Args:
            agent_name: Name of the agent
            error: Exception that occurred
            context: Additional context information
        """
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent': agent_name,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }
        
        # Log to JSON file
        log_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(error_entry, ensure_ascii=False) + '\n')
            self._flush_and_sync(f)
        
        # Log to standard logger
        self.logger.error(
            f"[{agent_name}] Error: {type(error).__name__}: {error}"
        )
        self.logger.debug(f"[{agent_name}] Traceback:\n{traceback.format_exc()}")
    
    def log_progress(
        self,
        iteration: int,
        total_tasks: int,
        completed_tasks: int,
        failed_tasks: int,
        pending_tasks: int
    ) -> None:
        """
        Log progress summary.
        
        Args:
            iteration: Current iteration number
            total_tasks: Total number of tasks
            completed_tasks: Number of completed tasks
            failed_tasks: Number of failed tasks
            pending_tasks: Number of pending tasks
        """
        progress_entry = {
            'timestamp': datetime.now().isoformat(),
            'iteration': iteration,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'pending_tasks': pending_tasks,
            'completion_rate': round(completed_tasks / total_tasks * 100, 2) if total_tasks > 0 else 0
        }
        
        # Log to JSON file
        log_file = self.log_dir / f"progress_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(progress_entry, ensure_ascii=False) + '\n')
            self._flush_and_sync(f)
        
        # Log to standard logger
        self.logger.info(
            f"[Progress] Iteration {iteration}: "
            f"{completed_tasks}/{total_tasks} completed, "
            f"{failed_tasks} failed, {pending_tasks} pending"
        )
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
    
    def exception(self, message: str, exc_info: bool = True) -> None:
        """Log exception with traceback."""
        self.logger.exception(message, exc_info=exc_info)
    
    def log_agent_command_output(
        self,
        agent_name: str,
        stdout: str,
        stderr: str,
        command: Optional[str] = None
    ) -> Path:
        """
        Log agent command output to individual log file (non-streaming API).
        For streaming use-cases, prefer `start_agent_command_stream`.
        
        Args:
            agent_name: Name of the agent
            stdout: Standard output from the command
            stderr: Standard error output from the command
            command: Command that was executed (optional)
        
        Returns:
            Path to the log file created
        """
        stream = self.start_agent_command_stream(agent_name=agent_name, command=command)
        
        # Write stdout
        if stdout:
            stream.write("=== Standard Output ===\n")
            stream.write(stdout)
            if not stdout.endswith('\n'):
                stream.write('\n')
            stream.write("\n")
        
        # Write stderr
        if stderr:
            stream.write("=== Standard Error ===\n")
            stream.write(stderr)
            if not stderr.endswith('\n'):
                stream.write('\n')
            stream.write("\n")
        
        stream.close()
        
        # Log to standard logger
        self.logger.info(
            f"[{agent_name}] Agent command output logged to: {stream.log_file}"
        )
        
        return stream.log_file

    def start_agent_command_stream(
        self,
        agent_name: str,
        command: Optional[str] = None
    ) -> "_AgentCommandLogStream":
        """
        Start a streaming log file for agent command output.
        Returns a stream object that can be written to incrementally.
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        thread_id = threading.get_ident()
        safe_agent_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in agent_name)
        log_filename = f"agent_{safe_agent_name}_{timestamp}_{thread_id}.log"
        log_file = self.log_dir / log_filename
        
        stream = _AgentCommandLogStream(log_file=log_file, logger=self)
        
        # Header
        stream.write("Agent Command Output Log\n")
        stream.write(f"{'=' * 60}\n")
        stream.write(f"Agent: {agent_name}\n")
        stream.write(f"Timestamp: {datetime.now().isoformat()}\n")
        stream.write(f"Thread ID: {thread_id}\n")
        if command:
            stream.write(f"Command: {command}\n")
        stream.write(f"{'=' * 60}\n\n")
        
        return stream


class _AgentCommandLogStream:
    """Streaming writer for agent command log files."""
    
    def __init__(self, log_file: Path, logger: AgentLogger):
        self.log_file = log_file
        self._logger = logger
        self._file = open(log_file, 'w', encoding='utf-8')
        self._closed = False
    
    def write(self, text: str) -> None:
        if self._closed:
            return
        self._file.write(text)
        self._logger._flush_and_sync(self._file)
    
    def close(self) -> None:
        if self._closed:
            return
        # Footer
        self._file.write(f"{'=' * 60}\n")
        self._file.write("End of log\n")
        self._logger._flush_and_sync(self._file)
        self._file.close()
        self._closed = True
