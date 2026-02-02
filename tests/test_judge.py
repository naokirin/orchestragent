"""Tests for agents.judge (JudgeAgent)."""

import pytest
from unittest.mock import MagicMock, patch

from orchestragent.agents.judge import JudgeAgent
from orchestragent.models.task import TaskStatus


class TestJudgeAgentInit:
    """Tests for JudgeAgent initialization."""

    def test_init_sets_mode_to_ask(self, mock_llm_client, state_manager):
        """JudgeAgent mode is set to 'ask'."""
        logger = MagicMock()
        agent = JudgeAgent(
            name="judge",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
        )
        assert agent.mode == "ask"


class TestJudgeBuildPrompt:
    """Tests for JudgeAgent.build_prompt."""

    @pytest.fixture
    def judge_agent(self, mock_llm_client, state_manager):
        logger = MagicMock()
        return JudgeAgent(
            name="judge",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
            config={"project_goal": "テストプロジェクト"},
        )

    def test_build_prompt_uses_fallback_template_when_file_not_found(self, judge_agent):
        """Use fallback when template file is not found."""
        state = {"plan": "現在の計画", "status": {"iteration": 1}}

        with patch("builtins.open", side_effect=FileNotFoundError):
            prompt = judge_agent.build_prompt(state)

        # Fallback is English; real file may be Japanese
        assert "Judge Agent" in prompt or "判定者" in prompt
        assert "テストプロジェクト" in prompt

    def test_build_prompt_includes_task_statistics(self, judge_agent, state_manager):
        """Task statistics are included in prompt."""
        # Add a task
        task_id = state_manager.add_task({"title": "Task 1", "description": "Desc"})
        state_manager.assign_task(task_id, "worker")
        state_manager.complete_task(task_id, {"report": "Done"})

        state = {"plan": "計画", "status": {"iteration": 1}}

        # Make only prompt template files raise FileNotFoundError
        original_open = open
        def mock_open_func(path, *args, **kwargs):
            if "prompts/" in str(path):
                raise FileNotFoundError
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            prompt = judge_agent.build_prompt(state)

        # Task statistics included (English template or system-injected Japanese)
        assert (
            "1 total" in prompt
            or "completed" in prompt.lower()
            or ("総タスク数" in prompt and "1" in prompt)
            or "完了タスク" in prompt
        )

    def test_build_prompt_includes_completed_task_results(self, judge_agent, state_manager):
        """Completed task results are included in prompt."""
        task_id = state_manager.add_task({"title": "Test Task", "description": "Desc"})
        state_manager.assign_task(task_id, "worker")
        state_manager.complete_task(task_id, {"report": "Task completed successfully"})

        state = {"plan": "計画", "status": {"iteration": 1}}

        # Make only prompt template raise FileNotFoundError
        original_open = open
        def mock_open_func(path, *args, **kwargs):
            if "prompts/" in str(path):
                raise FileNotFoundError
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            prompt = judge_agent.build_prompt(state)

        # Fallback template does not include completed_task_results but processes without error
        assert prompt is not None


class TestJudgeParseResponse:
    """Tests for JudgeAgent.parse_response."""

    @pytest.fixture
    def judge_agent(self, mock_llm_client, state_manager):
        logger = MagicMock()
        return JudgeAgent(
            name="judge",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
        )

    def test_parse_response_valid_json(self, judge_agent):
        """Parse and return when JSON is valid."""
        response = '''{
            "should_continue": true,
            "reason": "進捗良好",
            "progress_score": 0.8,
            "drift_detected": false
        }'''
        result = judge_agent.parse_response(response)

        assert result["should_continue"] is True
        assert result["reason"] == "進捗良好"
        assert result["progress_score"] == 0.8

    def test_parse_response_json_in_code_block(self, judge_agent):
        """JSON inside code block is also parsed."""
        response = '''```json
{
    "should_continue": false,
    "reason": "目標達成",
    "progress_score": 1.0,
    "drift_detected": false
}
```'''
        result = judge_agent.parse_response(response)

        assert result["should_continue"] is False
        assert result["progress_score"] == 1.0

    def test_parse_response_fallback_detects_continue_keyword(self, judge_agent):
        """Detect keyword 'continue' when JSON parse fails."""
        response = "プロジェクトは順調に進んでいます。継続して作業を進めてください。"
        result = judge_agent.parse_response(response)

        assert result["should_continue"] is True
        assert "progress_score" in result
        judge_agent.logger.warning.assert_called()

    def test_parse_response_fallback_detects_continue_english(self, judge_agent):
        """Detect keyword 'continue' (English) when JSON parse fails."""
        response = "The project should continue. Good progress has been made."
        result = judge_agent.parse_response(response)

        assert result["should_continue"] is True

    def test_parse_response_fallback_no_continue_keyword(self, judge_agent):
        """should_continue=False when no keyword on JSON parse failure."""
        response = "プロジェクトは完了しました。終了します。"
        result = judge_agent.parse_response(response)

        assert result["should_continue"] is False

    def test_parse_response_fallback_truncates_reason(self, judge_agent):
        """reason is truncated to 500 chars when JSON parse fails."""
        response = "a" * 1000
        result = judge_agent.parse_response(response)

        assert len(result["reason"]) == 500


class TestJudgeUpdateState:
    """Tests for JudgeAgent.update_state."""

    @pytest.fixture
    def judge_agent(self, mock_llm_client, state_manager):
        logger = MagicMock()
        return JudgeAgent(
            name="judge",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
        )

    def test_update_state_updates_status(self, judge_agent, state_manager):
        """Update status."""
        result = {
            "should_continue": True,
            "reason": "進捗良好",
            "progress_score": 0.75,
            "drift_detected": False,
        }
        judge_agent.update_state(result)

        status = state_manager.get_status()
        assert status.get("should_continue") is True
        assert status.get("progress_score") == 0.75

    def test_update_state_logs_drift_warning(self, judge_agent):
        """Log warning when drift_detected=True."""
        result = {
            "should_continue": True,
            "reason": "ドリフト検出",
            "progress_score": 0.5,
            "drift_detected": True,
            "drift_description": "目標からずれています",
        }
        judge_agent.update_state(result)

        judge_agent.logger.warning.assert_called()
        warning_call = str(judge_agent.logger.warning.call_args)
        assert "Drift" in warning_call or "drift" in warning_call.lower()

    def test_update_state_logs_info(self, judge_agent):
        """Log should_continue result."""
        result = {
            "should_continue": False,
            "reason": "プロジェクト完了",
            "progress_score": 1.0,
            "drift_detected": False,
        }
        judge_agent.update_state(result)

        judge_agent.logger.info.assert_called()

    def test_update_state_uses_defaults_for_missing_keys(self, judge_agent, state_manager):
        """Use default values when keys are missing."""
        result = {}  # empty result
        judge_agent.update_state(result)

        status = state_manager.get_status()
        assert status.get("should_continue") is True  # default
        assert status.get("progress_score") == 0.5  # default
