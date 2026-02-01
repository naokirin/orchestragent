"""Worker agent implementation."""

import re
from typing import Dict, Any, Optional

from .base import BaseAgent
from orchestragent.models import Task
from orchestragent.llm.model_selector import ModelSelector
from orchestragent.tracking.intent_parser import IntentParser
from orchestragent.tracking.intent_manager import IntentManager
from orchestragent.tracking.adr_manager import ADRManager


class WorkerAgent(BaseAgent):
    """Agent that executes tasks."""

    def __init__(
        self,
        *args,
        state_dir: str = "state",
        adr_dir: str = "docs/adr",
        model_selection_enabled: bool = False,
        model_complexity_threshold_light: float = 10.0,
        model_complexity_threshold_powerful: float = 30.0,
        worker_model_light: Optional[str] = None,
        worker_model_standard: Optional[str] = None,
        worker_model_powerful: Optional[str] = None,
        worker_model_default: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize worker agent.
        設定は依存性注入で受け取る。state_dir, adr_dir, model_* は省略時はデフォルト値を使用。
        """
        super().__init__(*args, **kwargs)
        self.mode = "agent"  # Worker uses agent mode (not plan)
        self.current_task_id = None

        # Initialize model selector from injected config
        self.model_selector = ModelSelector(
            enabled=model_selection_enabled,
            threshold_light=model_complexity_threshold_light,
            threshold_powerful=model_complexity_threshold_powerful,
            model_light=worker_model_light,
            model_standard=worker_model_standard,
            model_powerful=worker_model_powerful,
            model_default=worker_model_default,
        )

        # Initialize intent manager and ADR manager from injected config
        self.intent_manager = IntentManager(state_dir=state_dir)
        self.adr_manager = ADRManager(adr_dir=adr_dir)

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
            task_id=task.id,
            task_title=task.title,
            task_description=task.description,
            related_files=self._get_related_files(task),
            working_dir=working_dir
        )

        return prompt

    def _get_related_files(self, task: Task) -> str:
        """Get related files for the task."""
        # Simple implementation: extract file names from description
        description = task.description
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

            # Extract Intent information from response (includes commits list)
            intent_data = IntentParser.parse(response, self.current_task_id)

            # Build commits list: use intent_data["commits"] if present, else extract with regex
            commits = []
            if intent_data and intent_data.get("commits"):
                commits = [
                    {"hash": c["hash"], "message": c.get("message", "") or ""}
                    for c in intent_data["commits"]
                ]
            else:
                # Fallback: extract all commit hashes and messages by regex
                hash_matches = re.findall(
                    r'[-*]*\s*\**コミットハッシュ[:\*\s]+`?([a-f0-9]+)`?',
                    response,
                    re.IGNORECASE
                )
                msg_matches = re.findall(
                    r'[-*]*\s*\**コミットメッセージ[:\*\s]+`?(.+)`?',
                    response,
                    re.MULTILINE
                )
                for i, h in enumerate(hash_matches):
                    msg = msg_matches[i].strip() if i < len(msg_matches) else ""
                    commits.append({"hash": h, "message": msg})

            result = {
                "report": report,
                "commits": commits,
                "task_id": self.current_task_id
            }
            # Backward compat: first commit as commit_hash / commit_message
            if commits:
                result["commit_hash"] = commits[0]["hash"]
                result["commit_message"] = commits[0]["message"]
            else:
                result["commit_hash"] = None
                result["commit_message"] = None

            # Ensure task_id is set
            if not result.get("task_id"):
                result["task_id"] = self.current_task_id

            if intent_data:
                result["intent"] = intent_data
                self.logger.info(f"[Worker] Intent extracted for task {self.current_task_id}")

            return result
        except Exception as e:
            self.logger.error(f"[Worker] Error parsing response: {e}")
            # Return a safe fallback result
            return {
                "report": response[:1000] if response else "No response",
                "commits": [],
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

        # Create ADR first if Worker reported an architecture/design decision
        intent_data = result.get("intent")
        if intent_data and intent_data.get("adr_to_create"):
            adr_spec = intent_data["adr_to_create"]
            title = adr_spec.get("title") if isinstance(adr_spec, dict) else None
            if title and title.strip():
                try:
                    adr_number = self.adr_manager.create_adr(
                        title=title.strip(),
                        context=adr_spec.get("context", ""),
                        decision=adr_spec.get("decision", ""),
                        rationale=adr_spec.get("rationale", ""),
                        consequences=adr_spec.get("consequences", ""),
                        related_intents=[task_id],
                        status="Proposed",
                    )
                    # Link this intent to the new ADR (overwrite related_adr)
                    intent_data["related_adr"] = adr_number
                    self.logger.info(f"[Worker] ADR-{adr_number} created and linked to task {task_id}")
                except Exception as e:
                    self.logger.warning(f"[Worker] Failed to create ADR: {e}")
            # Remove adr_to_create so we don't persist it in the intent YAML
            intent_data.pop("adr_to_create", None)

        # Save Intent if present
        if "intent" in result and result["intent"]:
            try:
                filepath = self.intent_manager.save_intent(result["intent"])
                self.logger.info(f"[Worker] Intent saved for task {task_id}: {filepath}")

                # Add all commits to Intent (intent_data already has commits; add_commit dedupes)
                for c in result.get("commits", []):
                    ch = c.get("hash")
                    if ch:
                        self.intent_manager.add_commit_to_intent(
                            task_id,
                            ch,
                            c.get("message") or ""
                        )
                        self.logger.info(f"[Worker] Commit {ch[:8]} added to Intent {task_id}")
            except Exception as e:
                self.logger.warning(f"[Worker] Failed to save intent: {e}")

        # Update status (use task statistics from individual task files)
        task_stats = self.state_manager.get_task_statistics()
        completed_count = task_stats.completed

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

        if not task.is_pending():
            self.logger.warning(f"[Worker] Task {task_id} is not pending (status: {task.status.value})")
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
