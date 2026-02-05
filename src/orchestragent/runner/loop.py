"""Main loop logic for the agent system."""

import time
from dataclasses import dataclass, field
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional

from orchestragent.core.environment import is_running_in_container
from orchestragent.core.exceptions import AgentError
from orchestragent.core.logger import AgentLogger
from orchestragent.llm.client import LLMClient
from orchestragent.llm.factory import LLMClientFactory
from orchestragent.llm.backend_config import (
    AgentBackendConfig,
    LLMBackendSettings,
    BackendDynamicModels,
)
from orchestragent.state.manager import StateManager
from orchestragent.state.file_lock import FileLockManager
from orchestragent.scheduler.task_scheduler import TaskScheduler
from orchestragent.agents.planner import PlannerAgent
from orchestragent.agents.worker import WorkerAgent
from orchestragent.agents.judge import JudgeAgent
from orchestragent.agents.plan_judge import PlanJudgeAgent

from .startup import (
    check_cursor_cli,
    check_cursor_auth,
    authenticate_cursor,
    print_configuration,
)


@dataclass(frozen=True)
class RunnerConfig:
    """Configuration for the main loop and agents. Used for dependency injection; tests can pass a mock RunnerConfig."""
    llm_backend: str
    working_dir: str
    llm_output_format: str
    state_dir: str
    log_dir: str
    log_level: str
    log_fsync: bool
    agent_config: Dict[str, Any] = field(default_factory=dict)
    planner_model: Optional[str] = None
    worker_model: Optional[str] = None
    judge_model: Optional[str] = None
    max_plan_revisions: int = 3
    max_retries: int = 3
    enable_parallel_execution: bool = True
    max_parallel_workers: int = 3
    wait_time_seconds: int = 60
    max_iterations: int = 100
    adr_dir: str = "docs/adr"
    model_selection_enabled: bool = False
    model_complexity_threshold_light: float = 10.0
    model_complexity_threshold_powerful: float = 30.0
    worker_model_light: Optional[str] = None
    worker_model_standard: Optional[str] = None
    worker_model_powerful: Optional[str] = None
    compress_old_checkpoints: bool = True
    # Per-agent backend configuration with fallback
    planner_backends: str = ""
    worker_backends: str = ""
    judge_backends: str = ""
    # Per-backend default models
    cursor_cli_model: Optional[str] = None
    claude_code_cli_model: Optional[str] = None
    gemini_cli_model: Optional[str] = None
    # Per-backend dynamic model selection
    cursor_cli_model_light: Optional[str] = None
    cursor_cli_model_standard: Optional[str] = None
    cursor_cli_model_powerful: Optional[str] = None
    claude_code_cli_model_light: Optional[str] = None
    claude_code_cli_model_standard: Optional[str] = None
    claude_code_cli_model_powerful: Optional[str] = None
    gemini_cli_model_light: Optional[str] = None
    gemini_cli_model_standard: Optional[str] = None
    gemini_cli_model_powerful: Optional[str] = None
    # Backend availability check
    check_backend_availability: bool = True

    @classmethod
    def from_global_config(cls) -> "RunnerConfig":
        """Build RunnerConfig from the global config module."""
        import config as global_config
        return cls(
            llm_backend=global_config.LLM_BACKEND,
            working_dir=str(global_config.WORKING_DIR),
            llm_output_format=global_config.LLM_OUTPUT_FORMAT,
            state_dir=global_config.STATE_DIR,
            log_dir=global_config.LOG_DIR,
            log_level=global_config.LOG_LEVEL,
            log_fsync=global_config.LOG_FSYNC,
            agent_config=global_config.AGENT_CONFIG.copy(),
            planner_model=global_config.PLANNER_MODEL,
            worker_model=global_config.WORKER_MODEL,
            judge_model=global_config.JUDGE_MODEL,
            max_plan_revisions=global_config.MAX_PLAN_REVISIONS,
            max_retries=global_config.MAX_RETRIES,
            enable_parallel_execution=global_config.ENABLE_PARALLEL_EXECUTION,
            max_parallel_workers=global_config.MAX_PARALLEL_WORKERS,
            wait_time_seconds=global_config.WAIT_TIME_SECONDS,
            max_iterations=global_config.MAX_ITERATIONS,
            adr_dir=getattr(global_config, "ADR_DIR", "docs/adr"),
            model_selection_enabled=global_config.MODEL_SELECTION_ENABLED,
            model_complexity_threshold_light=global_config.MODEL_COMPLEXITY_THRESHOLD_LIGHT,
            model_complexity_threshold_powerful=global_config.MODEL_COMPLEXITY_THRESHOLD_POWERFUL,
            worker_model_light=global_config.WORKER_MODEL_LIGHT,
            worker_model_standard=global_config.WORKER_MODEL_STANDARD,
            worker_model_powerful=global_config.WORKER_MODEL_POWERFUL,
            compress_old_checkpoints=global_config.COMPRESS_OLD_CHECKPOINTS,
            planner_backends=getattr(global_config, "PLANNER_BACKENDS", ""),
            worker_backends=getattr(global_config, "WORKER_BACKENDS", ""),
            judge_backends=getattr(global_config, "JUDGE_BACKENDS", ""),
            cursor_cli_model=getattr(global_config, "CURSOR_CLI_MODEL", None),
            claude_code_cli_model=getattr(global_config, "CLAUDE_CODE_CLI_MODEL", None),
            gemini_cli_model=getattr(global_config, "GEMINI_CLI_MODEL", None),
            cursor_cli_model_light=getattr(global_config, "CURSOR_CLI_MODEL_LIGHT", None),
            cursor_cli_model_standard=getattr(global_config, "CURSOR_CLI_MODEL_STANDARD", None),
            cursor_cli_model_powerful=getattr(global_config, "CURSOR_CLI_MODEL_POWERFUL", None),
            claude_code_cli_model_light=getattr(global_config, "CLAUDE_CODE_CLI_MODEL_LIGHT", None),
            claude_code_cli_model_standard=getattr(global_config, "CLAUDE_CODE_CLI_MODEL_STANDARD", None),
            claude_code_cli_model_powerful=getattr(global_config, "CLAUDE_CODE_CLI_MODEL_POWERFUL", None),
            gemini_cli_model_light=getattr(global_config, "GEMINI_CLI_MODEL_LIGHT", None),
            gemini_cli_model_standard=getattr(global_config, "GEMINI_CLI_MODEL_STANDARD", None),
            gemini_cli_model_powerful=getattr(global_config, "GEMINI_CLI_MODEL_POWERFUL", None),
            check_backend_availability=getattr(global_config, "CHECK_BACKEND_AVAILABILITY", True),
        )

    def build_backend_settings(self) -> LLMBackendSettings:
        """Build LLMBackendSettings from this config."""
        # Build per-backend dynamic models
        cursor_dynamic = None
        if any([self.cursor_cli_model_light, self.cursor_cli_model_standard, self.cursor_cli_model_powerful]):
            cursor_dynamic = BackendDynamicModels(
                model_light=self.cursor_cli_model_light,
                model_standard=self.cursor_cli_model_standard,
                model_powerful=self.cursor_cli_model_powerful,
            )

        claude_dynamic = None
        if any([self.claude_code_cli_model_light, self.claude_code_cli_model_standard, self.claude_code_cli_model_powerful]):
            claude_dynamic = BackendDynamicModels(
                model_light=self.claude_code_cli_model_light,
                model_standard=self.claude_code_cli_model_standard,
                model_powerful=self.claude_code_cli_model_powerful,
            )

        gemini_dynamic = None
        if any([self.gemini_cli_model_light, self.gemini_cli_model_standard, self.gemini_cli_model_powerful]):
            gemini_dynamic = BackendDynamicModels(
                model_light=self.gemini_cli_model_light,
                model_standard=self.gemini_cli_model_standard,
                model_powerful=self.gemini_cli_model_powerful,
            )

        return LLMBackendSettings(
            default_backend=self.llm_backend,
            default_model=self.planner_model,  # Backward compat: use first agent model as default
            output_format=self.llm_output_format,
            project_root=self.working_dir,
            cursor_cli_model=self.cursor_cli_model,
            claude_code_cli_model=self.claude_code_cli_model,
            gemini_cli_model=self.gemini_cli_model,
            cursor_cli_dynamic_models=cursor_dynamic,
            claude_code_cli_dynamic_models=claude_dynamic,
            gemini_cli_dynamic_models=gemini_dynamic,
            planner_backends=(
                AgentBackendConfig.from_string(self.planner_backends)
                if self.planner_backends else None
            ),
            worker_backends=(
                AgentBackendConfig.from_string(self.worker_backends)
                if self.worker_backends else None
            ),
            judge_backends=(
                AgentBackendConfig.from_string(self.judge_backends)
                if self.judge_backends else None
            ),
        )


