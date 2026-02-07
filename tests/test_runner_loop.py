"""Tests for runner loop (functions after run_main_loop split)."""

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
    run_plan_finalize_on_judge_completion,
)
from orchestragent.core.exceptions import AgentError


def _default_runner_config(temp_state_dir: Path) -> RunnerConfig:
    """Minimal RunnerConfig for tests."""
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
    """Build LoopContext (StateManager, Logger, LLM, FileLock, TaskScheduler are real)."""
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
    """Build AgentContext with mocks (for run_plan_phase / run_work_phase / run_judge_phase)."""
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
    """Tests for initialize_session() (startup mocked)."""

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
        """When startup succeeds, LoopContext is returned (config passed via DI)."""
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
    """Tests for setup_agents()."""

    def test_returns_agent_context(self, loop_context):
        """Passing LoopContext returns AgentContext (config from ctx.runner_config)."""
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
    """Tests for run_plan_phase()."""

    def test_returns_true_when_plan_accepted(
        self, loop_context, mock_agent_context
    ):
        """Returns True when Plan_Judge returns accept."""
        mock_agent_context.planner.run.return_value = None
        mock_agent_context.plan_judge.run.return_value = {"decision": "accept"}

        result = run_plan_phase(loop_context, mock_agent_context, iteration=1)

        assert result is True
        mock_agent_context.planner.run.assert_called_once()
        mock_agent_context.plan_judge.run.assert_called_once()

    def test_returns_false_when_planner_raises(
        self, loop_context, mock_agent_context
    ):
        """Returns False when Planner raises AgentError."""
        mock_agent_context.planner.run.side_effect = AgentError("planner error")

        result = run_plan_phase(loop_context, mock_agent_context, iteration=1)

        assert result is False
        mock_agent_context.planner.run.assert_called_once()
        mock_agent_context.plan_judge.run.assert_not_called()

    def test_returns_false_when_plan_judge_returns_revise_after_max_attempts(
        self, loop_context, mock_agent_context, temp_state_dir
    ):
        """Returns False after max attempts when Plan_Judge always returns revise."""
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
    """Tests for run_work_phase()."""

    def test_no_pending_tasks_sequential(
        self, loop_context, mock_agent_context
    ):
        """Worker is not run when parallel disabled and no pending tasks."""
        # loop_context.runner_config has enable_parallel_execution=False from _default_runner_config
        # state_manager is real so get_pending_tasks() returns [] (empty state)
        run_work_phase(loop_context, mock_agent_context, iteration=1)

        mock_agent_context.worker.assign_task.assert_not_called()
        mock_agent_context.worker.run.assert_not_called()


# =============================================================================
# run_judge_phase
# =============================================================================


class TestRunJudgePhase:
    """Tests for run_judge_phase()."""

    def test_calls_judge_run(
        self, loop_context, mock_agent_context
    ):
        """Judge.run is called once."""
        run_judge_phase(loop_context, mock_agent_context, iteration=1)

        mock_agent_context.judge.run.assert_called_once()
        call_kw = mock_agent_context.judge.run.call_args[1]
        assert call_kw["iteration"] == 1


# =============================================================================
# run_plan_finalize_on_judge_completion
# =============================================================================


class TestRunPlanFinalizeOnJudgeCompletion:
    """Tests for run_plan_finalize_on_judge_completion()."""

    def test_calls_planner_run_with_finalize_true(
        self, loop_context, mock_agent_context
    ):
        """Judge正常終了時に Planner が finalize=True で実行される。"""
        run_plan_finalize_on_judge_completion(loop_context, mock_agent_context, iteration=3)

        mock_agent_context.planner.run.assert_called_once()
        call_kw = mock_agent_context.planner.run.call_args[1]
        assert call_kw["iteration"] == 3
        assert call_kw["finalize"] is True
