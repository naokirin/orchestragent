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
        """PlannerAgent mode is set to 'plan'."""
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
        """Use fallback template when template file is not found."""
        state = {"plan": "", "tasks": {"tasks": []}, "status": {}}

        with patch("builtins.open", side_effect=FileNotFoundError):
            prompt = planner_agent.build_prompt(state)

        assert "テスト目標" in prompt
        # Fallback is English; real file may be Japanese
        assert "Planner Agent" in prompt or "プランナー" in prompt

    def test_build_prompt_formats_existing_tasks(self, planner_agent, state_manager, temp_state_dir):
        """Existing tasks are formatted when present."""
        # Add a task
        task_id = state_manager.add_task({"title": "Task 1", "description": "Desc 1"})

        state = {
            "plan": "現在の計画",
            "tasks": {"tasks": [{"id": task_id, "title": "Task 1"}]},
            "status": {},
        }

        # Make only prompt template files raise FileNotFoundError
        original_open = open
        def mock_open_func(path, *args, **kwargs):
            if "prompts/" in str(path):
                raise FileNotFoundError
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            prompt = planner_agent.build_prompt(state)

        assert "Task 1" in prompt

    def test_build_prompt_shows_no_tasks_message_when_empty(self, planner_agent):
        """Show 'None' when there are no tasks."""
        state = {"plan": "", "tasks": {"tasks": []}, "status": {}}

        with patch("builtins.open", side_effect=FileNotFoundError):
            prompt = planner_agent.build_prompt(state)

        assert "None" in prompt

    def test_build_prompt_with_plan_judge_feedback_no_error(self, planner_agent):
        """build_prompt does not error when last_plan_judge_feedback is present."""
        state = {
            "plan": "",
            "tasks": {"tasks": []},
            "status": {"last_plan_judge_feedback": {"score": 0.8, "feedback": "良い計画"}},
        }

        # Make only prompt template files raise FileNotFoundError
        original_open = open
        def mock_open_func(path, *args, **kwargs):
            if "prompts/" in str(path):
                raise FileNotFoundError
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            prompt = planner_agent.build_prompt(state)

        # No error when fallback template is used
        assert prompt is not None
        assert "Planner Agent" in prompt or "プランナー" in prompt

    def test_build_prompt_with_execution_feedback_no_error(self, planner_agent):
        """build_prompt does not error when last_execution_feedback (Judge result) is present."""
        state = {
            "plan": "",
            "tasks": {"tasks": []},
            "status": {
                "reason": "進捗良好",
                "progress_score": 0.7,
                "drift_detected": False,
            },
        }

        # Make only prompt template files raise FileNotFoundError
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
        """Return file list when there are 20 or fewer Python files."""
        # Create 5 Python files
        for i in range(5):
            (temp_dir / f"file{i}.py").touch()

        summary = planner_agent._get_codebase_summary()

        assert "Key files" in summary
        assert "file0.py" in summary

    def test_get_codebase_summary_many_files(self, planner_agent, temp_dir):
        """Return count message when there are more than 20 Python files."""
        # Create 25 Python files
        for i in range(25):
            (temp_dir / f"file{i}.py").touch()

        summary = planner_agent._get_codebase_summary()

        assert "Python files" in summary


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
        """Parse and return when JSON is valid."""
        response = '{"plan_update": "新しい計画", "new_tasks": []}'
        result = planner_agent.parse_response(response)

        assert result["plan_update"] == "新しい計画"
        assert result["new_tasks"] == []

    def test_parse_response_json_in_code_block(self, planner_agent):
        """JSON inside code block is also parsed."""
        response = '''```json
{"plan_update": "計画更新", "new_tasks": [{"title": "新タスク"}]}
```'''
        result = planner_agent.parse_response(response)

        assert result["plan_update"] == "計画更新"
        assert len(result["new_tasks"]) == 1

    def test_parse_response_invalid_json_returns_fallback(self, planner_agent):
        """Return fallback result when JSON parse fails."""
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
        """Save plan when plan_update is present."""
        result = {"plan_update": "新しい計画内容", "new_tasks": []}
        planner_agent.update_state(result)

        saved_plan = state_manager.get_plan()
        assert saved_plan == "新しい計画内容"

    def test_update_state_adds_new_tasks(self, planner_agent, state_manager):
        """Add tasks when new_tasks is present."""
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
        """Extract quoted file paths from task description."""
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
        """Extract file: prefix paths from task description."""
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
        """Do not extract when files are already specified."""
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
        """Existing tasks can be updated via updated_tasks."""
        # Add a task first
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
        """Log warning when updated_tasks entry has no id."""
        result = {
            "plan_update": "",
            "new_tasks": [],
            "updated_tasks": [{"title": "IDなし"}],  # no id
        }
        planner_agent.update_state(result)

        planner_agent.logger.warning.assert_called()

    def test_update_state_skips_update_with_empty_updates(self, planner_agent, state_manager):
        """Skip when updated_tasks entry has no fields other than id."""
        task_id = state_manager.add_task({"title": "元タイトル", "description": "元説明"})

        result = {
            "plan_update": "",
            "new_tasks": [],
            "updated_tasks": [{"id": task_id}],  # id only, no update fields
        }
        planner_agent.update_state(result)

        # Task is unchanged
        task = state_manager.get_task_by_id(task_id)
        assert task.title == "元タイトル"