@dataclass
class LoopContext:
    """Context: components created during session initialization."""

    state_manager: StateManager
    logger: AgentLogger
    llm_client: LLMClient  # Default client for backward compatibility
    file_lock_manager: FileLockManager
    task_scheduler: TaskScheduler
    runner_config: RunnerConfig
    backend_settings: Optional[LLMBackendSettings] = None
    planner_client: Optional[LLMClient] = None
    worker_client: Optional[LLMClient] = None
    judge_client: Optional[LLMClient] = None


@dataclass
class AgentContext:
    """Context: agents and config created during agent setup."""

    planner: PlannerAgent
    worker: WorkerAgent
    judge: JudgeAgent
    plan_judge: PlanJudgeAgent
    worker_config: Dict[str, Any]
    runner_config: RunnerConfig


def initialize_session(cfg: Optional[RunnerConfig] = None) -> LoopContext:
    """
    Initialize environment check, auth, StateManager, Logger, LLM, FileLock, TaskScheduler.
    Testable unit. Pass cfg to use that config; otherwise build from global config.
    """
    if cfg is None:
        cfg = RunnerConfig.from_global_config()

    print("=" * 60)
    print("orchestragent")
    print("Phase 1: 動作確認")
    print("=" * 60)

    print_configuration()

    if not is_running_in_container():
        print("\n[警告] コンテナ外で実行されています。Docker/DevContainerでの実行を推奨します。")

    if not check_cursor_cli():
        raise RuntimeError(
            "Cursor CLI not found. "
            "Please run in Docker container or install Cursor CLI."
        )

    auth_status = check_cursor_auth()
    if not auth_status:
        print("\n[警告] 認証状態の確認に失敗しました。")
        cursor_config_dir = Path.home() / '.cursor'
        cursor_config_auth = Path.home() / '.config' / 'cursor' / 'auth.json'
        if cursor_config_dir.exists() or cursor_config_auth.exists():
            print(f"[情報] Cursor設定ディレクトリが存在します:")
            if cursor_config_dir.exists():
                print(f"  - {cursor_config_dir}")
            if cursor_config_auth.exists():
                print(f"  - {cursor_config_auth}")
            print("[情報] 認証済みの可能性があります。続行します...")
        else:
            authenticate_cursor()

    print("\n[初期化] コンポーネントを初期化しています...")

    # Build backend settings for per-agent client creation
    backend_settings = cfg.build_backend_settings()

    # Create per-agent clients if configured, otherwise use default
    has_per_agent_backends = (
        cfg.planner_backends or cfg.worker_backends or cfg.judge_backends
    )

    if has_per_agent_backends:
        print("[初期化] エージェント別バックエンド設定を検出しました")
        planner_client = LLMClientFactory.create_for_agent(
            "planner", backend_settings, cfg.planner_model, cfg.check_backend_availability
        )
        worker_client = LLMClientFactory.create_for_agent(
            "worker", backend_settings, cfg.worker_model, cfg.check_backend_availability
        )
        judge_client = LLMClientFactory.create_for_agent(
            "judge", backend_settings, cfg.judge_model, cfg.check_backend_availability
        )
        # Use planner_client as default for backward compatibility
        llm_client = planner_client
    else:
        # Backward compatible: single client for all agents
        llm_client = LLMClientFactory.create(
            backend=cfg.llm_backend,
            project_root=cfg.working_dir,
            output_format=cfg.llm_output_format
        )
        planner_client = None
        worker_client = None
        judge_client = None

    state_manager = StateManager(state_dir=cfg.state_dir)

    validation = state_manager.validate_state()
    if not validation.valid:
        print("\n[警告] 状態ファイルに問題が検出されました")
        for error in validation.errors:
            print(f"  エラー: {error}")
        print("\n[復元] 最新のチェックポイントから復元を試みます...")
        if state_manager.recover_from_corruption():
            print("[復元] 復元に成功しました")
            validation = state_manager.validate_state()
            if not validation.valid:
                print("[警告] 復元後も問題が残っています。手動での確認を推奨します。")
        else:
            print("[復元] 復元に失敗しました。初期状態から開始します。")

    recovered_tasks = state_manager.recover_in_progress_tasks()
    if recovered_tasks:
        print(f"\n[復元] {len(recovered_tasks)}個の中断されたタスクを再実行可能にしました:")
        for task_id in recovered_tasks:
            print(f"  - {task_id}")

    logger = AgentLogger(
        log_dir=cfg.log_dir,
        log_level=cfg.log_level,
        sync=cfg.log_fsync,
    )

    file_lock_manager = FileLockManager(lock_dir=f"{cfg.state_dir}/locks")
    task_scheduler = TaskScheduler(state_manager, file_lock_manager)

    return LoopContext(
        state_manager=state_manager,
        logger=logger,
        llm_client=llm_client,
        file_lock_manager=file_lock_manager,
        task_scheduler=task_scheduler,
        runner_config=cfg,
        backend_settings=backend_settings,
        planner_client=planner_client,
        worker_client=worker_client,
        judge_client=judge_client,
    )


