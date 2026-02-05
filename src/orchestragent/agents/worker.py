"""Worker agent implementation."""

import re
from typing import Dict, Any, Optional

from .base import BaseAgent
from orchestragent.models import Task
from orchestragent.utils.file_extractor import extract_file_paths_from_text
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
        """Initialize worker agent. Config is injected; state_dir, adr_dir, model_* use defaults when omitted."""
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
        """Build prompt for worker. Role/instructions come from prompt file; assigned task and output format are injected by the system."""
        if not self.current_task_id:
            raise ValueError("No task assigned to worker. Call assign_task() first.")
        task = self.state_manager.get_task_by_id(self.current_task_id)
        if not task:
            raise ValueError(f"Task {self.current_task_id} not found")

        import config as _config
        user_part = self.load_user_prompt(
            "prompt_template",
            _config.AGENT_CONFIG["prompt_template_worker"],
            "# Worker Agent\n\nPlease complete the assigned task and report the result.",
        )
        context_block = self._build_worker_context(task)
        output_block = self._build_worker_output_format(task.id)
        return self._build_prompt_parts(user_part, context_block, output_block)

    def _build_worker_context(self, task: Task) -> str:
        """Build context block from system template (contract guaranteed)."""
        return self._load_system_template(
            "worker_context.md",
            working_dir=self.config.get("project_root", "."),
            task_id=task.id,
            task_title=task.title,
            task_description=task.description,
            related_files=self._get_related_files(task),
        )

    def _build_worker_output_format(self, task_id: str) -> str:
        """Build output format block from system template (contract guaranteed)."""
        return self._load_system_template("worker_output.md", task_id=task_id)

    def _get_related_files(self, task: Task) -> str:
        """Get related files for the task."""
        files = extract_file_paths_from_text(
            task.description,
            include_common_pattern=True,
        )
        if files:
            return "\n".join([f"- {f}" for f in files])
        return "No related files information."

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse worker response including Intent extraction."""
        try:
            # Extract report from response
            # Try to find markdown report section
            report_match = re.search(
                r'# (?:Task Report|タスク完了レポート)[:\s].*', response, re.DOTALL | re.IGNORECASE
            )
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
                    r'[-*]*\s*\**(?:Commit hash|コミットハッシュ)[:\*\s]+`?([a-f0-9]+)`?',
                    response,
                    re.IGNORECASE
                )
                msg_matches = re.findall(
                    r'[-*]*\s*\**(?:Commit message|コミットメッセージ)[:\*\s]+`?(.+)`?',
                    response,
                    re.MULTILINE | re.IGNORECASE
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

        # Select model tier based on task complexity (if enabled)
        # This uses the new model_tier approach for per-backend dynamic models
        model_tier = self.model_selector.select_model_tier(task)

        if model_tier:
            complexity_score = self.model_selector.calculate_complexity_score(task)
            self.logger.info(
                f"[Worker] Model tier selected: {model_tier} "
                f"(score: {complexity_score:.2f})"
            )
            # Set model tier for the LLM client call
            self._model_tier = model_tier

        try:
            # Call parent's _run_internal() which will use self._model_tier
            result = super()._run_internal(iteration, start_time)
            return result
        finally:
            # Reset model tier
            self._model_tier = None
