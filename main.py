"""Main entry point for the agent system."""

import os
import sys
import time
from pathlib import Path
import time
from utils.llm_client_factory import LLMClientFactory
from utils.state_manager import StateManager
from utils.logger import AgentLogger
from agents.planner import PlannerAgent
from agents.worker import WorkerAgent
from agents.judge import JudgeAgent
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
        print(f"  モデル: {config.LLM_MODEL}")
    else:
        print(f"  モデル: (デフォルト)")
    
    # State Configuration
    print("\n[状態管理設定]")
    print(f"  状態ディレクトリ: {config.STATE_DIR}")
    
    # Logging Configuration
    print("\n[ログ設定]")
    print(f"  ログディレクトリ: {config.LOG_DIR}")
    print(f"  ログレベル: {config.LOG_LEVEL}")
    
    # Main Loop Configuration
    print("\n[メインループ設定]")
    print(f"  待機時間: {config.WAIT_TIME_MINUTES}分")
    print(f"  最大イテレーション数: {config.MAX_ITERATIONS}")
    
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


def main():
    """Main function."""
    print("=" * 60)
    print("プランナー・ワーカースタイル自律エージェントシステム")
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
    
    llm_client = LLMClientFactory.create(
        backend=config.LLM_BACKEND,
        project_root=config.PROJECT_ROOT,
        output_format=config.LLM_OUTPUT_FORMAT
    )
    
    state_manager = StateManager(state_dir=config.STATE_DIR)
    logger = AgentLogger(log_dir=config.LOG_DIR, log_level=config.LOG_LEVEL)
    
    # Initialize agents
    planner_config = config.AGENT_CONFIG.copy()
    planner_config["mode"] = "plan"
    
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
    print(f"待機時間: {config.WAIT_TIME_MINUTES}分")
    print(f"最大イテレーション: {config.MAX_ITERATIONS}")
    
    iteration = 0
    
    try:
        while iteration < config.MAX_ITERATIONS:
            iteration += 1
            print(f"\n{'=' * 60}")
            print(f"イテレーション {iteration}")
            print(f"{'=' * 60}")
            
            # 1. Planner実行
            print("\n[1/3] Planner実行中...")
            try:
                planner.run(iteration=iteration)
                print("[Planner] 完了")
            except Exception as e:
                logger.error(f"[Planner] Error: {e}")
                print(f"[Planner] エラー: {e}")
            
            # 待機
            wait_seconds = config.WAIT_TIME_MINUTES * 60
            print(f"\n[待機] {config.WAIT_TIME_MINUTES}分待機中...")
            time.sleep(wait_seconds)
            
            # 2. Worker実行（保留中のタスクがある限り）
            print("\n[2/3] Worker実行中...")
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
                        worker_result = worker.run(iteration=iteration)
                        print(f"[Worker] タスク {task_id} 完了")
                    except Exception as e:
                        import traceback
                        error_traceback = traceback.format_exc()
                        error_msg = f"{type(e).__name__}: {e}\n{error_traceback}"
                        logger.error(f"[Worker] Error: {e}")
                        logger.error(f"[Worker] Traceback:\n{error_traceback}")
                        state_manager.fail_task(task_id, str(e))
                        print(f"[Worker] エラー: {e}")
                else:
                    print(f"[Worker] タスク {task_id} の割り当てに失敗")
                
                # 待機
                print(f"\n[待機] {config.WAIT_TIME_MINUTES}分待機中...")
                time.sleep(wait_seconds)
            
            # 3. Judge実行
            print("\n[3/3] Judge実行中...")
            try:
                judge.run(iteration=iteration)
                print("[Judge] 完了")
            except Exception as e:
                logger.error(f"[Judge] Error: {e}")
                print(f"[Judge] エラー: {e}")
            
            # 継続判定
            status = state_manager.get_status()
            should_continue = status.get("should_continue", True)
            
            print(f"\n[判定] 継続判定: {should_continue}")
            print(f"理由: {status.get('reason', 'N/A')}")
            
            if not should_continue:
                print("\n[完了] Judgeが停止を判定しました")
                break
            
            # 次のイテレーション前に待機
            if iteration < config.MAX_ITERATIONS:
                print(f"\n[待機] 次のイテレーションまで {config.WAIT_TIME_MINUTES}分待機中...")
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
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        raise
    
    print("\n[Phase 2] メインループ完了")


if __name__ == "__main__":
    main()
