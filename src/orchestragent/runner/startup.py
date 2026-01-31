"""Startup utilities for the agent system."""

import subprocess
import sys
from pathlib import Path

import config
from orchestragent.core.environment import is_running_in_container


def check_cursor_cli() -> bool:
    """Check if Cursor CLI is available."""
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


def check_cursor_auth() -> bool:
    """Check Cursor CLI authentication status."""
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


def authenticate_cursor() -> None:
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


def print_configuration() -> None:
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