def setup_agents(ctx: LoopContext) -> AgentContext:
    """Set up agents (Planner, Worker, Judge, Plan_Judge). Testable unit; config from ctx.runner_config."""
    cfg = ctx.runner_config

    # Use per-agent clients if available, otherwise fall back to default
    planner_llm = ctx.planner_client or ctx.llm_client
    worker_llm = ctx.worker_client or ctx.llm_client
    judge_llm = ctx.judge_client or ctx.llm_client

    planner_config = cfg.agent_config.copy()
    planner_config["mode"] = "plan"
    planner_config["model"] = cfg.planner_model

    planner = PlannerAgent(
        name="Planner",
        llm_client=planner_llm,
        state_manager=ctx.state_manager,
        logger=ctx.logger,
        config=planner_config
    )

    import config as _cfg
    worker_config = cfg.agent_config.copy()
    worker_config["mode"] = "agent"
    worker_config["prompt_template"] = cfg.agent_config.get(
        "prompt_template_worker", _cfg.AGENT_CONFIG["prompt_template_worker"]
    )
    worker_config["model"] = cfg.worker_model

    worker = WorkerAgent(
        name="Worker",
        llm_client=worker_llm,
        state_manager=ctx.state_manager,
        logger=ctx.logger,
        config=worker_config,
        state_dir=cfg.state_dir,
        adr_dir=cfg.adr_dir,
        model_selection_enabled=cfg.model_selection_enabled,
        model_complexity_threshold_light=cfg.model_complexity_threshold_light,
        model_complexity_threshold_powerful=cfg.model_complexity_threshold_powerful,
        worker_model_light=cfg.worker_model_light,
        worker_model_standard=cfg.worker_model_standard,
        worker_model_powerful=cfg.worker_model_powerful,
        worker_model_default=cfg.worker_model,
    )

    judge_config = cfg.agent_config.copy()
    judge_config["mode"] = "ask"
    judge_config["prompt_template"] = cfg.agent_config.get(
        "prompt_template_judge", _cfg.AGENT_CONFIG["prompt_template_judge"]
    )
    judge_config["model"] = cfg.judge_model

    judge = JudgeAgent(
        name="Judge",
        llm_client=judge_llm,
        state_manager=ctx.state_manager,
        logger=ctx.logger,
        config=judge_config
    )

    plan_judge_config = cfg.agent_config.copy()
    plan_judge_config["mode"] = "ask"
    plan_judge_config["prompt_template"] = cfg.agent_config.get(
        "prompt_template_plan_judge", _cfg.AGENT_CONFIG["prompt_template_plan_judge"]
    )
    plan_judge_config["model"] = cfg.judge_model

    plan_judge = PlanJudgeAgent(
        name="Plan_Judge",
        llm_client=judge_llm,
        state_manager=ctx.state_manager,
        logger=ctx.logger,
        config=plan_judge_config,
    )

    print("[初期化] 完了")
    return AgentContext(
        planner=planner,
        worker=worker,
        judge=judge,
        plan_judge=plan_judge,
        worker_config=worker_config,
        runner_config=cfg,
    )


