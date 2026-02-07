"""Judge agent implementation."""

from typing import Dict, Any

from .base import BaseAgent
from orchestragent.utils.json_parser import extract_json_from_response


class JudgeAgent(BaseAgent):
    """Agent that evaluates progress and decides whether to continue."""

    def __init__(self, *args, **kwargs):
        """Initialize judge agent."""
        super().__init__(*args, **kwargs)
        self.mode = "ask"  # Judge uses ask mode (read-only)

    def build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for judge. Role/instructions come from prompt file; context and output format are injected by the system."""
        import config as _config
        user_part = self.load_user_prompt(
            "prompt_template",
            _config.AGENT_CONFIG["prompt_template_judge"],
            "# Judge Agent\n\nPlease evaluate progress and decide whether to continue.",
        )
        context_block = self._build_judge_context(state)
        output_block = self._build_judge_output_format()
        return self._build_prompt_parts(user_part, context_block, output_block)

    def _build_judge_context(self, state: Dict[str, Any]) -> str:
        """Build context block from system template (contract guaranteed)."""
        task_stats = self.state_manager.get_task_statistics()
        all_tasks = self.state_manager.get_all_tasks_from_files()
        completed_results = []
        for task in all_tasks:
            if task.is_completed() and task.result_file:
                try:
                    result_content = self.state_manager.load_text(task.result_file)
                    completed_results.append(
                        f"### {task.id}: {task.title}\n{result_content[:200]}..."
                    )
                except Exception:
                    pass
        completed_results_str = (
            "\n\n".join(completed_results) if completed_results else "No completed tasks."
        )
        return self._load_system_template(
            "judge_context.md",
            project_goal=self.config.get("project_goal", "Not set"),
            current_plan=state.get("plan", "No plan has been created yet."),
            total_tasks=task_stats.total,
            completed_tasks=task_stats.completed,
            failed_tasks=task_stats.failed,
            pending_tasks=task_stats.pending,
            completed_task_results=completed_results_str,
            iteration=state.get("status", {}).get("iteration", 0),
        )

    def _build_judge_output_format(self) -> str:
        """Build output format block from system template (contract guaranteed)."""
        return self._load_system_template("judge_output.md")

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse judge response."""
        result = extract_json_from_response(response)
        if result is not None:
            return result

        # Fallback: extract key information from text
        self.logger.warning("[Judge] Failed to parse JSON from response")
        should_continue = "continue" in response.lower() or "true" in response.lower() or "継続" in response
        return {
            "should_continue": should_continue,
            "reason": response[:500],
            "progress_score": 0.5,
            "drift_detected": False,
            "recommendations": [],
            "next_iteration_focus": "JSON形式で出力されませんでした"
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
            drift_detected=drift_detected,
            last_execution_feedback=result
        )

        self.logger.info(f"[Judge] Should continue: {should_continue}, Reason: {reason[:100]}")

        if drift_detected:
            self.logger.warning(f"[Judge] Drift detected: {result.get('drift_description', 'N/A')}")

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
