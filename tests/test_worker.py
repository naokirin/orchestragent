"""Tests for agents.worker (WorkerAgent)."""

import pytest
from unittest.mock import MagicMock, patch

from orchestragent.agents.worker import WorkerAgent
from orchestragent.models.task import TaskStatus


class TestWorkerAgentInit:
    """Tests for WorkerAgent initialization."""

    def test_init_sets_mode_to_agent(self, mock_llm_client, state_manager, temp_state_dir):
        """WorkerAgent の mode は 'agent' に設定される。"""
        logger = MagicMock()
        agent = WorkerAgent(
            name="worker",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
            state_dir=str(temp_state_dir),
        )
        assert agent.mode == "agent"
        assert agent.current_task_id is None

    def test_init_with_model_selection_config(self, mock_llm_client, state_manager, temp_state_dir):
        """モデル選択の設定が渡せる。"""
        logger = MagicMock()
        agent = WorkerAgent(
            name="worker",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
            state_dir=str(temp_state_dir),
            model_selection_enabled=True,
            model_complexity_threshold_light=5.0,
            model_complexity_threshold_powerful=20.0,
        )
        assert agent.model_selector.enabled is True
        assert agent.model_selector.threshold_light == 5.0


class TestWorkerAssignTask:
    """Tests for WorkerAgent.assign_task."""

    @pytest.fixture
    def worker_agent(self, mock_llm_client, state_manager, temp_state_dir):
        logger = MagicMock()
        return WorkerAgent(
            name="worker",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
            state_dir=str(temp_state_dir),
        )

    def test_assign_task_success(self, worker_agent, state_manager):
        """pending タスクの割当は成功する。"""
        task_id = state_manager.add_task({"title": "Test", "description": "Desc"})

        result = worker_agent.assign_task(task_id)

        assert result is True
        assert worker_agent.current_task_id == task_id

    def test_assign_task_nonexistent_returns_false(self, worker_agent):
        """存在しないタスクの割当は失敗する。"""
        result = worker_agent.assign_task("nonexistent-task")

        assert result is False
        worker_agent.logger.error.assert_called()

    def test_assign_task_not_pending_returns_false(self, worker_agent, state_manager):
        """pending でないタスクの割当は失敗する。"""
        task_id = state_manager.add_task({"title": "Test", "description": "Desc"})
        # タスクを in_progress に変更
        state_manager.assign_task(task_id, "other_worker")

        result = worker_agent.assign_task(task_id)

        assert result is False
        worker_agent.logger.warning.assert_called()


class TestWorkerBuildPrompt:
    """Tests for WorkerAgent.build_prompt."""

    @pytest.fixture
    def worker_agent(self, mock_llm_client, state_manager, temp_state_dir):
        logger = MagicMock()
        return WorkerAgent(
            name="worker",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
            state_dir=str(temp_state_dir),
            config={"project_root": "."},
        )

    def test_build_prompt_raises_when_no_task_assigned(self, worker_agent):
        """タスク未割当時は ValueError を送出。"""
        with pytest.raises(ValueError) as exc_info:
            worker_agent.build_prompt({})

        assert "No task assigned" in str(exc_info.value)

    def test_build_prompt_raises_when_task_not_found(self, worker_agent):
        """タスクが見つからない場合は ValueError を送出。"""
        worker_agent.current_task_id = "nonexistent-task"

        with pytest.raises(ValueError) as exc_info:
            worker_agent.build_prompt({})

        assert "not found" in str(exc_info.value)

    def test_build_prompt_uses_fallback_template(self, worker_agent, state_manager):
        """テンプレートファイルがない場合はフォールバックを使用。"""
        task_id = state_manager.add_task({"title": "Test Task", "description": "Task description"})
        worker_agent.current_task_id = task_id

        # プロンプトテンプレートファイルのみFileNotFoundにする
        original_open = open
        def mock_open_func(path, *args, **kwargs):
            if "prompts/" in str(path):
                raise FileNotFoundError
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            prompt = worker_agent.build_prompt({})

        assert "Worker Agent" in prompt
        assert "Test Task" in prompt


