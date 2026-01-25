"""Judge agent implementation."""

import json
import re
from typing import Dict, Any
from .base import BaseAgent
from utils.state_manager import StateManager


class JudgeAgent(BaseAgent):
    """Agent that evaluates progress and decides whether to continue."""
    
    def __init__(self, *args, **kwargs):
        """Initialize judge agent."""
        super().__init__(*args, **kwargs)
        self.mode = "ask"  # Judge uses ask mode (read-only)
    
    def build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for judge."""
        # Load prompt template
        prompt_template_path = self.config.get(
            "prompt_template",
            "prompts/judge.md"
        )
        
        try:
            with open(prompt_template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            # Fallback to simple prompt
            template = """# Judge Agent

Project Goal: {project_goal}
Current Plan: {current_plan}
Tasks: {total_tasks} total, {completed_tasks} completed, {pending_tasks} pending

Please evaluate progress and decide whether to continue.
"""
        
        # Get task statistics
        tasks = state.get("tasks", {})
        task_list = tasks.get("tasks", [])
        total_tasks = len(task_list)
        completed_tasks = len([t for t in task_list if t.get("status") == "completed"])
        failed_tasks = len([t for t in task_list if t.get("status") == "failed"])
        pending_tasks = len([t for t in task_list if t.get("status") == "pending"])
        
        # Get completed task results
        completed_results = []
        for task in task_list:
            if task.get("status") == "completed":
                result_file = task.get("result_file")
                if result_file:
                    try:
                        result_content = self.state_manager.load_text(result_file)
                        completed_results.append(f"### {task.get('id')}: {task.get('title')}\n{result_content[:200]}...")
                    except:
                        pass
        
        completed_results_str = "\n\n".join(completed_results) if completed_results else "完了したタスクはありません"
        
        # Format template
        prompt = template.format(
            project_goal=self.config.get("project_goal", "未設定"),
            current_plan=state.get("plan", "計画はまだ作成されていません"),
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            pending_tasks=pending_tasks,
            completed_task_results=completed_results_str,
            iteration=state.get("status", {}).get("iteration", 0)
        )
        
        return prompt
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse judge response."""
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
            
            # If no JSON found, try to extract key information
            should_continue = "継続" in response or "continue" in response.lower() or "true" in response.lower()
            return {
                "should_continue": should_continue,
                "reason": response[:500],  # First 500 chars
                "progress_score": 0.5,
                "drift_detected": False,
                "recommendations": [],
                "next_iteration_focus": "JSON形式で出力されませんでした"
            }
        except json.JSONDecodeError as e:
            self.logger.warning(f"[Judge] Failed to parse JSON: {e}")
            # Fallback: extract from text
            should_continue = "継続" in response or "continue" in response.lower()
            return {
                "should_continue": should_continue,
                "reason": f"JSON解析エラー: {e}. レスポンス: {response[:500]}",
                "progress_score": 0.5,
                "drift_detected": False,
                "recommendations": [],
                "next_iteration_focus": "JSON形式で出力してください"
            }
    
    def update_state(self, result: Dict[str, Any]) -> None:
        """Update state with judge result."""
        should_continue = result.get("should_continue", True)
        reason = result.get("reason", "判定理由がありません")
        progress_score = result.get("progress_score", 0.5)
        drift_detected = result.get("drift_detected", False)
        
        # Update status
        self.state_manager.update_status(
            last_judge_run=self._get_timestamp(),
            should_continue=should_continue,
            reason=reason,
            progress_score=progress_score,
            drift_detected=drift_detected
        )
        
        self.logger.info(f"[Judge] Should continue: {should_continue}, Reason: {reason[:100]}")
        
        if drift_detected:
            self.logger.warning(f"[Judge] Drift detected: {result.get('drift_description', 'N/A')}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
