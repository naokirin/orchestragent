"""Planner agent implementation."""

import json
from typing import Dict, Any

from .base import BaseAgent
from orchestragent.models import Task
from orchestragent.utils.file_extractor import extract_file_paths_from_text
from orchestragent.utils.json_parser import extract_json_from_response


class PlannerAgent(BaseAgent):
    """Agent that creates tasks and updates plans."""

    def __init__(self, *args, **kwargs):
        """Initialize planner agent."""
        super().__init__(*args, **kwargs)
        self.mode = "plan"

    def build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for planner. Role/instructions come from prompt file; context and output format are injected by the system."""
        user_part = self.load_user_prompt(
            "prompt_template",
            "prompts/planner.md",
            "# Planner Agent\n\nPlease create a plan and new tasks in JSON format.",
        )
        context_block = self._build_planner_context(state)
        output_block = self._build_planner_output_format()
        return self._build_prompt_parts(user_part, context_block, output_block)

    def _build_planner_context(self, state: Dict[str, Any]) -> str:
        """Build context block from system template (contract guaranteed)."""
        plan = state.get("plan", "")
        tasks = state.get("tasks", {})
        status = state.get("status", {})
        tasks_list = tasks.get("tasks", [])

        existing_tasks_str = ""
        if tasks_list:
            task_lines = []
            for task_index in tasks_list:
                task_id = task_index.get("id", "unknown")
                task = self.state_manager.get_task_by_id(task_id)
                task_status = task.status.value if task else "unknown"
                title = task_index.get("title", "No title")
                task_lines.append(f"- {task_id}: {title} ({task_status})")
            existing_tasks_str = "\n".join(task_lines)
        else:
            existing_tasks_str = "None"

        last_plan_judge = status.get("last_plan_judge_feedback")
        if last_plan_judge:
            try:
                last_plan_judge_str = json.dumps(
                    last_plan_judge, indent=2, ensure_ascii=False
                )
            except TypeError:
                last_plan_judge_str = str(last_plan_judge)
        else:
            last_plan_judge_str = "No Plan_Judge feedback yet."

        last_execution_feedback = {
            "reason": status.get("reason"),
            "progress_score": status.get("progress_score"),
            "drift_detected": status.get("drift_detected"),
            "drift_description": status.get("drift_description"),
            "recommendations": status.get("recommendations"),
            "next_iteration_focus": status.get("next_iteration_focus"),
        }
        if any(v is not None for v in last_execution_feedback.values()):
            last_execution_feedback_str = json.dumps(
                last_execution_feedback, indent=2, ensure_ascii=False
            )
        else:
            last_execution_feedback_str = "No Judge execution feedback yet."

        return self._load_system_template(
            "planner_context.md",
            working_dir=self.config.get("project_root", "."),
            project_goal=self.config.get("project_goal", "Not set"),
            current_plan=plan if plan else "No plan has been created yet.",
            last_plan_judge_str=last_plan_judge_str,
            last_execution_feedback_str=last_execution_feedback_str,
            existing_tasks_str=existing_tasks_str,
            codebase_summary=self._get_codebase_summary(),
        )

    def _build_planner_output_format(self) -> str:
        """Build output format block from system template (contract guaranteed)."""
        return self._load_system_template("planner_output.md")

    def _get_codebase_summary(self) -> str:
        """Get codebase summary."""
        # Simple implementation: list Python files
        from pathlib import Path

        project_root = Path(self.config.get("project_root", "."))
        python_files = list(project_root.glob("**/*.py"))

        if len(python_files) > 20:
            return f"The codebase has {len(python_files)}+ Python files."
        else:
            file_list = "\n".join([f"- {f.relative_to(project_root)}" for f in python_files[:20]])
            return f"Key files:\n{file_list}"

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse planner response."""
        result = extract_json_from_response(response)
        if result is not None:
            return result

        # Fallback: return response as-is
        self.logger.warning(f"[{self.name}] Failed to parse JSON from response")
        return {
            "plan_update": response,
            "new_tasks": [],
            "reasoning": "JSON形式で出力されませんでした"
        }

    def update_state(self, result: Dict[str, Any]) -> None:
        """Update state with planner result."""
        # Update plan
        plan_update = result.get("plan_update", "")
        if plan_update:
            self.state_manager.save_plan(plan_update)
            self.logger.info(f"[{self.name}] Plan updated")

        # Update existing tasks if specified
        updated_tasks = result.get("updated_tasks", [])
        for updated in updated_tasks:
            task_id = updated.get("id")
            if not task_id:
                self.logger.warning(f"[{self.name}] updated_tasks entry without id: {updated}")
                continue

            # Only fields other than id are updated
            updates = {k: v for k, v in updated.items() if k != "id"}
            if not updates:
                continue

            try:
                self.state_manager.update_task(task_id, updates)
                self.logger.info(
                    f"[{self.name}] Updated task {task_id}: {', '.join(updates.keys())}"
                )
            except Exception as e:
                self.logger.warning(f"[{self.name}] Failed to update task {task_id}: {e}")

        # Add new tasks
        new_tasks = result.get("new_tasks", [])
        for task in new_tasks:
            # Ensure files field exists (extract from description if not provided)
            if "files" not in task:
                # Try to extract files from description
                description = task.get("description", "")
                files = extract_file_paths_from_text(description)
                if files:
                    task["files"] = files

            task_id = self.state_manager.add_task(task)
            self.logger.info(f"[{self.name}] Added task: {task_id} - {task.get('title', 'No title')}")
            if task.get("files"):
                self.logger.info(f"[{self.name}] Task {task_id} files: {', '.join(task['files'])}")

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
