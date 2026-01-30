"""Worker agent implementation."""

import re
import time
from typing import Dict, Any, Optional
from .base import BaseAgent
from utils.state_manager import StateManager
from utils.model_selector import ModelSelector
from utils.intent_parser import IntentParser
from utils.intent_manager import IntentManager
import config


class WorkerAgent(BaseAgent):
    """Agent that executes tasks."""
    
    def __init__(self, *args, **kwargs):
        """Initialize worker agent."""
        super().__init__(*args, **kwargs)
        self.mode = "agent"  # Worker uses agent mode (not plan)
        self.current_task_id = None

        # Initialize model selector for dynamic model selection
        self.model_selector = ModelSelector(
            enabled=config.MODEL_SELECTION_ENABLED,
            threshold_light=config.MODEL_COMPLEXITY_THRESHOLD_LIGHT,
            threshold_powerful=config.MODEL_COMPLEXITY_THRESHOLD_POWERFUL,
            model_light=config.WORKER_MODEL_LIGHT,
            model_standard=config.WORKER_MODEL_STANDARD,
            model_powerful=config.WORKER_MODEL_POWERFUL,
            model_default=config.WORKER_MODEL
        )

        # Initialize intent manager for tracking change intents
        self.intent_manager = IntentManager(state_dir=config.STATE_DIR)
    
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
        
        # Get working directory from config
        working_dir = self.config.get("project_root", ".")
        
        # Format template
        prompt = template.format(
            task_id=task.get("id", "unknown"),
            task_title=task.get("title", "No title"),
            task_description=task.get("description", "No description"),
            related_files=self._get_related_files(task),
            working_dir=working_dir
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
        """Parse worker response including Intent extraction."""
        try:
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

            result = {
                "report": report,
                "commit_hash": commit_hash,
                "commit_message": commit_message,
                "task_id": self.current_task_id
            }

            # Ensure task_id is set
            if not result.get("task_id"):
                result["task_id"] = self.current_task_id

            # Extract Intent information from response
            intent_data = IntentParser.parse(response, self.current_task_id)
            if intent_data:
                result["intent"] = intent_data
                self.logger.info(f"[Worker] Intent extracted for task {self.current_task_id}")

            return result
        except Exception as e:
            self.logger.error(f"[Worker] Error parsing response: {e}")
            # Return a safe fallback result
            return {
                "report": response[:1000] if response else "No response",
                "commit_hash": None,
                "commit_message": None,
                "task_id": self.current_task_id,
                "error": str(e)
            }
    
    def update_state(self, result: Dict[str, Any]) -> None:
        """Update state with worker result including Intent saving."""
        # Ensure result is a dictionary
        if not isinstance(result, dict):
            raise ValueError(f"result must be a dict, got {type(result)}")

        task_id = result.get("task_id") or self.current_task_id
        if not task_id:
            self.logger.error("[Worker] No task ID in result")
            raise ValueError("No task ID available")

        # Mark task as completed
        try:
            self.state_manager.complete_task(task_id, result)
            self.logger.info(f"[Worker] Task {task_id} completed")
        except Exception as e:
            self.logger.error(f"[Worker] Error completing task: {e}")
            raise

        # Save Intent if present
        if "intent" in result and result["intent"]:
            try:
                filepath = self.intent_manager.save_intent(result["intent"])
                self.logger.info(f"[Worker] Intent saved for task {task_id}: {filepath}")
            except Exception as e:
                self.logger.warning(f"[Worker] Failed to save intent: {e}")

        # Update status (use task statistics from individual task files)
        task_stats = self.state_manager.get_task_statistics()
        completed_count = task_stats.get("completed", 0)

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
    
    def _run_internal(self, iteration: int, start_time: float) -> Dict[str, Any]:
        """
        Internal run method with dynamic model selection.
        
        Args:
            iteration: Current iteration number
            start_time: Start time for duration calculation
        
        Returns:
            Result dictionary
        """
        # Get current task for model selection
        if not self.current_task_id:
            raise ValueError("No task assigned to worker. Call assign_task() first.")
        
        task = self.state_manager.get_task_by_id(self.current_task_id)
        if not task:
            raise ValueError(f"Task {self.current_task_id} not found")
        
        # Select model based on task complexity (if enabled)
        original_model = self.config.get("model")
        selected_model = self.model_selector.select_model(task)
        
        if selected_model != original_model:
            # Temporarily update model in config
            self.config["model"] = selected_model
            complexity_category = self.model_selector.get_complexity_category(task)
            complexity_score = self.model_selector.calculate_complexity_score(task)
            self.logger.info(
                f"[Worker] Model selected: {selected_model} "
                f"(category: {complexity_category}, score: {complexity_score:.2f})"
            )
        
        try:
            # Call parent's _run_internal() with selected model
            result = super()._run_internal(iteration, start_time)
            return result
        finally:
            # Restore original model in config
            if selected_model != original_model:
                self.config["model"] = original_model