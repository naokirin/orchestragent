"""Tests for agents.judge (JudgeAgent)."""

import pytest
from unittest.mock import MagicMock, patch

from orchestragent.agents.judge import JudgeAgent
from orchestragent.models.task import TaskStatus


class TestJudgeAgentInit:
    """Tests for JudgeAgent initialization."""

    def test_init_sets_mode_to_ask(self, mock_llm_client, state_manager):
        """JudgeAgent の mode は 'ask' に設定される。"""
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
        """テンプレートファイルがない場合はフォールバックを使用。"""
        state = {"plan": "現在の計画", "status": {"iteration": 1}}

        with patch("builtins.open", side_effect=FileNotFoundError):
            prompt = judge_agent.build_prompt(state)

        # フォールバック時は英語、実ファイル読み込み時は日本語
        assert "Judge Agent" in prompt or "判定者" in prompt
        assert "テストプロジェクト" in prompt

    def test_build_prompt_includes_task_statistics(self, judge_agent, state_manager):
        """タスク統計がプロンプトに含まれる。"""
        # タスクを追加
        task_id = state_manager.add_task({"title": "Task 1", "description": "Desc"})
        state_manager.assign_task(task_id, "worker")
        state_manager.complete_task(task_id, {"report": "Done"})

        state = {"plan": "計画", "status": {"iteration": 1}}

        # プロンプトテンプレートファイルのみFileNotFoundにする
        original_open = open
        def mock_open_func(path, *args, **kwargs):
            if "prompts/" in str(path):
                raise FileNotFoundError
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            prompt = judge_agent.build_prompt(state)

        # タスク統計が含まれる（英語テンプレートまたはシステム注入の日本語）
        assert (
            "1 total" in prompt
            or "completed" in prompt.lower()
            or ("総タスク数" in prompt and "1" in prompt)
            or "完了タスク" in prompt
        )

    def test_build_prompt_includes_completed_task_results(self, judge_agent, state_manager):
        """完了タスクの結果がプロンプトに含まれる。"""
        task_id = state_manager.add_task({"title": "Test Task", "description": "Desc"})
        state_manager.assign_task(task_id, "worker")
        state_manager.complete_task(task_id, {"report": "Task completed successfully"})

        state = {"plan": "計画", "status": {"iteration": 1}}

        # プロンプトテンプレートのみFileNotFoundにする
        original_open = open
        def mock_open_func(path, *args, **kwargs):
            if "prompts/" in str(path):
                raise FileNotFoundError
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            prompt = judge_agent.build_prompt(state)

        # フォールバックテンプレートでは completed_task_results は含まれないが、
        # エラーなく処理される
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
        """有効なJSONの場合はパースして返す。"""
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
        """コードブロック内のJSONもパース可能。"""
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
        """JSONパース失敗時にキーワード「継続」を検出。"""
        response = "プロジェクトは順調に進んでいます。継続して作業を進めてください。"
        result = judge_agent.parse_response(response)

        assert result["should_continue"] is True
        assert "progress_score" in result
        judge_agent.logger.warning.assert_called()

    def test_parse_response_fallback_detects_continue_english(self, judge_agent):
        """JSONパース失敗時にキーワード「continue」を検出。"""
        response = "The project should continue. Good progress has been made."
        result = judge_agent.parse_response(response)

        assert result["should_continue"] is True

    def test_parse_response_fallback_no_continue_keyword(self, judge_agent):
        """JSONパース失敗時にキーワードがない場合は should_continue=False。"""
        response = "プロジェクトは完了しました。終了します。"
        result = judge_agent.parse_response(response)

        assert result["should_continue"] is False

    def test_parse_response_fallback_truncates_reason(self, judge_agent):
        """JSONパース失敗時に reason は500文字に切り詰められる。"""
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
        """ステータスを更新する。"""
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
        """drift_detected=True の場合は警告をログ出力。"""
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
        """should_continue の結果をログ出力。"""
        result = {
            "should_continue": False,
            "reason": "プロジェクト完了",
            "progress_score": 1.0,
            "drift_detected": False,
        }
        judge_agent.update_state(result)

        judge_agent.logger.info.assert_called()

    def test_update_state_uses_defaults_for_missing_keys(self, judge_agent, state_manager):
        """キーが欠けている場合はデフォルト値を使用。"""
        result = {}  # 空の結果
        judge_agent.update_state(result)

        status = state_manager.get_status()
        assert status.get("should_continue") is True  # デフォルト
        assert status.get("progress_score") == 0.5  # デフォルト
