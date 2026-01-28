"""Main entry point for the agent system."""

import os
import sys
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.llm_client_factory import LLMClientFactory
from utils.state_manager import StateManager
from utils.logger import AgentLogger
from utils.file_lock import FileLockManager
from utils.task_scheduler import TaskScheduler
from agents.planner import PlannerAgent
from agents.worker import WorkerAgent
from agents.judge import JudgeAgent
from utils.exceptions import AgentError
from typing import Dict, Any
import config


def is_running_in_container():
    """Check if running in container."""
    # Docker environment detection
    if os.path.exists('/.dockerenv'):
        return True
    # cgroup check
    try:
        with open('/proc/self/cgroup', 'r') as f:
            return 'docker' in f.read()
    except:
        pass
    return False


def check_cursor_cli():
    """Check if Cursor CLI is available."""
    import subprocess
    try:
        result = subprocess.run(
            ['agent', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_cursor_auth():
    """Check Cursor CLI authentication status."""
    import subprocess
    try:
        # Check if auth files exist (primary check)
        # Cursor CLI stores auth in two locations:
        # 1. ~/.cursor
        # 2. ~/.config/cursor/auth.json
        cursor_config_dir = Path.home() / '.cursor'
        cursor_config_auth = Path.home() / '.config' / 'cursor' / 'auth.json'
        
        # Check both locations
        has_auth = False
        if cursor_config_auth.exists():
            has_auth = True
        elif cursor_config_dir.exists():
            config_files = list(cursor_config_dir.iterdir())
            # Check for common auth file patterns
            auth_indicators = ['auth', 'token', 'session', 'config']
            if any(any(indicator in f.name.lower() for indicator in auth_indicators) for f in config_files):
                has_auth = True
        
        if has_auth:
            # Try a lightweight command to verify auth is working
            try:
                result = subprocess.run(
                    ['agent', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        
        # Fallback: Try a simple command (not 'ls' which might be slow)
        try:
            result = subprocess.run(
                ['agent', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # If version command works and config exists, assume authenticated
            if (cursor_config_dir.exists() or cursor_config_auth.exists()) and result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return False
    except Exception as e:
        print(f"Warning: Could not check auth status: {e}")
        # If config directory exists, assume authenticated (optimistic)
        cursor_config_dir = Path.home() / '.cursor'
        cursor_config_auth = Path.home() / '.config' / 'cursor' / 'auth.json'
        if cursor_config_dir.exists() or cursor_config_auth.exists():
            print("Note: Cursor config directory exists, assuming authenticated")
            return True
        return False


def authenticate_cursor():
    """Guide user through Cursor CLI authentication."""
    print("=" * 60)
    print("Cursor CLI認証が必要です")
    print("=" * 60)
    print("\n以下のコマンドを実行して認証してください:")
    print("  docker compose run --rm agent agent login")
    print("\n表示されたURLをホスト側のブラウザで開いて認証を完了してください。")
    print("認証後、このスクリプトを再実行してください。")
    print("=" * 60)
    sys.exit(1)


def print_configuration():
    """Print current configuration settings."""
    print("\n" + "=" * 60)
    print("実行設定")
    print("=" * 60)
    
    # Project Configuration
    print("\n[プロジェクト設定]")
    print(f"  プロジェクトルート: {config.PROJECT_ROOT}")
    print(f"  プロジェクト目標: {config.AGENT_CONFIG['project_goal']}")
    
    # LLM Configuration
    print("\n[LLM設定]")
    print(f"  バックエンド: {config.LLM_BACKEND}")
    print(f"  出力形式: {config.LLM_OUTPUT_FORMAT}")
    if config.LLM_MODEL:
        print(f"  デフォルトモデル: {config.LLM_MODEL}")
    else:
        print(f"  デフォルトモデル: (未設定)")
    
    # Model Configuration
    print("\n[モデル設定]")
    print(f"  Planner モデル: {config.PLANNER_MODEL or '(デフォルト)'}")
    print(f"  Worker モデル: {config.WORKER_MODEL or '(デフォルト)'}")
    print(f"  Judge モデル: {config.JUDGE_MODEL or '(デフォルト)'}")
    
    # Dynamic Model Selection
    print(f"\n[動的モデル選択]")
    print(f"  有効: {'有効' if config.MODEL_SELECTION_ENABLED else '無効'}")
    if config.MODEL_SELECTION_ENABLED:
        print(f"  軽量タスク用モデル: {config.WORKER_MODEL_LIGHT or '(デフォルト)'}")
        print(f"  標準タスク用モデル: {config.WORKER_MODEL_STANDARD or '(デフォルト)'}")
        print(f"  複雑タスク用モデル: {config.WORKER_MODEL_POWERFUL or '(デフォルト)'}")
        print(f"  軽量判定閾値: {config.MODEL_COMPLEXITY_THRESHOLD_LIGHT}")
        print(f"  複雑判定閾値: {config.MODEL_COMPLEXITY_THRESHOLD_POWERFUL}")
    
    # State Configuration
    print("\n[状態管理設定]")
    print(f"  状態ディレクトリ: {config.STATE_DIR}")
    
    # Logging Configuration
    print("\n[ログ設定]")
    print(f"  ログディレクトリ: {config.LOG_DIR}")
    print(f"  ログレベル: {config.LOG_LEVEL}")
    
    # Main Loop Configuration
    print("\n[メインループ設定]")
    print(f"  待機時間: {config.WAIT_TIME_SECONDS}秒")
    print(f"  最大イテレーション数: {config.MAX_ITERATIONS}")
    
    # Parallel Execution Configuration
    print("\n[並列実行設定]")
    print(f"  並列実行: {'有効' if config.ENABLE_PARALLEL_EXECUTION else '無効'}")
    if config.ENABLE_PARALLEL_EXECUTION:
        print(f"  最大並列Worker数: {config.MAX_PARALLEL_WORKERS}")
    
    # Agent Configuration
    print("\n[エージェント設定]")
    print(f"  Planner モード: plan")
    print(f"  Planner プロンプト: {config.AGENT_CONFIG['prompt_template']}")
    print(f"  Worker モード: agent")
    print(f"  Worker プロンプト: prompts/worker.md")
    print(f"  Judge モード: ask")
    print(f"  Judge プロンプト: prompts/judge.md")
    
    # Environment Information
    print("\n[環境情報]")
    is_container = is_running_in_container()
    print(f"  実行環境: {'コンテナ内' if is_container else 'ホスト環境'}")
    cursor_cli_available = check_cursor_cli()
    print(f"  Cursor CLI: {'利用可能' if cursor_cli_available else '未検出'}")
    
    print("=" * 60)


def run_main_loop():
    """
    Run the main agent loop.
    This function contains the original main loop logic.
    """
    print("=" * 60)
    print("orchestragent")
    print("Phase 1: 動作確認")
    print("=" * 60)
    
    # Print configuration at the start
    print_configuration()
    
    # Environment check
    if not is_running_in_container():
        print("\n[警告] コンテナ外で実行されています。Docker/DevContainerでの実行を推奨します。")
    
    if not check_cursor_cli():
        raise RuntimeError(
            "Cursor CLI not found. "
            "Please run in Docker container or install Cursor CLI."
        )
    
    # Auth check (with warning if check fails but continue if config exists)
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
    
    # Initialize components
    print("\n[初期化] コンポーネントを初期化しています...")
    
    # Use WORKING_DIR which is already determined based on container/host environment
    llm_client = LLMClientFactory.create(
        backend=config.LLM_BACKEND,
        project_root=str(config.WORKING_DIR),
        output_format=config.LLM_OUTPUT_FORMAT
    )
    
    state_manager = StateManager(state_dir=config.STATE_DIR)
    
    # Validate state and attempt recovery if needed
    validation = state_manager.validate_state()
    if not validation["valid"]:
        print("\n[警告] 状態ファイルに問題が検出されました")
        for error in validation["errors"]:
            print(f"  エラー: {error}")
        print("\n[復元] 最新のチェックポイントから復元を試みます...")
        if state_manager.recover_from_corruption():
            print("[復元] 復元に成功しました")
            # Re-validate
            validation = state_manager.validate_state()
            if not validation["valid"]:
                print("[警告] 復元後も問題が残っています。手動での確認を推奨します。")
        else:
            print("[復元] 復元に失敗しました。初期状態から開始します。")
    
    logger = AgentLogger(
        log_dir=config.LOG_DIR,
        log_level=config.LOG_LEVEL,
        sync=config.LOG_FSYNC,
    )
    
    # Initialize file lock manager and task scheduler for parallel execution
    file_lock_manager = FileLockManager(lock_dir=f"{config.STATE_DIR}/locks")
    task_scheduler = TaskScheduler(state_manager, file_lock_manager)
    
    # Initialize agents
    planner_config = config.AGENT_CONFIG.copy()
    planner_config["mode"] = "plan"
    planner_config["model"] = config.PLANNER_MODEL
    
    planner = PlannerAgent(
        name="Planner",
        llm_client=llm_client,
        state_manager=state_manager,
        logger=logger,
        config=planner_config
    )
    
    worker_config = config.AGENT_CONFIG.copy()
    worker_config["mode"] = "agent"
    worker_config["prompt_template"] = "prompts/worker.md"
    worker_config["model"] = config.WORKER_MODEL
    
    worker = WorkerAgent(
        name="Worker",
        llm_client=llm_client,
        state_manager=state_manager,
        logger=logger,
        config=worker_config
    )
    
    judge_config = config.AGENT_CONFIG.copy()
    judge_config["mode"] = "ask"
    judge_config["prompt_template"] = "prompts/judge.md"
    judge_config["model"] = config.JUDGE_MODEL
    
    judge = JudgeAgent(
        name="Judge",
        llm_client=llm_client,
        state_manager=state_manager,
        logger=logger,
        config=judge_config
    )
    
    print("[初期化] 完了")
    
    # Phase 2: Main loop
    print("\n[Phase 2] メインループを開始します...")
    print(f"プロジェクト目標: {config.AGENT_CONFIG['project_goal']}")
    print(f"待機時間: {config.WAIT_TIME_SECONDS}秒")
    print(f"最大イテレーション: {config.MAX_ITERATIONS}")
    
    iteration = 0
    
    # Create initial checkpoint
    try:
        checkpoint_path = state_manager.create_checkpoint("initial")
        logger.info(f"Initial checkpoint created: {checkpoint_path}")
    except Exception as e:
        logger.warning(f"Failed to create initial checkpoint: {e}")
    
    try:
        while iteration < config.MAX_ITERATIONS:
            iteration += 1
            print(f"\n{'=' * 60}")
            print(f"イテレーション {iteration}")
            print(f"{'=' * 60}")
            
            # Update status with current iteration
            state_manager.update_status(current_iteration=iteration)
            
            # 1. Planner実行
            print("\n[1/3] Planner実行中...")
            try:
                planner.run(iteration=iteration, max_retries=config.MAX_RETRIES)
                print("[Planner] 完了")
            except AgentError as e:
                logger.log_error_with_traceback("Planner", e, context={"iteration": iteration})
                print(f"[Planner] エラー: {e}")
                # Continue to next iteration even if planner fails
            except Exception as e:
                logger.log_error_with_traceback("Planner", e, context={"iteration": iteration})
                print(f"[Planner] 予期しないエラー: {e}")
                # Continue to next iteration
            
            # 待機
            wait_seconds = config.WAIT_TIME_SECONDS
            print(f"\n[待機] {config.WAIT_TIME_SECONDS}秒待機中...")
            time.sleep(wait_seconds)
            
            # 2. Worker実行（並列実行対応）
            print("\n[2/3] Worker実行中...")
            
            if config.ENABLE_PARALLEL_EXECUTION:
                # Parallel execution mode
                parallelizable_tasks = task_scheduler.get_parallelizable_tasks(
                    max_workers=config.MAX_PARALLEL_WORKERS
                )
                
                if not parallelizable_tasks:
                    print("[Worker] 並列実行可能なタスクがありません")
                else:
                    print(f"[Worker] {len(parallelizable_tasks)}個のタスクを並列実行します")
                    
                    def run_worker_task(task_data: Dict[str, Any]) -> Dict[str, Any]:
                        """Run a single worker task."""
                        task_id = task_data.get("id")
                        worker_instance = WorkerAgent(
                            name=f"Worker-{task_id}",
                            llm_client=llm_client,
                            state_manager=state_manager,
                            logger=logger,
                            config=worker_config
                        )
                        
                        result = {
                            "task_id": task_id,
                            "success": False,
                            "error": None
                        }
                        
                        try:
                            # Acquire file locks
                            task_files = task_scheduler._extract_task_files(task_data)
                            locks_acquired = []
                            for filepath in task_files:
                                if file_lock_manager.acquire_lock(filepath, task_id, timeout=10.0):
                                    locks_acquired.append(filepath)
                                else:
                                    # Failed to acquire lock, release acquired locks and skip
                                    for locked_file in locks_acquired:
                                        file_lock_manager.release_lock(locked_file)
                                    result["error"] = f"Failed to acquire lock for {filepath}"
                                    return result
                            
                            # Assign and run task
                            if worker_instance.assign_task(task_id):
                                try:
                                    worker_result = worker_instance.run(
                                        iteration=iteration,
                                        max_retries=config.MAX_RETRIES
                                    )
                                    result["success"] = True
                                    logger.info(f"[Worker-{task_id}] Task completed")
                                except Exception as e:
                                    result["error"] = str(e)
                                    state_manager.fail_task(task_id, str(e))
                                    logger.log_error_with_traceback(
                                        f"Worker-{task_id}",
                                        e,
                                        context={"iteration": iteration, "task_id": task_id}
                                    )
                            else:
                                result["error"] = "Failed to assign task"
                            
                            # Release file locks
                            for filepath in locks_acquired:
                                file_lock_manager.release_lock(filepath)
                        
                        except Exception as e:
                            result["error"] = str(e)
                            logger.log_error_with_traceback(
                                f"Worker-{task_id}",
                                e,
                                context={"iteration": iteration, "task_id": task_id}
                            )
                        
                        return result
                    
                    # Execute tasks in parallel
                    with ThreadPoolExecutor(max_workers=config.MAX_PARALLEL_WORKERS) as executor:
                        future_to_task = {
                            executor.submit(run_worker_task, task): task
                            for task in parallelizable_tasks
                        }
                        
                        completed_count = 0
                        failed_count = 0
                        
                        for future in as_completed(future_to_task):
                            task = future_to_task[future]
                            task_id = task.get("id")
                            try:
                                result = future.result()
                                if result["success"]:
                                    completed_count += 1
                                    print(f"[Worker] タスク {task_id} 完了: {task.get('title', 'No title')}")
                                else:
                                    failed_count += 1
                                    print(f"[Worker] タスク {task_id} 失敗: {result.get('error', 'Unknown error')}")
                            except Exception as e:
                                failed_count += 1
                                logger.log_error_with_traceback(
                                    f"Worker-{task_id}",
                                    e,
                                    context={"iteration": iteration, "task_id": task_id}
                                )
                                print(f"[Worker] タスク {task_id} 例外: {e}")
                        
                        print(f"[Worker] 並列実行完了: {completed_count}成功, {failed_count}失敗")
                    
                    # Cleanup stale locks
                    stale_locks = file_lock_manager.cleanup_stale_locks(timeout=300.0)
                    if stale_locks > 0:
                        logger.info(f"Cleaned up {stale_locks} stale locks")
            else:
                # Sequential execution mode (original behavior)
                pending_tasks = state_manager.get_pending_tasks()
                
                if not pending_tasks:
                    print("[Worker] 保留中のタスクがありません")
                else:
                    # 最初の保留タスクを実行
                    task = pending_tasks[0]
                    task_id = task.get("id")
                    print(f"[Worker] タスク {task_id} を実行: {task.get('title', 'No title')}")
                    
                    if worker.assign_task(task_id):
                        try:
                            # Worker.run() will use self.current_task_id set by assign_task()
                            worker_result = worker.run(iteration=iteration, max_retries=config.MAX_RETRIES)
                            print(f"[Worker] タスク {task_id} 完了")
                        except AgentError as e:
                            logger.log_error_with_traceback(
                                "Worker",
                                e,
                                context={"iteration": iteration, "task_id": task_id}
                            )
                            state_manager.fail_task(task_id, str(e))
                            print(f"[Worker] エラー: {e}")
                        except Exception as e:
                            logger.log_error_with_traceback(
                                "Worker",
                                e,
                                context={"iteration": iteration, "task_id": task_id}
                            )
                            state_manager.fail_task(task_id, str(e))
                            print(f"[Worker] 予期しないエラー: {e}")
                    else:
                        print(f"[Worker] タスク {task_id} の割り当てに失敗")
            
            # 待機
            print(f"\n[待機] {config.WAIT_TIME_SECONDS}秒待機中...")
            time.sleep(wait_seconds)
            
            # 3. Judge実行
            print("\n[3/3] Judge実行中...")
            try:
                judge.run(iteration=iteration, max_retries=config.MAX_RETRIES)
                print("[Judge] 完了")
            except AgentError as e:
                logger.log_error_with_traceback("Judge", e, context={"iteration": iteration})
                print(f"[Judge] エラー: {e}")
                # Continue to next iteration even if judge fails
            except Exception as e:
                logger.log_error_with_traceback("Judge", e, context={"iteration": iteration})
                print(f"[Judge] 予期しないエラー: {e}")
                # Continue to next iteration
            
            # 継続判定
            status = state_manager.get_status()
            should_continue = status.get("should_continue", True)
            
            # 進捗ログ（個別タスクファイルから正確な状態を取得）
            task_stats = state_manager.get_task_statistics()
            total_tasks = task_stats["total"]
            completed_tasks = task_stats["completed"]
            failed_tasks = task_stats["failed"]
            pending_tasks = task_stats["pending"]
            
            logger.log_progress(
                iteration=iteration,
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                pending_tasks=pending_tasks
            )
            
            print(f"\n[判定] 継続判定: {should_continue}")
            print(f"理由: {status.get('reason', 'N/A')}")
            
            if not should_continue:
                print("\n[完了] Judgeが停止を判定しました")
                break
            
            # Create checkpoint after each iteration
            try:
                checkpoint_path = state_manager.create_checkpoint()
                logger.info(f"Checkpoint created after iteration {iteration}: {checkpoint_path}")
            except Exception as e:
                logger.warning(f"Failed to create checkpoint: {e}")
            
            # Create backup periodically (every 5 iterations)
            if iteration % 5 == 0:
                try:
                    backup_path = state_manager.create_backup()
                    logger.info(f"Backup created: {backup_path}")
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")
            
            # 次のイテレーション前に待機
            if iteration < config.MAX_ITERATIONS:
                print(f"\n[待機] 次のイテレーションまで {config.WAIT_TIME_SECONDS}秒待機中...")
                time.sleep(wait_seconds)
        
        if iteration >= config.MAX_ITERATIONS:
            print(f"\n[完了] 最大イテレーション数 ({config.MAX_ITERATIONS}) に達しました")
        
        # 最終状態を表示
        print("\n" + "=" * 60)
        print("最終状態")
        print("=" * 60)
        
        tasks = state_manager.get_tasks()
        task_list = tasks.get("tasks", [])
        status = state_manager.get_status()
        
        print(f"総イテレーション: {iteration}")
        print(f"総タスク数: {len(task_list)}")
        print(f"完了タスク: {status.get('completed_tasks', 0)}")
        print(f"失敗タスク: {status.get('failed_tasks', 0)}")
        print(f"保留中タスク: {len([t for t in task_list if t.get('status') == 'pending'])}")
        
    except KeyboardInterrupt:
        print("\n\n[中断] ユーザーによって中断されました")
        logger.info("Main loop interrupted by user")
        # Release all file locks
        if config.ENABLE_PARALLEL_EXECUTION:
            file_lock_manager.release_all_locks()
        # Create checkpoint before exit
        try:
            checkpoint_path = state_manager.create_checkpoint("interrupted")
            logger.info(f"Checkpoint created before exit: {checkpoint_path}")
            print(f"[チェックポイント] 中断前の状態を保存しました: {checkpoint_path}")
        except Exception as e:
            logger.warning(f"Failed to create checkpoint before exit: {e}")
    except Exception as e:
        logger.log_error_with_traceback("MainLoop", e, context={"iteration": iteration})
        # Release all file locks
        if config.ENABLE_PARALLEL_EXECUTION:
            file_lock_manager.release_all_locks()
        # Create checkpoint before exit
        try:
            checkpoint_path = state_manager.create_checkpoint("error")
            logger.info(f"Checkpoint created after error: {checkpoint_path}")
            print(f"[チェックポイント] エラー発生時の状態を保存しました: {checkpoint_path}")
        except Exception as checkpoint_error:
            logger.warning(f"Failed to create checkpoint after error: {checkpoint_error}")
        raise
    
    print("\n[Phase 2] メインループ完了")


def main():
    """
    Main entry point with command-line argument parsing.
    Supports --dashboard option to run in dashboard mode.
    """
    parser = argparse.ArgumentParser(
        description='プランナー・ワーカースタイル自律エージェントシステム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python main.py                    # 簡易ログ形式（デフォルト）
  python main.py --dashboard         # ダッシュボード形式
        """
    )
    parser.add_argument(
        '--dashboard',
        action='store_true',
        help='ダッシュボード形式で表示（インタラクティブなUI）'
    )
    
    args = parser.parse_args()
    
    if args.dashboard:
        # ダッシュボードモード
        try:
            from dashboard.app import DashboardApp
            app = DashboardApp()
            app.run()
        except ImportError as e:
            print(f"エラー: ダッシュボードモードに必要なライブラリがインストールされていません: {e}")
            print("以下のコマンドでインストールしてください:")
            print("  pip install rich textual")
            sys.exit(1)
    else:
        # 通常モード（既存の動作）
        run_main_loop()


if __name__ == "__main__":
    main()
