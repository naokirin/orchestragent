"""Tests for runner loop (run_main_loop 分割後の各関数)."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from orchestragent.runner.loop import (
    LoopContext,
    AgentContext,
    RunnerConfig,
    initialize_session,
    setup_agents,
    run_plan_phase,
    run_work_phase,
    run_judge_phase,
)
from orchestragent.core.exceptions import AgentError


def _default_runner_config(temp_state_dir: Path) -> RunnerConfig:
    """テスト用の最小 RunnerConfig。"""
    log_dir = temp_state_dir / "logs"
    return RunnerConfig(
        llm_backend="cursor_cli",
        working_dir=str(temp_state_dir),
        llm_output_format="text",
        state_dir=str(temp_state_dir),
        log_dir=str(log_dir),
        log_level="DEBUG",
        log_fsync=False,
        agent_config={
            "project_goal": "test",
            "prompt_template": "prompts/planner.md",
            "mode": "plan",
        },
        planner_model="",
        worker_model="",
        judge_model="",
        max_plan_revisions=3,
        max_retries=1,
        enable_parallel_execution=False,
        max_parallel_workers=1,
        wait_time_seconds=0,
        max_iterations=10,
        adr_dir="docs/adr",
    )


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
    runner_config = _default_runner_config(temp_state_dir)

    return LoopContext(
        state_manager=state_manager,
        logger=logger,
        llm_client=mock_llm_client,
        file_lock_manager=file_lock_manager,
        task_scheduler=task_scheduler,
        runner_config=runner_config,
    )


@pytest.fixture
def mock_agent_context(loop_context):
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
        runner_config=loop_context.runner_config,
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
    def test_returns_loop_context(
        self,
        mock_llm_factory,
        _mock_container,
        _mock_print,
        _mock_auth,
        _mock_cli,
        temp_state_dir,
        mock_llm_client,
    ):
        """startup をすべて成功させたとき、LoopContext が返る（config は DI で渡す）。"""
        mock_llm_factory.return_value = mock_llm_client
        cfg = RunnerConfig(
            llm_backend="cursor_cli",
            working_dir=str(temp_state_dir),
            llm_output_format="json",
            state_dir=str(temp_state_dir),
            log_dir=str(temp_state_dir / "logs"),
            log_level="DEBUG",
            log_fsync=False,
        )

        ctx = initialize_session(cfg=cfg)

        assert isinstance(ctx, LoopContext)
        assert ctx.state_manager is not None
        assert ctx.logger is not None
        assert ctx.llm_client is mock_llm_client
        assert ctx.file_lock_manager is not None
        assert ctx.task_scheduler is not None
        assert ctx.runner_config is cfg


# =============================================================================
# setup_agents
# =============================================================================


class TestSetupAgents:
    """setup_agents() のテスト。"""

    def test_returns_agent_context(self, loop_context):
        """LoopContext を渡すと AgentContext が返る（設定は ctx.runner_config から取得）。"""
        agents = setup_agents(loop_context)

        assert isinstance(agents, AgentContext)
        assert agents.planner is not None
        assert agents.worker is not None
        assert agents.judge is not None
        assert agents.plan_judge is not None
        assert "mode" in agents.worker_config
        assert agents.runner_config is loop_context.runner_config


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
        self, loop_context, mock_agent_context, temp_state_dir
    ):
        """Plan_Judge が常に revise を返すと最大回数で False。"""
        mock_agent_context.planner.run.return_value = None
        mock_agent_context.plan_judge.run.return_value = {"decision": "revise"}

        cfg = RunnerConfig(
            llm_backend="cursor_cli",
            working_dir=str(temp_state_dir),
            llm_output_format="text",
            state_dir=str(temp_state_dir),
            log_dir=str(temp_state_dir / "logs"),
            log_level="DEBUG",
            log_fsync=False,
            max_plan_revisions=2,
            max_retries=1,
        )
        ctx = LoopContext(
            state_manager=loop_context.state_manager,
            logger=loop_context.logger,
            llm_client=loop_context.llm_client,
            file_lock_manager=loop_context.file_lock_manager,
            task_scheduler=loop_context.task_scheduler,
            runner_config=cfg,
        )
        mock_agent_context.runner_config = cfg
        result = run_plan_phase(ctx, mock_agent_context, iteration=1)

        assert result is False


# =============================================================================
# run_work_phase
# =============================================================================


class TestRunWorkPhase:
    """run_work_phase() のテスト。"""

    def test_no_pending_tasks_sequential(
        self, loop_context, mock_agent_context
    ):
        """並列無効・保留タスクなしのときは Worker は実行されない。"""
        # loop_context.runner_config は _default_runner_config で enable_parallel_execution=False
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