def run_plan_phase(
    ctx: LoopContext,
    agents: AgentContext,
    iteration: int,
) -> bool:
    """Run Planner ↔ Plan_Judge phase. Returns True if plan accepted, False if failed or max revisions reached without acceptance."""
    print("\n[1/3] Planner / Plan_Judge フェーズを開始します...")
    plan_loop_failed = False
    decision: Optional[str] = None

    cfg = ctx.runner_config
    for plan_attempt in range(1, cfg.max_plan_revisions + 1):
        print(f"\n[1/3] Planner実行中... (attempt {plan_attempt}/{cfg.max_plan_revisions})")
        try:
            agents.planner.run(iteration=iteration, max_retries=cfg.max_retries)
            print("[Planner] 完了")
        except AgentError as e:
            ctx.logger.log_error_with_traceback(
                "Planner", e, context={"iteration": iteration, "attempt": plan_attempt}
            )
            print(f"[Planner] エラー: {e}")
            plan_loop_failed = True
            break
        except Exception as e:
            ctx.logger.log_error_with_traceback(
                "Planner", e, context={"iteration": iteration, "attempt": plan_attempt}
            )
            print(f"[Planner] 予期しないエラー: {e}")
            plan_loop_failed = True
            break

        print("\n[1/3] Plan_Judge実行中...")
        try:
            plan_judge_result = agents.plan_judge.run(
                iteration=iteration, max_retries=cfg.max_retries
            )
            decision = plan_judge_result.get("decision", "accept")
            print(f"[Plan_Judge] 完了 (decision: {decision})")

            if decision != "revise":
                break
            print("[Plan_Judge] 計画の再検討が必要と判断されました。Planner を再実行します...")
        except AgentError as e:
            ctx.logger.log_error_with_traceback(
                "Plan_Judge", e, context={"iteration": iteration, "attempt": plan_attempt}
            )
            print(f"[Plan_Judge] エラー: {e}")
            plan_loop_failed = True
            break
        except Exception as e:
            ctx.logger.log_error_with_traceback(
                "Plan_Judge", e, context={"iteration": iteration, "attempt": plan_attempt}
            )
            print(f"[Plan_Judge] 予期しないエラー: {e}")
            plan_loop_failed = True
            break

    if plan_loop_failed or (decision is not None and decision == "revise"):
        return False
    return True