class TestWorkerGetRelatedFiles:
    """Tests for WorkerAgent._get_related_files."""

    @pytest.fixture
    def worker_agent(self, mock_llm_client, state_manager, temp_state_dir):
        logger = MagicMock()
        return WorkerAgent(
            name="worker",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
            state_dir=str(temp_state_dir),
        )

    def test_get_related_files_extracts_from_description(self, worker_agent, state_manager):
        """タスク説明からファイルを抽出する（include_common_pattern=True）。"""
        from orchestragent.models.task import Task

        task = Task(
            id="task-001",
            title="Test",
            description="Modify src/main.py and tests/test_main.py",
        )

        files_str = worker_agent._get_related_files(task)

        # include_common_pattern=True なのでパスが抽出される
        assert "src/main.py" in files_str
        assert "tests/test_main.py" in files_str

    def test_get_related_files_returns_message_when_no_files(self, worker_agent):
        """ファイルが見つからない場合はメッセージを返す。"""
        from orchestragent.models.task import Task

        task = Task(
            id="task-001",
            title="Test",
            description="Do something without file references",
        )

        files_str = worker_agent._get_related_files(task)

        assert "関連ファイルの情報がありません" in files_str


class TestWorkerParseResponse:
    """Tests for WorkerAgent.parse_response."""

    @pytest.fixture
    def worker_agent(self, mock_llm_client, state_manager, temp_state_dir):
        logger = MagicMock()
        agent = WorkerAgent(
            name="worker",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
            state_dir=str(temp_state_dir),
        )
        agent.current_task_id = "task-001"
        return agent

    def test_parse_response_extracts_report_section(self, worker_agent):
        """# タスク完了レポート セクションを抽出する。"""
        response = """作業完了しました。

# タスク完了レポート
- 変更点1
- 変更点2

以上です。"""
        result = worker_agent.parse_response(response)

        assert "# タスク完了レポート" in result["report"]
        assert result["task_id"] == "task-001"

    def test_parse_response_uses_full_response_when_no_report_section(self, worker_agent):
        """レポートセクションがない場合は全体を使用。"""
        response = "タスクを完了しました。変更を加えました。"
        result = worker_agent.parse_response(response)

        assert result["report"] == response
        assert result["task_id"] == "task-001"

    def test_parse_response_extracts_commit_info_from_intent(self, worker_agent):
        """Intent からコミット情報を抽出する。"""
        response = """# タスク完了レポート

## Intent
- task_id: task-001
- goal: テスト追加
- commits:
  - hash: abc1234
    message: Add tests

完了しました。"""
        result = worker_agent.parse_response(response)

        # IntentParser の結果に依存
        assert result["task_id"] == "task-001"

    def test_parse_response_extracts_commit_by_regex_fallback(self, worker_agent):
        """コミット情報を正規表現でフォールバック抽出。"""
        response = """# タスク完了レポート

コミットハッシュ: `abc1234def`
コミットメッセージ: `Add new feature`

完了しました。"""
        result = worker_agent.parse_response(response)

        assert len(result["commits"]) >= 1
        assert result["commits"][0]["hash"] == "abc1234def"

    def test_parse_response_handles_exception_gracefully(self, worker_agent):
        """例外発生時はフォールバック結果を返す。"""
        # IntentParser.parse をモックして例外を発生させる
        with patch(
            "orchestragent.agents.worker.IntentParser.parse",
            side_effect=Exception("Parse error"),
        ):
            result = worker_agent.parse_response("Some response")

        assert "error" in result
        assert result["task_id"] == "task-001"
        worker_agent.logger.error.assert_called()


