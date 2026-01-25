"""Planner agent implementation."""

import json
import re
from typing import Dict, Any
from .base import BaseAgent
from utils.state_manager import StateManager


class PlannerAgent(BaseAgent):
    """Agent that creates tasks and updates plans."""
    
    def __init__(self, *args, **kwargs):
        """Initialize planner agent."""
        super().__init__(*args, **kwargs)
        self.mode = "plan"
    
    def build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for planner."""
        # Load prompt template
        prompt_template_path = self.config.get(
            "prompt_template",
            "prompts/planner.md"
        )
        
        try:
            with open(prompt_template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            # Fallback to simple prompt
            template = """# Planner Agent

Project Goal: {project_goal}
Current Plan: {current_plan}
Existing Tasks: {existing_tasks}

Please create a plan and new tasks in JSON format.
"""
        
        # Format template
        plan = state.get("plan", "")
        tasks = state.get("tasks", {})
        tasks_list = tasks.get("tasks", [])
        
        # Format existing tasks
        existing_tasks_str = "\n".join([
            f"- {t.get('id', 'unknown')}: {t.get('title', 'No title')} ({t.get('status', 'unknown')})"
            for t in tasks_list
        ]) if tasks_list else "なし"
        
        prompt = template.format(
            project_goal=self.config.get("project_goal", "未設定"),
            current_plan=plan if plan else "計画はまだ作成されていません",
            existing_tasks=existing_tasks_str,
            codebase_summary=self._get_codebase_summary()
        )
        
        return prompt
    
    def _get_codebase_summary(self) -> str:
        """Get codebase summary."""
        # Simple implementation: list Python files
        from pathlib import Path
        
        project_root = Path(self.config.get("project_root", "."))
        python_files = list(project_root.glob("**/*.py"))
        
        if len(python_files) > 20:
            return f"コードベースには {len(python_files)} 個以上のPythonファイルがあります。"
        else:
            file_list = "\n".join([f"- {f.relative_to(project_root)}" for f in python_files[:20]])
            return f"主要なファイル:\n{file_list}"
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse planner response."""
        # Try to extract JSON from response
        try:
            # Look for JSON code block
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            # If no JSON found, return response as-is
            return {
                "plan_update": response,
                "new_tasks": [],
                "reasoning": "JSON形式で出力されませんでした"
            }
        except json.JSONDecodeError as e:
            self.logger.warning(f"[{self.name}] Failed to parse JSON: {e}")
            return {
                "plan_update": response,
                "new_tasks": [],
                "reasoning": f"JSON解析エラー: {e}"
            }
    
    def update_state(self, result: Dict[str, Any]) -> None:
        """Update state with planner result."""
        # Update plan
        plan_update = result.get("plan_update", "")
        if plan_update:
            self.state_manager.save_plan(plan_update)
            self.logger.info(f"[{self.name}] Plan updated")
        
        # Add new tasks
        new_tasks = result.get("new_tasks", [])
        for task in new_tasks:
            task_id = self.state_manager.add_task(task)
            self.logger.info(f"[{self.name}] Added task: {task_id} - {task.get('title', 'No title')}")
        
        # Update status
        self.state_manager.update_status(
            last_planner_run=self._get_timestamp(),
            total_tasks=len(self.state_manager.get_tasks().get("tasks", []))
        )
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
