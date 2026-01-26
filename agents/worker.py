"""Worker agent implementation."""

import re
from typing import Dict, Any, Optional
from .base import BaseAgent
from utils.state_manager import StateManager


class WorkerAgent(BaseAgent):
    """Agent that executes tasks."""
    
    def __init__(self, *args, **kwargs):
        """Initialize worker agent."""
        super().__init__(*args, **kwargs)
        self.mode = "agent"  # Worker uses agent mode (not plan)
        self.current_task_id = None
    
    def build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for worker."""
        # Get assigned task from current_task_id (set by assign_task)
        if not self.current_task_id:
            raise ValueError("No task assigned to worker. Call assign_task() first.")
        
        task = self.state_manager.get_task_by_id(self.current_task_id)
        if not task:
            raise ValueError(f"Task {self.current_task_id} not found")
        
        # Load prompt template
        prompt_template_path = self.config.get(
            "prompt_template",
            "prompts/worker.md"
        )
        
        try:
            with open(prompt_template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            # Fallback to simple prompt
            template = """# Worker Agent

Task ID: {task_id}
Task Title: {task_title}
Task Description: {task_description}

Please complete this task and report the result.
"""
        
        # Format template
        prompt = template.format(
            task_id=task.get("id", "unknown"),
            task_title=task.get("title", "No title"),
            task_description=task.get("description", "No description"),
            related_files=self._get_related_files(task)
        )
        
        return prompt
    
    def _get_related_files(self, task: Dict[str, Any]) -> str:
        """Get related files for the task."""
        # Simple implementation: extract file names from description
        description = task.get("description", "")
        # Look for file patterns in description
        file_patterns = re.findall(r'[\w\-_/]+\.(py|ts|js|md|json|yml|yaml)', description)
        if file_patterns:
            return "\n".join([f"- {f}" for f in set(file_patterns)])
        return "関連ファイルの情報がありません"
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse worker response."""
        # Extract report from response
        # Try to find markdown report section
        report_match = re.search(r'# タスク完了レポート.*', response, re.DOTALL)
        if report_match:
            report = report_match.group(0)
        else:
            # If no structured report, use entire response
            report = response
        
        # Try to extract commit info
        commit_hash = None
        commit_message = None
        commit_match = re.search(r'コミットハッシュ[:\s]+([a-f0-9]+)', response, re.IGNORECASE)
        if commit_match:
            commit_hash = commit_match.group(1)
        
        msg_match = re.search(r'コミットメッセージ[:\s]+(.+)', response, re.MULTILINE)
        if msg_match:
            commit_message = msg_match.group(1).strip()
        
        return {
            "report": report,
            "commit_hash": commit_hash,
            "commit_message": commit_message,
            "task_id": self.current_task_id
        }
    
    def update_state(self, result: Dict[str, Any]) -> None:
        """Update state with worker result."""
        task_id = result.get("task_id")
        if not task_id:
            self.logger.error("[Worker] No task ID in result")
            return
        
        # Mark task as completed
        self.state_manager.complete_task(task_id, result)
        self.logger.info(f"[Worker] Task {task_id} completed")
        
        # Update status
        tasks = self.state_manager.get_tasks()
        task_list = tasks.get("tasks", [])
        completed_count = len([t for t in task_list if t.get("status") == "completed"])
        
        self.state_manager.update_status(
            last_worker_run=self._get_timestamp(),
            completed_tasks=completed_count
        )
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def assign_task(self, task_id: str) -> bool:
        """
        Assign a task to this worker.
        
        Args:
            task_id: Task ID to assign
        
        Returns:
            True if task was assigned successfully, False otherwise
        """
        task = self.state_manager.get_task_by_id(task_id)
        if not task:
            self.logger.error(f"[Worker] Task {task_id} not found")
            return False
        
        if task.get("status") != "pending":
            self.logger.warning(f"[Worker] Task {task_id} is not pending (status: {task.get('status')})")
            return False
        
        # Set current_task_id before assigning (used in build_prompt)
        self.current_task_id = task_id
        
        self.state_manager.assign_task(task_id, self.name)
        self.logger.info(f"[Worker] Assigned task {task_id}")
        return True
