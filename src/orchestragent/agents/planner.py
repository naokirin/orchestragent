"""Planner agent implementation."""

import json
import re
from typing import Dict, Any

from .base import BaseAgent
from orchestragent.models import Task


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
        status = state.get("status", {})
        tasks_list = tasks.get("tasks", [])

        # Format existing tasks (load status from individual task files)
        existing_tasks_str = ""
        if tasks_list:
            task_lines = []
            for task_index in tasks_list:
                task_id = task_index.get("id", "unknown")
                # Load full task data to get current status
                task = self.state_manager.get_task_by_id(task_id)
                if task:
                    task_status = task.status.value
                else:
                    # Fallback to index data if individual file doesn't exist
                    task_status = "unknown"
                title = task_index.get("title", "No title")
                task_lines.append(f"- {task_id}: {title} ({task_status})")
            existing_tasks_str = "\n".join(task_lines)
        else:
            existing_tasks_str = "なし"

        # Previous Plan_Judge feedback
        last_plan_judge = status.get("last_plan_judge_feedback")
        if last_plan_judge:
            try:
                last_plan_judge_str = json.dumps(
                    last_plan_judge, indent=2, ensure_ascii=False
                )
            except TypeError:
                last_plan_judge_str = str(last_plan_judge)
        else:
            last_plan_judge_str = "まだ Plan_Judge のフィードバックはありません。"

        # Previous execution (Judge) feedback
        last_execution_feedback = {
            "reason": status.get("reason"),
            "progress_score": status.get("progress_score"),
            "drift_detected": status.get("drift_detected"),
            "drift_description": status.get("drift_description"),
            "recommendations": status.get("recommendations"),
            "next_iteration_focus": status.get("next_iteration_focus"),
        }
        # フィードバックがまったく存在しない場合は簡易メッセージにする
        if any(v is not None for v in last_execution_feedback.values()):
            last_execution_feedback_str = json.dumps(
                last_execution_feedback, indent=2, ensure_ascii=False
            )
        else:
            last_execution_feedback_str = "まだ Judge の実行結果フィードバックはありません。"

        # Get working directory from config
        working_dir = self.config.get("project_root", ".")

        prompt = template.format(
            project_goal=self.config.get("project_goal", "未設定"),
            current_plan=plan if plan else "計画はまだ作成されていません",
            existing_tasks=existing_tasks_str,
             last_plan_judge_feedback=last_plan_judge_str,
             last_execution_feedback=last_execution_feedback_str,
            codebase_summary=self._get_codebase_summary(),
            working_dir=working_dir
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

        # Update existing tasks if specified
        updated_tasks = result.get("updated_tasks", [])
        for updated in updated_tasks:
            task_id = updated.get("id")
            if not task_id:
                self.logger.warning(f"[{self.name}] updated_tasks entry without id: {updated}")
                continue

            # id 以外のフィールドだけを更新対象とする
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
                files = self._extract_files_from_description(description)
                if files:
                    task["files"] = files

            task_id = self.state_manager.add_task(task)
            self.logger.info(f"[{self.name}] Added task: {task_id} - {task.get('title', 'No title')}")
            if task.get("files"):
                self.logger.info(f"[{self.name}] Task {task_id} files: {', '.join(task['files'])}")

    def _extract_files_from_description(self, description: str) -> list:
        """Extract file paths from task description."""
        import re
        files = []

        # Pattern 1: Explicit file mentions
        explicit_pattern = r'file:\s*([^\s\n]+\.(py|ts|js|md|json|yml|yaml|txt|html|css))'
        matches = re.findall(explicit_pattern, description, re.IGNORECASE)
        files.extend([m[0] for m in matches])

        # Pattern 2: File paths in quotes
        quoted_pattern = r'["\'`]([^\'"`]+\.(py|ts|js|md|json|yml|yaml|txt|html|css))["\'`]'
        matches = re.findall(quoted_pattern, description, re.IGNORECASE)
        files.extend([m[0] for m in matches])

        # Normalize and deduplicate
        normalized_files = []
        seen = set()
        for filepath in files:
            normalized = filepath.strip().strip('"\'`')
            if normalized and normalized not in seen:
                normalized_files.append(normalized)
                seen.add(normalized)

        return normalized_files

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
