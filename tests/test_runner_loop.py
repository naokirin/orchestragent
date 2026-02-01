"""Tests for runner loop (run_main_loop 分割後の各関数)."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from orchestragent.runner.loop import (
    LoopContext,
    AgentContext,
    initialize_session,
    setup_agents,
    run_plan_phase,
    run_work_phase,
    run_judge_phase,
)
from orchestragent.core.exceptions import AgentError


# =============================================================================
# Fixtures: LoopContext / AgentContext (mock)
# =============================================================================


@pytest.fixture
def loop_context(state_manager, mock_llm_client, temp_state_dir):
    """LoopContext を構築（StateManager / Logger / LLM / FileLock / TaskScheduler は実体）。"""
    from orchestragent.core.logger import AgentLogger
    from orchestragent.state.file_lock import FileLockManager
    from orchestragent.scheduler.task_scheduler import TaskScheduler

    log_dir = temp_state_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    logger = AgentLogger(log_dir=str(log_dir), log_level="DEBUG", sync=False)
    file_lock_manager = FileLockManager(lock_dir=str(temp_state_dir / "locks"))
    task_scheduler = TaskScheduler(state_manager, file_lock_manager)

    return LoopContext(
        state_manager=state_manager,
        logger=logger,
        llm_client=mock_llm_client,
        file_lock_manager=file_lock_manager,
        task_scheduler=task_scheduler,
    )


@pytest.fixture
def mock_agent_context():
    """AgentContext をモックで構築（run_plan_phase / run_work_phase / run_judge_phase 用）。"""
    planner = MagicMock()
    worker = MagicMock()
    judge = MagicMock()
    plan_judge = MagicMock()
    worker_config = {"mode": "agent", "model": ""}
    return AgentContext(
        planner=planner,
        worker=worker,
        judge=judge,
        plan_judge=plan_judge,
        worker_config=worker_config,
    )


# =============================================================================
# initialize_session
# =============================================================================


class TestInitializeSession:
    """initialize_session() のテスト（startup をモック）。"""

    @patch("orchestragent.runner.loop.check_cursor_cli", return_value=True)
    @patch("orchestragent.runner.loop.check_cursor_auth", return_value=True)
    @patch("orchestragent.runner.loop.print_configuration")
    @patch("orchestragent.runner.loop.is_running_in_container", return_value=True)
    @patch("orchestragent.runner.loop.LLMClientFactory.create")
    @patch("orchestragent.runner.loop.config")
    def test_returns_loop_context(
        self,
        mock_config,
        mock_llm_factory,
        _mock_container,
        _mock_print,
        _mock_auth,
        _mock_cli,
        temp_state_dir,
        mock_llm_client,
    ):
        """startup をすべて成功させたとき、LoopContext が返る。"""
        mock_config.STATE_DIR = str(temp_state_dir)
        mock_config.LOG_DIR = str(temp_state_dir / "logs")
        mock_config.LOG_LEVEL = "DEBUG"
        mock_config.LOG_FSYNC = False
        mock_config.WORKING_DIR = temp_state_dir
        mock_config.LLM_BACKEND = "cursor_cli"
        mock_config.LLM_OUTPUT_FORMAT = "json"
        mock_llm_factory.return_value = mock_llm_client

        ctx = initialize_session()

        assert isinstance(ctx, LoopContext)
        assert ctx.state_manager is not None
        assert ctx.logger is not None
        assert ctx.llm_client is mock_llm_client
        assert ctx.file_lock_manager is not None
        assert ctx.task_scheduler is not None


# =============================================================================
# setup_agents
# =============================================================================


class TestSetupAgents:
    """setup_agents() のテスト。"""

    @patch("orchestragent.runner.loop.config")
    def test_returns_agent_context(self, mock_config, loop_context):
        """LoopContext を渡すと AgentContext が返る。"""
        mock_config.AGENT_CONFIG = {
            "project_goal": "test",
            "prompt_template": "prompts/planner.md",
            "mode": "plan",
        }
        mock_config.PLANNER_MODEL = ""
        mock_config.WORKER_MODEL = ""
        mock_config.JUDGE_MODEL = ""

        agents = setup_agents(loop_context)

        assert isinstance(agents, AgentContext)
        assert agents.planner is not None
        assert agents.worker is not None
        assert agents.judge is not None
        assert agents.plan_judge is not None
        assert "mode" in agents.worker_config


# =============================================================================
# run_plan_phase
# =============================================================================


class TestRunPlanPhase:
    """run_plan_phase() のテスト。"""

    def test_returns_true_when_plan_accepted(
        self, loop_context, mock_agent_context
    ):
        """Plan_Judge が accept を返すと True。"""
        mock_agent_context.planner.run.return_value = None
        mock_agent_context.plan_judge.run.return_value = {"decision": "accept"}

        result = run_plan_phase(loop_context, mock_agent_context, iteration=1)

        assert result is True
        mock_agent_context.planner.run.assert_called_once()
        mock_agent_context.plan_judge.run.assert_called_once()

    def test_returns_false_when_planner_raises(
        self, loop_context, mock_agent_context
    ):
        """Planner が AgentError を出すと False。"""
        mock_agent_context.planner.run.side_effect = AgentError("planner error")

        result = run_plan_phase(loop_context, mock_agent_context, iteration=1)

        assert result is False
        mock_agent_context.planner.run.assert_called_once()
        mock_agent_context.plan_judge.run.assert_not_called()

    def test_returns_false_when_plan_judge_returns_revise_after_max_attempts(
        self, loop_context, mock_agent_context
    ):
        """Plan_Judge が常に revise を返すと最大回数で False。"""
        mock_agent_context.planner.run.return_value = None
        mock_agent_context.plan_judge.run.return_value = {"decision": "revise"}

        with patch("orchestragent.runner.loop.config") as mock_config:
            mock_config.MAX_PLAN_REVISIONS = 2
            mock_config.MAX_RETRIES = 1
            result = run_plan_phase(
                loop_context, mock_agent_context, iteration=1
            )

        assert result is False


# =============================================================================
# run_work_phase
# =============================================================================


class TestRunWorkPhase:
    """run_work_phase() のテスト。"""

    @patch("orchestragent.runner.loop.config")
    def test_no_pending_tasks_sequential(
        self, mock_config, loop_context, mock_agent_context
    ):
        """並列無効・保留タスクなしのときは Worker は実行されない。"""
        mock_config.ENABLE_PARALLEL_EXECUTION = False
        mock_config.WAIT_TIME_SECONDS = 0
        # state_manager は実体なので get_pending_tasks() は空の状態で [] を返す

        run_work_phase(loop_context, mock_agent_context, iteration=1)

        mock_agent_context.worker.assign_task.assert_not_called()
        mock_agent_context.worker.run.assert_not_called()


# =============================================================================
# run_judge_phase
# =============================================================================


class TestRunJudgePhase:
    """run_judge_phase() のテスト。"""

    def test_calls_judge_run(
        self, loop_context, mock_agent_context
    ):
        """Judge.run が 1 回呼ばれる。"""
        run_judge_phase(loop_context, mock_agent_context, iteration=1)

        mock_agent_context.judge.run.assert_called_once()
        call_kw = mock_agent_context.judge.run.call_args[1]
        assert call_kw["iteration"] == 1
