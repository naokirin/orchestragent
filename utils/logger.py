"""Logging utilities for the agent system."""

import json
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler
import traceback


class AgentLogger:
    """Logger for agent execution."""
    
    def __init__(self, log_dir: str = "logs", log_level: str = "INFO", max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5):
        """
        Initialize logger.
        
        Args:
            log_dir: Directory for log files
            log_level: Log level (DEBUG, INFO, WARNING, ERROR)
            max_bytes: Maximum size of log file before rotation (default: 10MB)
            backup_count: Number of backup files to keep (default: 5)
        """
        self.log_dir = Path(log_dir)
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
        Log agent command output to individual log file.
        
        Args:
            agent_name: Name of the agent
            stdout: Standard output from the command
            stderr: Standard error output from the command
            command: Command that was executed (optional)
        
        Returns:
            Path to the log file created
        """
        # Generate unique log file name with agent name, timestamp, and thread ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        thread_id = threading.get_ident()
        # Sanitize agent name for filename (replace special characters)
        safe_agent_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in agent_name)
        log_filename = f"agent_{safe_agent_name}_{timestamp}_{thread_id}.log"
        log_file = self.log_dir / log_filename
        
        # Write to log file
        with open(log_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"Agent Command Output Log\n")
            f.write(f"{'=' * 60}\n")
            f.write(f"Agent: {agent_name}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Thread ID: {thread_id}\n")
            if command:
                f.write(f"Command: {command}\n")
            f.write(f"{'=' * 60}\n\n")
            
            # Write stdout
            if stdout:
                f.write("=== Standard Output ===\n")
                f.write(stdout)
                if not stdout.endswith('\n'):
                    f.write('\n')
                f.write("\n")
            
            # Write stderr
            if stderr:
                f.write("=== Standard Error ===\n")
                f.write(stderr)
                if not stderr.endswith('\n'):
                    f.write('\n')
                f.write("\n")
            
            f.write(f"{'=' * 60}\n")
            f.write(f"End of log\n")
        
        # Log to standard logger
        self.logger.info(
            f"[{agent_name}] Agent command output logged to: {log_file}"
        )
        
        return log_file
