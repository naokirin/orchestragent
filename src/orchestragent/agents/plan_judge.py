"""Plan judge agent implementation."""

import logging
from typing import Dict, Any

from .base import BaseAgent
from orchestragent.models import Task
from orchestragent.utils.json_parser import extract_json_from_response

logger = logging.getLogger(__name__)


class PlanJudgeAgent(BaseAgent):
    """Agent that evaluates the current plan and task list."""

    def __init__(self, *args, **kwargs):
        """Initialize plan judge agent."""
        super().__init__(*args, **kwargs)
        # Plan_Judge はコードには手を触れない評価専用のため ask モード
        self.mode = "ask"

    def build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for plan judge.
        プロンプトファイルは「役割・指示」のみ。現在の状況と出力形式はシステムが自動付与する。
        """
        user_part = self.load_user_prompt(
            "prompt_template",
            "prompts/plan_judge.md",
            "# Plan Judge Agent\n\nPlease evaluate whether this plan and task list are appropriate.",
        )
        context_block = self._build_plan_judge_context(state)
        output_block = self._build_plan_judge_output_format()
        return self._build_prompt_parts(user_part, context_block, output_block)

    def _build_plan_judge_context(self, state: Dict[str, Any]) -> str:
        """Build context block from system template (contract guaranteed)."""
        plan = state.get("plan", "")
        tasks = state.get("tasks", {})
        status = state.get("status", {})
        tasks_list = tasks.get("tasks", [])

        tasks_summary = ""
        if tasks_list:
            lines = []
            for task_index in tasks_list:
                task_id = task_index.get("id", "unknown")
                title = task_index.get("title", "No title")
                try:
                    task = self.state_manager.get_task_by_id(task_id)
                except (OSError, ValueError, KeyError) as e:
                    logger.warning("Failed to get task %s: %s", task_id, e)
                    task = None
                if task:
                    task_status = task.status.value
                    priority = task.priority.value
                else:
                    task_status = "unknown"
                    priority = task_index.get("priority", "medium")
                lines.append(
                    f"- {task_id}: {title} (status: {task_status}, priority: {priority})"
                )
            tasks_summary = "\n".join(lines)
        else:
            tasks_summary = "タスクはまだ作成されていません"

        return self._load_system_template(
            "plan_judge_context.md",
            working_dir=self.config.get("project_root", "."),
            project_goal=self.config.get("project_goal", "未設定"),
            current_plan=plan if plan else "計画はまだ作成されていません",
            tasks_summary=tasks_summary,
            codebase_summary=self._get_codebase_summary(),
            iteration=status.get("current_iteration", 0),
        )

    def _build_plan_judge_output_format(self) -> str:
        """Build output format block from system template (contract guaranteed)."""
        return self._load_system_template("plan_judge_output.md")

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
        result = extract_json_from_response(response)
        if result is not None:
            return result

        # Fallback: treat as free-form feedback, default to accept
        self.logger.warning("[Plan_Judge] Failed to parse JSON from response")
        return {
            "decision": "accept",
            "score": 0.5,
            "issues": [],
            "suggested_changes": response[:500],
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
            f"[Plan_Judge] Decision: {decision}, score: {score}, "
            f"issues: {len(result.get('issues', []))}"
        )

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().isoformat()
