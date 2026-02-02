"""Tests for agents.planner (PlannerAgent)."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from orchestragent.agents.planner import PlannerAgent
from orchestragent.models.task import TaskStatus


class TestPlannerAgentInit:
    """Tests for PlannerAgent initialization."""

    def test_init_sets_mode_to_plan(self, mock_llm_client, state_manager):
        """PlannerAgent の mode は 'plan' に設定される。"""
        logger = MagicMock()
        agent = PlannerAgent(
            name="planner",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
        )
        assert agent.mode == "plan"


class TestPlannerBuildPrompt:
    """Tests for PlannerAgent.build_prompt."""

    @pytest.fixture
    def planner_agent(self, mock_llm_client, state_manager):
        logger = MagicMock()
        return PlannerAgent(
            name="planner",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
            config={"project_goal": "テスト目標", "project_root": "."},
        )

    def test_build_prompt_uses_fallback_template_when_file_not_found(self, planner_agent):
        """テンプレートファイルが存在しない場合はフォールバックテンプレートを使用。"""
        state = {"plan": "", "tasks": {"tasks": []}, "status": {}}

        with patch("builtins.open", side_effect=FileNotFoundError):
            prompt = planner_agent.build_prompt(state)

        assert "テスト目標" in prompt
        # フォールバック時は英語、実ファイル読み込み時は日本語
        assert "Planner Agent" in prompt or "プランナー" in prompt

    def test_build_prompt_formats_existing_tasks(self, planner_agent, state_manager, temp_state_dir):
        """既存タスクがある場合はフォーマットされる。"""
        # タスクを追加
        task_id = state_manager.add_task({"title": "Task 1", "description": "Desc 1"})

        state = {
            "plan": "現在の計画",
            "tasks": {"tasks": [{"id": task_id, "title": "Task 1"}]},
            "status": {},
        }

        # プロンプトテンプレートファイルのみFileNotFoundにする
        original_open = open
        def mock_open_func(path, *args, **kwargs):
            if "prompts/" in str(path):
                raise FileNotFoundError
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            prompt = planner_agent.build_prompt(state)

        assert "Task 1" in prompt

    def test_build_prompt_shows_no_tasks_message_when_empty(self, planner_agent):
        """タスクがない場合は「なし」と表示。"""
        state = {"plan": "", "tasks": {"tasks": []}, "status": {}}

        with patch("builtins.open", side_effect=FileNotFoundError):
            prompt = planner_agent.build_prompt(state)

        assert "なし" in prompt

    def test_build_prompt_with_plan_judge_feedback_no_error(self, planner_agent):
        """last_plan_judge_feedback があっても build_prompt がエラーにならない。"""
        state = {
            "plan": "",
            "tasks": {"tasks": []},
            "status": {"last_plan_judge_feedback": {"score": 0.8, "feedback": "良い計画"}},
        }

        # プロンプトテンプレートファイルのみFileNotFoundにする
        original_open = open
        def mock_open_func(path, *args, **kwargs):
            if "prompts/" in str(path):
                raise FileNotFoundError
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            prompt = planner_agent.build_prompt(state)

        # フォールバックテンプレートが使われてもエラーにならない
        assert prompt is not None
        assert "Planner Agent" in prompt or "プランナー" in prompt

    def test_build_prompt_with_execution_feedback_no_error(self, planner_agent):
        """last_execution_feedback (Judge結果) があっても build_prompt がエラーにならない。"""
        state = {
            "plan": "",
            "tasks": {"tasks": []},
            "status": {
                "reason": "進捗良好",
                "progress_score": 0.7,
                "drift_detected": False,
            },
        }

        # プロンプトテンプレートファイルのみFileNotFoundにする
        original_open = open
        def mock_open_func(path, *args, **kwargs):
            if "prompts/" in str(path):
                raise FileNotFoundError
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            prompt = planner_agent.build_prompt(state)

        assert prompt is not None


class TestPlannerGetCodebaseSummary:
    """Tests for PlannerAgent._get_codebase_summary."""

    @pytest.fixture
    def planner_agent(self, mock_llm_client, state_manager, temp_dir):
        logger = MagicMock()
        return PlannerAgent(
            name="planner",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
            config={"project_root": str(temp_dir)},
        )

    def test_get_codebase_summary_few_files(self, planner_agent, temp_dir):
        """Pythonファイルが20個以下の場合はファイルリストを返す。"""
        # 5個のPythonファイルを作成
        for i in range(5):
            (temp_dir / f"file{i}.py").touch()

        summary = planner_agent._get_codebase_summary()

        assert "主要なファイル" in summary
        assert "file0.py" in summary

    def test_get_codebase_summary_many_files(self, planner_agent, temp_dir):
        """Pythonファイルが20個を超える場合はカウントメッセージを返す。"""
        # 25個のPythonファイルを作成
        for i in range(25):
            (temp_dir / f"file{i}.py").touch()

        summary = planner_agent._get_codebase_summary()

        assert "個以上のPythonファイル" in summary


class TestPlannerParseResponse:
    """Tests for PlannerAgent.parse_response."""

    @pytest.fixture
    def planner_agent(self, mock_llm_client, state_manager):
        logger = MagicMock()
        return PlannerAgent(
            name="planner",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
        )

    def test_parse_response_valid_json(self, planner_agent):
        """有効なJSONの場合はパースして返す。"""
        response = '{"plan_update": "新しい計画", "new_tasks": []}'
        result = planner_agent.parse_response(response)

        assert result["plan_update"] == "新しい計画"
        assert result["new_tasks"] == []

    def test_parse_response_json_in_code_block(self, planner_agent):
        """コードブロック内のJSONもパース可能。"""
        response = '''```json
{"plan_update": "計画更新", "new_tasks": [{"title": "新タスク"}]}
```'''
        result = planner_agent.parse_response(response)

        assert result["plan_update"] == "計画更新"
        assert len(result["new_tasks"]) == 1

    def test_parse_response_invalid_json_returns_fallback(self, planner_agent):
        """JSONパース失敗時はフォールバック結果を返す。"""
        response = "これはJSONではありません。計画を更新しました。"
        result = planner_agent.parse_response(response)

        assert "plan_update" in result
        assert result["new_tasks"] == []
        assert "JSON形式で出力されませんでした" in result["reasoning"]
        planner_agent.logger.warning.assert_called()


class TestPlannerUpdateState:
    """Tests for PlannerAgent.update_state."""

    @pytest.fixture
    def planner_agent(self, mock_llm_client, state_manager):
        logger = MagicMock()
        return PlannerAgent(
            name="planner",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
        )

    def test_update_state_saves_plan(self, planner_agent, state_manager):
        """plan_update がある場合はプランを保存する。"""
        result = {"plan_update": "新しい計画内容", "new_tasks": []}
        planner_agent.update_state(result)

        saved_plan = state_manager.get_plan()
        assert saved_plan == "新しい計画内容"

    def test_update_state_adds_new_tasks(self, planner_agent, state_manager):
        """new_tasks がある場合はタスクを追加する。"""
        result = {
            "plan_update": "",
            "new_tasks": [
                {"title": "タスク1", "description": "説明1"},
                {"title": "タスク2", "description": "説明2"},
            ],
        }
        planner_agent.update_state(result)

        stats = state_manager.get_task_statistics()
        assert stats.total == 2

    def test_update_state_extracts_files_from_description_quoted(self, planner_agent, state_manager):
        """タスク説明からクオートされたファイルパスを抽出する。"""
        result = {
            "plan_update": "",
            "new_tasks": [
                {
                    "title": "ファイル修正",
                    "description": '`src/main.py` を修正してください',
                },
            ],
        }
        planner_agent.update_state(result)

        tasks = state_manager.get_all_tasks_from_files()
        assert len(tasks) == 1
        assert "src/main.py" in tasks[0].files

    def test_update_state_extracts_files_with_file_prefix(self, planner_agent, state_manager):
        """タスク説明から file: プレフィックス付きパスを抽出する。"""
        result = {
            "plan_update": "",
            "new_tasks": [
                {
                    "title": "設定修正",
                    "description": "file: config/settings.yml を更新",
                },
            ],
        }
        planner_agent.update_state(result)

        tasks = state_manager.get_all_tasks_from_files()
        assert len(tasks) == 1
        assert "config/settings.yml" in tasks[0].files

    def test_update_state_does_not_extract_if_files_provided(self, planner_agent, state_manager):
        """files が既に指定されている場合は抽出しない。"""
        result = {
            "plan_update": "",
            "new_tasks": [
                {
                    "title": "ファイル修正",
                    "description": '`src/main.py` を修正',
                    "files": ["other/file.py"],
                },
            ],
        }
        planner_agent.update_state(result)

        tasks = state_manager.get_all_tasks_from_files()
        assert len(tasks) == 1
        assert tasks[0].files == ["other/file.py"]
        assert "src/main.py" not in tasks[0].files

    def test_update_state_updates_existing_tasks(self, planner_agent, state_manager):
        """updated_tasks で既存タスクを更新できる。"""
        # 先にタスクを追加
        task_id = state_manager.add_task({"title": "元タイトル", "description": "元説明"})

        result = {
            "plan_update": "",
            "new_tasks": [],
            "updated_tasks": [{"id": task_id, "title": "更新後タイトル"}],
        }
        planner_agent.update_state(result)

        updated_task = state_manager.get_task_by_id(task_id)
        assert updated_task.title == "更新後タイトル"

    def test_update_state_logs_warning_for_invalid_update(self, planner_agent, state_manager):
        """updated_tasks に id がない場合は警告をログ出力。"""
        result = {
            "plan_update": "",
            "new_tasks": [],
            "updated_tasks": [{"title": "IDなし"}],  # id がない
        }
        planner_agent.update_state(result)

        planner_agent.logger.warning.assert_called()

    def test_update_state_skips_update_with_empty_updates(self, planner_agent, state_manager):
        """updated_tasks で id 以外のフィールドがない場合はスキップ。"""
        task_id = state_manager.add_task({"title": "元タイトル", "description": "元説明"})

        result = {
            "plan_update": "",
            "new_tasks": [],
            "updated_tasks": [{"id": task_id}],  # id のみ、更新フィールドなし
        }
        planner_agent.update_state(result)

        # タスクは変更されていない
        task = state_manager.get_task_by_id(task_id)
        assert task.title == "元タイトル"
