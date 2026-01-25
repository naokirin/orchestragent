"""Logging utilities for the agent system."""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class AgentLogger:
    """Logger for agent execution."""
    
    def __init__(self, log_dir: str = "logs", log_level: str = "INFO"):
        """
        Initialize logger.
        
        Args:
            log_dir: Directory for log files
            log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Python logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_dir / f"execution_{datetime.now().strftime('%Y%m%d')}.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("agent_system")
    
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
            'duration_seconds': duration,
            **kwargs
        }
        
        # Log to JSON file
        log_file = self.log_dir / f"execution_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        # Log to standard logger
        self.logger.info(
            f"[{agent_name}] Iteration {iteration} completed in {duration:.2f}s"
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