def run_work_phase(
    ctx: LoopContext,
    agents: AgentContext,
    iteration: int,
) -> None:
    """Run Worker phase (parallel or serial according to config)."""
    print("\n[2/3] Worker実行中...")

    cfg = ctx.runner_config
    if cfg.enable_parallel_execution:
        parallelizable_tasks = ctx.task_scheduler.get_parallelizable_tasks(
            max_workers=cfg.max_parallel_workers
        )

        if not parallelizable_tasks:
            print("[Worker] 並列実行可能なタスクがありません")
        else:
            print(f"[Worker] {len(parallelizable_tasks)}個のタスクを並列実行します")

            def run_worker_task(task_data) -> Dict[str, Any]:
                task_id = task_data.id
                rc = agents.runner_config
                # Use per-agent client if available
                worker_llm = ctx.worker_client or ctx.llm_client
                worker_instance = WorkerAgent(
                    name=f"Worker-{task_id}",
                    llm_client=worker_llm,
                    state_manager=ctx.state_manager,
                    logger=ctx.logger,
                    config=agents.worker_config,
                    state_dir=rc.state_dir,
                    adr_dir=rc.adr_dir,
                    model_selection_enabled=rc.model_selection_enabled,
                    model_complexity_threshold_light=rc.model_complexity_threshold_light,
                    model_complexity_threshold_powerful=rc.model_complexity_threshold_powerful,
                    worker_model_light=rc.worker_model_light,
                    worker_model_standard=rc.worker_model_standard,
                    worker_model_powerful=rc.worker_model_powerful,
                    worker_model_default=rc.worker_model,
                )

                result: Dict[str, Any] = {
                    "task_id": task_id,
                    "success": False,
                    "error": None
                }

                try:
                    task_files = ctx.task_scheduler._extract_task_files(task_data)
                    locks_acquired = []
                    for filepath in task_files:
                        if ctx.file_lock_manager.acquire_lock(filepath, task_id, timeout=10.0):
                            locks_acquired.append(filepath)
                        else:
                            for locked_file in locks_acquired:
                                ctx.file_lock_manager.release_lock(locked_file)
                            result["error"] = f"Failed to acquire lock for {filepath}"
                            return result

                    if worker_instance.assign_task(task_id):
                        try:
                            worker_instance.run(
                                iteration=iteration,
                                max_retries=cfg.max_retries
                            )
                            result["success"] = True
                            ctx.logger.info(f"[Worker-{task_id}] Task completed")
                        except Exception as e:
                            result["error"] = str(e)
                            ctx.state_manager.fail_task(task_id, str(e))
                            ctx.logger.log_error_with_traceback(
                                f"Worker-{task_id}",
                                e,
                                context={"iteration": iteration, "task_id": task_id}
                            )
                    else:
                        result["error"] = "Failed to assign task"

                    for filepath in locks_acquired:
                        ctx.file_lock_manager.release_lock(filepath)

                except Exception as e:
                    result["error"] = str(e)
                    ctx.logger.log_error_with_traceback(
                        f"Worker-{task_id}",
                        e,
                        context={"iteration": iteration, "task_id": task_id}
                    )

                return result

            with ThreadPoolExecutor(max_workers=cfg.max_parallel_workers) as executor:
                future_to_task = {
                    executor.submit(run_worker_task, task): task
                    for task in parallelizable_tasks
                }

                completed_count = 0
                failed_count = 0

                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    task_id = task.id
                    try:
                        result = future.result()
                        if result["success"]:
                            completed_count += 1
                            print(f"[Worker] タスク {task_id} 完了: {task.title}")
                        else:
                            failed_count += 1
                            print(f"[Worker] タスク {task_id} 失敗: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        failed_count += 1
                        ctx.logger.log_error_with_traceback(
                            f"Worker-{task_id}",
                            e,
                            context={"iteration": iteration, "task_id": task_id}
                        )
                        print(f"[Worker] タスク {task_id} 例外: {e}")

                print(f"[Worker] 並列実行完了: {completed_count}成功, {failed_count}失敗")

            stale_locks = ctx.file_lock_manager.cleanup_stale_locks(timeout=300.0)
            if stale_locks > 0:
                ctx.logger.info(f"Cleaned up {stale_locks} stale locks")
    else:
        pending_tasks = ctx.state_manager.get_pending_tasks()

        if not pending_tasks:
            print("[Worker] 保留中のタスクがありません")
        else:
            task = pending_tasks[0]
            task_id = task.id
            print(f"[Worker] タスク {task_id} を実行: {task.title}")

            if agents.worker.assign_task(task_id):
                try:
                    agents.worker.run(iteration=iteration, max_retries=cfg.max_retries)
                    print(f"[Worker] タスク {task_id} 完了")
                except AgentError as e:
                    ctx.logger.log_error_with_traceback(
                        "Worker",
                        e,
                        context={"iteration": iteration, "task_id": task_id}
                    )
                    ctx.state_manager.fail_task(task_id, str(e))
                    print(f"[Worker] エラー: {e}")
                except Exception as e:
                    ctx.logger.log_error_with_traceback(
                        "Worker",
                        e,
                        context={"iteration": iteration, "task_id": task_id}
                    )
                    ctx.state_manager.fail_task(task_id, str(e))
                    print(f"[Worker] 予期しないエラー: {e}")
            else:
                print(f"[Worker] タスク {task_id} の割り当てに失敗")


def run_judge_phase(
    ctx: LoopContext,
    agents: AgentContext,
    iteration: int,
) -> None:
    """Run Judge phase."""
    print("\n[3/3] Judge実行中...")
    cfg = ctx.runner_config
    try:
        agents.judge.run(iteration=iteration, max_retries=cfg.max_retries)
        print("[Judge] 完了")
    except AgentError as e:
        ctx.logger.log_error_with_traceback("Judge", e, context={"iteration": iteration})
        print(f"[Judge] エラー: {e}")
    except Exception as e:
        ctx.logger.log_error_with_traceback("Judge", e, context={"iteration": iteration})
        print(f"[Judge] 予期しないエラー: {e}")


def run_plan_finalize_on_judge_completion(
    ctx: LoopContext,
    agents: AgentContext,
    iteration: int,
) -> None:
    """
    Judgeが正常終了を判定した際に、Planner を「最終化」モードで実行し、
    state/plan.md 全体を現状（完了サマリ・残タスクの解消など）に合わせて更新する。
    """
    print("\n[計画の最終化] Planner を実行して state/plan.md を現状に合わせて更新します...")
    cfg = ctx.runner_config
    try:
        agents.planner.run(
            iteration=iteration,
            max_retries=cfg.max_retries,
            finalize=True,
        )
        print("[計画の最終化] 完了")
    except AgentError as e:
        ctx.logger.log_error_with_traceback(
            "Planner(finalize)", e, context={"iteration": iteration}
        )
        print(f"[計画の最終化] エラー: {e}")
    except Exception as e:
        ctx.logger.log_error_with_traceback(
            "Planner(finalize)", e, context={"iteration": iteration}
        )
        print(f"[計画の最終化] 予期しないエラー: {e}")


def run_main_loop(cfg: Optional[RunnerConfig] = None) -> None:
    """
    Run the main agent loop. Initializes session, sets up agents, and runs plan/work/judge phases.
    Pass cfg to use that config; otherwise build from global config.
    """
    ctx = initialize_session(cfg)
    agents = setup_agents(ctx)
    cfg = ctx.runner_config

    print("\n[Phase 2] メインループを開始します...")
    print(f"プロジェクト目標: {cfg.agent_config['project_goal']}")
    print(f"待機時間: {cfg.wait_time_seconds}秒")
    print(f"最大イテレーション: {cfg.max_iterations}")

    # 再実行時は継続判定を「継続」にリセット（Webダッシュボードの表示を正しくするため）
    ctx.state_manager.update_status(
        should_continue=True,
        reason="実行中",
    )

    iteration = 0

    try:
        checkpoint_path = ctx.state_manager.create_checkpoint("initial")
        ctx.logger.info(f"Initial checkpoint created: {checkpoint_path}")
        if cfg.compress_old_checkpoints:
            n = ctx.state_manager.compress_old_checkpoints(keep_latest_n=1)
            if n > 0:
                ctx.logger.info(f"Compressed {n} old checkpoint(s)")
    except Exception as e:
        ctx.logger.warning(f"Failed to create initial checkpoint: {e}")

    try:
        while iteration < cfg.max_iterations:
            iteration += 1
            print(f"\n{'=' * 60}")
            print(f"イテレーション {iteration}")
            print(f"{'=' * 60}")

            ctx.state_manager.update_status(current_iteration=iteration)

            if not run_plan_phase(ctx, agents, iteration):
                reason = (
                    "Planner と Plan_Judge の最大再計画回数に達しても妥当な計画に収束しなかったため、"
                    "エージェントシステム全体を失敗として終了します。"
                )
                print(f"\n[致命的エラー] {reason}")
                ctx.state_manager.update_status(
                    should_continue=False,
                    reason=reason,
                    plan_revision_failed=True,
                    last_failed_iteration=iteration,
                )
                break

            print(f"\n[待機] {cfg.wait_time_seconds}秒待機中...")
            time.sleep(cfg.wait_time_seconds)

            run_work_phase(ctx, agents, iteration)

            print(f"\n[待機] {cfg.wait_time_seconds}秒待機中...")
            time.sleep(cfg.wait_time_seconds)

            run_judge_phase(ctx, agents, iteration)

            status = ctx.state_manager.get_status()
            should_continue = status.get("should_continue", True)

            task_stats = ctx.state_manager.get_task_statistics()
            ctx.logger.log_progress(
                iteration=iteration,
                total_tasks=task_stats.total,
                completed_tasks=task_stats.completed,
                failed_tasks=task_stats.failed,
                pending_tasks=task_stats.pending
            )

            print(f"\n[判定] 継続判定: {should_continue}")
            print(f"理由: {status.get('reason', 'N/A')}")

            if not should_continue:
                print("\n[完了] Judgeが停止を判定しました")
                run_plan_finalize_on_judge_completion(ctx, agents, iteration)
                try:
                    checkpoint_path = ctx.state_manager.create_checkpoint("completed")
                    ctx.logger.info(f"完了時チェックポイント作成: {checkpoint_path}")
                    if cfg.compress_old_checkpoints:
                        n = ctx.state_manager.compress_old_checkpoints(keep_latest_n=1)
                        if n > 0:
                            ctx.logger.info(f"Compressed {n} old checkpoint(s)")
                except Exception as e:
                    ctx.logger.warning(f"Failed to create checkpoint on completion: {e}")
                break

            try:
                checkpoint_path = ctx.state_manager.create_checkpoint()
                ctx.logger.info(f"Checkpoint created after iteration {iteration}: {checkpoint_path}")
                if cfg.compress_old_checkpoints:
                    n = ctx.state_manager.compress_old_checkpoints(keep_latest_n=1)
                    if n > 0:
                        ctx.logger.info(f"Compressed {n} old checkpoint(s)")
            except Exception as e:
                ctx.logger.warning(f"Failed to create checkpoint: {e}")

            if iteration % 5 == 0:
                try:
                    backup_path = ctx.state_manager.create_backup()
                    ctx.logger.info(f"Backup created: {backup_path}")
                except Exception as e:
                    ctx.logger.warning(f"Failed to create backup: {e}")

            if iteration < cfg.max_iterations:
                print(f"\n[待機] 次のイテレーションまで {cfg.wait_time_seconds}秒待機中...")
                time.sleep(cfg.wait_time_seconds)

        if iteration >= cfg.max_iterations:
            print(f"\n[完了] 最大イテレーション数 ({cfg.max_iterations}) に達しました")

        print("\n" + "=" * 60)
        print("最終状態")
        print("=" * 60)

        task_stats = ctx.state_manager.get_task_statistics()
        print(f"総イテレーション: {iteration}")
        print(f"総タスク数: {task_stats.total}")
        print(f"完了タスク: {task_stats.completed}")
        print(f"失敗タスク: {task_stats.failed}")
        print(f"保留中タスク: {task_stats.pending}")
        print(f"実行中タスク: {task_stats.in_progress}")

    except KeyboardInterrupt:
        print("\n\n[中断] ユーザーによって中断されました")
        ctx.logger.info("Main loop interrupted by user")
        if cfg.enable_parallel_execution:
            ctx.file_lock_manager.release_all_locks()
        try:
            ctx.state_manager.update_status(should_continue=False)
        except Exception as e:
            ctx.logger.warning(f"Failed to update status on interrupt: {e}")
        try:
            checkpoint_path = ctx.state_manager.create_checkpoint("interrupted")
            ctx.logger.info(f"Checkpoint created before exit: {checkpoint_path}")
            print(f"[チェックポイント] 中断前の状態を保存しました: {checkpoint_path}")
            if cfg.compress_old_checkpoints:
                ctx.state_manager.compress_old_checkpoints(keep_latest_n=1)
        except Exception as e:
            ctx.logger.warning(f"Failed to create checkpoint before exit: {e}")
    except Exception as e:
        ctx.logger.log_error_with_traceback("MainLoop", e, context={"iteration": iteration})
        if cfg.enable_parallel_execution:
            ctx.file_lock_manager.release_all_locks()
        try:
            checkpoint_path = ctx.state_manager.create_checkpoint("error")
            ctx.logger.info(f"Checkpoint created after error: {checkpoint_path}")
            print(f"[チェックポイント] エラー発生時の状態を保存しました: {checkpoint_path}")
            if cfg.compress_old_checkpoints:
                ctx.state_manager.compress_old_checkpoints(keep_latest_n=1)
        except Exception as checkpoint_error:
            ctx.logger.warning(f"Failed to create checkpoint after error: {checkpoint_error}")
        raise

    print("\n[Phase 2] メインループ完了")
