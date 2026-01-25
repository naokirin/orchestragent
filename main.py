"""Main entry point for the agent system."""

import os
import sys
import time
from pathlib import Path
from utils.llm_client_factory import LLMClientFactory
from utils.state_manager import StateManager
from utils.logger import AgentLogger
from agents.planner import PlannerAgent
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
        # Check if auth files exist
        cursor_config_dir = Path.home() / '.cursor'
        if cursor_config_dir.exists():
            config_files = list(cursor_config_dir.iterdir())
            if any('auth' in f.name.lower() or 'token' in f.name.lower() for f in config_files):
                return True
        
        # Try to run a command to check auth
        result = subprocess.run(
            ['agent', 'ls'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # If not auth error, assume authenticated
        if 'auth' in result.stderr.lower() or 'login' in result.stderr.lower():
            return False
        
        return result.returncode == 0
    except Exception as e:
        print(f"Warning: Could not check auth status: {e}")
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


def main():
    """Main function."""
    print("=" * 60)
    print("プランナー・ワーカースタイル自律エージェントシステム")
    print("Phase 1: 最小動作確認")
    print("=" * 60)
    
    # Environment check
    if not is_running_in_container():
        print("Warning: Not running in container. Recommended to use Docker/DevContainer.")
    
    if not check_cursor_cli():
        raise RuntimeError(
            "Cursor CLI not found. "
            "Please run in Docker container or install Cursor CLI."
        )
    
    # Auth check
    if not check_cursor_auth():
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
    
    # Initialize planner
    planner = PlannerAgent(
        name="Planner",
        llm_client=llm_client,
        state_manager=state_manager,
        logger=logger,
        config=config.AGENT_CONFIG
    )
    
    print("[初期化] 完了")
    
    # Phase 1: Test planner
    print("\n[Phase 1] Plannerエージェントをテストします...")
    print(f"プロジェクト目標: {config.AGENT_CONFIG['project_goal']}")
    
    try:
        result = planner.run(iteration=0)
        print("\n[Phase 1] Planner実行完了")
        print(f"結果: {result.get('reasoning', 'N/A')}")
        
        # Show created tasks
        tasks = state_manager.get_tasks()
        task_list = tasks.get("tasks", [])
        if task_list:
            print(f"\n作成されたタスク数: {len(task_list)}")
            for task in task_list[-5:]:  # Show last 5 tasks
                print(f"  - {task.get('id', 'unknown')}: {task.get('title', 'No title')}")
        
        # Show plan
        plan = state_manager.get_plan()
        if plan:
            print(f"\n計画が更新されました（{len(plan)}文字）")
        
    except Exception as e:
        logger.error(f"Error in planner execution: {e}")
        raise
    
    print("\n[Phase 1] テスト完了")


if __name__ == "__main__":
    main()
