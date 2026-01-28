"""Plan judge agent implementation."""

import json
import re
from typing import Dict, Any
from .base import BaseAgent


class PlanJudgeAgent(BaseAgent):
    """Agent that evaluates the current plan and task list."""

    def __init__(self, *args, **kwargs):
        """Initialize plan judge agent."""
        super().__init__(*args, **kwargs)
        # Plan_Judge はコードには手を触れない評価専用のため ask モード
        self.mode = "ask"

    def build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for plan judge."""
        # Load prompt template
        prompt_template_path = self.config.get(
            "prompt_template",
            "prompts/plan_judge.md",
        )

        try:
            with open(prompt_template_path, "r", encoding="utf-8") as f:
                template = f.read()
        except FileNotFoundError:
            # Fallback to simple prompt
            template = """# Plan Judge Agent

Project Goal: {project_goal}
Current Plan: {current_plan}
Tasks Summary:
{tasks_summary}

Please evaluate whether this plan and task list are appropriate.
"""

        plan = state.get("plan", "")
        tasks = state.get("tasks", {})
        status = state.get("status", {})
        tasks_list = tasks.get("tasks", [])

        # Format tasks summary (load status from individual task files)
        tasks_summary = ""
        if tasks_list:
            lines = []
            for task_index in tasks_list:
                task_id = task_index.get("id", "unknown")
                title = task_index.get("title", "No title")
                # Plan_Judge は index 情報だけで十分なため、status は index ではなく個別ファイルから取得
                try:
                    task = self.state_manager.get_task_by_id(task_id)
                except Exception:
                    task = None
                if task:
                    task_status = task.get("status", "unknown")
                    priority = task.get("priority", task_index.get("priority", "medium"))
                else:
                    task_status = "unknown"
                    priority = task_index.get("priority", "medium")
                lines.append(
                    f"- {task_id}: {title} (status: {task_status}, priority: {priority})"
                )
            tasks_summary = "\n".join(lines)
        else:
            tasks_summary = "タスクはまだ作成されていません"

        working_dir = self.config.get("project_root", ".")

        prompt = template.format(
            project_goal=self.config.get("project_goal", "未設定"),
            current_plan=plan if plan else "計画はまだ作成されていません",
            tasks_summary=tasks_summary,
            codebase_summary=self._get_codebase_summary(),
            iteration=status.get("current_iteration", 0),
            working_dir=working_dir,
        )

        return prompt

    def _get_codebase_summary(self) -> str:
        """Get codebase summary."""
        from pathlib import Path

        project_root = Path(self.config.get("project_root", "."))
        python_files = list(project_root.glob("**/*.py"))

        if len(python_files) > 20:
            return f"コードベースには {len(python_files)} 個以上のPythonファイルがあります。"
        file_list = "\n".join(
            [f"- {f.relative_to(project_root)}" for f in python_files[:20]]
        )
        return f"主要なファイル:\n{file_list}"

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse plan judge response."""
        try:
            # Look for JSON code block
            json_match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Try to find JSON object directly
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))

            # Fallback: treat as free-form feedback, default to accept
            return {
                "decision": "accept",
                "score": 0.5,
                "issues": [],
                "suggested_changes": response[:500],
            }
        except json.JSONDecodeError as e:
            self.logger.warning(f"[PlanJudge] Failed to parse JSON: {e}")
            return {
                "decision": "accept",
                "score": 0.5,
                "issues": [],
                "suggested_changes": f"JSON解析エラー: {e}. レスポンス: {response[:500]}",
            }

    def update_state(self, result: Dict[str, Any]) -> None:
        """Update state with plan judge result."""
        decision = result.get("decision", "accept")
        score = result.get("score", 0.5)

        # Save full feedback for next Planner run
        self.state_manager.update_status(
            last_plan_judge_run=self._get_timestamp(),
            last_plan_judge_feedback=result,
            last_plan_judge_decision=decision,
            last_plan_judge_score=score,
        )

        self.logger.info(
            f"[PlanJudge] Decision: {decision}, score: {score}, "
            f"issues: {len(result.get('issues', []))}"
        )

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().isoformat()