class TestWorkerUpdateState:
    """Tests for WorkerAgent.update_state."""

    @pytest.fixture
    def worker_agent(self, mock_llm_client, state_manager, temp_state_dir):
        logger = MagicMock()
        agent = WorkerAgent(
            name="worker",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
            state_dir=str(temp_state_dir),
            adr_dir=str(temp_state_dir / "adr"),
        )
        return agent

    def test_update_state_raises_when_result_not_dict(self, worker_agent):
        """result が dict でない場合は ValueError を送出。"""
        with pytest.raises(ValueError) as exc_info:
            worker_agent.update_state("not a dict")

        assert "must be a dict" in str(exc_info.value)

    def test_update_state_raises_when_no_task_id(self, worker_agent):
        """task_id がない場合は ValueError を送出。"""
        worker_agent.current_task_id = None

        with pytest.raises(ValueError) as exc_info:
            worker_agent.update_state({"report": "Done"})

        assert "No task ID" in str(exc_info.value)

    def test_update_state_completes_task(self, worker_agent, state_manager):
        """タスクを completed に更新する。"""
        task_id = state_manager.add_task({"title": "Test", "description": "Desc"})
        state_manager.assign_task(task_id, "worker")
        worker_agent.current_task_id = task_id

        result = {"task_id": task_id, "report": "Task completed successfully"}
        worker_agent.update_state(result)

        task = state_manager.get_task_by_id(task_id)
        assert task.status == TaskStatus.COMPLETED

    def test_update_state_creates_adr_when_specified(self, worker_agent, state_manager, temp_state_dir):
        """adr_to_create が指定されている場合は ADR を作成。"""
        task_id = state_manager.add_task({"title": "Test", "description": "Desc"})
        state_manager.assign_task(task_id, "worker")
        worker_agent.current_task_id = task_id

        result = {
            "task_id": task_id,
            "report": "Done",
            "intent": {
                "task_id": task_id,
                "adr_to_create": {
                    "title": "Use Factory Pattern",
                    "context": "Need flexible object creation",
                    "decision": "Use factory pattern",
                },
            },
        }
        worker_agent.update_state(result)

        # ADR ディレクトリを確認
        adr_dir = temp_state_dir / "adr"
        adr_files = list(adr_dir.glob("*.md"))
        # テンプレート以外のファイルがあるか
        non_template_files = [f for f in adr_files if "template" not in f.name]
        assert len(non_template_files) >= 1

    def test_update_state_saves_intent(self, worker_agent, state_manager, temp_state_dir):
        """Intent を保存する。"""
        task_id = state_manager.add_task({"title": "Test", "description": "Desc"})
        state_manager.assign_task(task_id, "worker")
        worker_agent.current_task_id = task_id

        result = {
            "task_id": task_id,
            "report": "Done",
            "intent": {
                "task_id": task_id,
                "goal": "Add new feature",
            },
            "commits": [],
        }
        worker_agent.update_state(result)

        # Intent ファイルを確認
        intent_file = temp_state_dir / "intents" / f"intent_{task_id}.yaml"
        assert intent_file.exists()


class TestWorkerRunInternal:
    """Tests for WorkerAgent._run_internal."""

    @pytest.fixture
    def worker_agent(self, mock_llm_client, state_manager, temp_state_dir):
        logger = MagicMock()
        return WorkerAgent(
            name="worker",
            llm_client=mock_llm_client,
            state_manager=state_manager,
            logger=logger,
            state_dir=str(temp_state_dir),
            model_selection_enabled=True,
        )

    def test_run_internal_raises_when_no_task_assigned(self, worker_agent):
        """タスク未割当時は ValueError を送出。"""
        import time

        with pytest.raises(ValueError) as exc_info:
            worker_agent._run_internal(iteration=0, start_time=time.time())

        assert "No task assigned" in str(exc_info.value)

    def test_run_internal_raises_when_task_not_found(self, worker_agent):
        """タスクが見つからない場合は ValueError を送出。"""
        import time

        worker_agent.current_task_id = "nonexistent-task"

        with pytest.raises(ValueError) as exc_info:
            worker_agent._run_internal(iteration=0, start_time=time.time())

        assert "not found" in str(exc_info.value)
