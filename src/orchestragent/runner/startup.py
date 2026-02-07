"""Startup utilities for the agent system."""

import subprocess
import sys
from pathlib import Path

from orchestragent import config
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


def check_claude_code_cli() -> bool:
    """Check if Claude Code CLI is available."""
    try:
        result = subprocess.run(
            ['claude', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_gemini_cli() -> bool:
    """Check if Gemini CLI is available."""
    try:
        result = subprocess.run(
            ['gemini', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_available_backends() -> dict:
    """Get availability status of all supported backends."""
    return {
        "cursor_cli": check_cursor_cli(),
        "claude_code_cli": check_claude_code_cli(),
        "gemini_cli": check_gemini_cli(),
    }


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
    print(f"  デフォルトバックエンド: {config.LLM_BACKEND}")
    print(f"  出力形式: {config.LLM_OUTPUT_FORMAT}")

    # Per-agent Backend Configuration
    print("\n[エージェント別バックエンド設定]")
    print(f"  Planner: {config.PLANNER_BACKENDS or '(デフォルト)'}")
    print(f"  Worker: {config.WORKER_BACKENDS or '(デフォルト)'}")
    print(f"  Judge: {config.JUDGE_BACKENDS or '(デフォルト)'}")

    # Per-backend Model Configuration
    print("\n[バックエンド別モデル設定]")
    print(f"  Cursor CLI: {config.CURSOR_CLI_MODEL or '(CLI デフォルト)'}")
    print(f"  Claude Code CLI: {config.CLAUDE_CODE_CLI_MODEL or '(CLI デフォルト)'}")
    print(f"  Gemini CLI: {config.GEMINI_CLI_MODEL or '(CLI デフォルト)'}")

    # Dynamic Model Selection
    print("\n[動的モデル選択]")
    print(f"  有効: {'有効' if config.MODEL_SELECTION_ENABLED else '無効'}")
    if config.MODEL_SELECTION_ENABLED:
        print(f"  閾値 (軽量 < {config.MODEL_COMPLEXITY_THRESHOLD_LIGHT} < 標準 < {config.MODEL_COMPLEXITY_THRESHOLD_POWERFUL} < 複雑)")
        print("  [Cursor CLI]")
        print(f"    軽量: {config.CURSOR_CLI_MODEL_LIGHT or '(デフォルト)'}")
        print(f"    標準: {config.CURSOR_CLI_MODEL_STANDARD or '(デフォルト)'}")
        print(f"    複雑: {config.CURSOR_CLI_MODEL_POWERFUL or '(デフォルト)'}")
        print("  [Claude Code CLI]")
        print(f"    軽量: {config.CLAUDE_CODE_CLI_MODEL_LIGHT or '(デフォルト)'}")
        print(f"    標準: {config.CLAUDE_CODE_CLI_MODEL_STANDARD or '(デフォルト)'}")
        print(f"    複雑: {config.CLAUDE_CODE_CLI_MODEL_POWERFUL or '(デフォルト)'}")
        print("  [Gemini CLI]")
        print(f"    軽量: {config.GEMINI_CLI_MODEL_LIGHT or '(デフォルト)'}")
        print(f"    標準: {config.GEMINI_CLI_MODEL_STANDARD or '(デフォルト)'}")
        print(f"    複雑: {config.GEMINI_CLI_MODEL_POWERFUL or '(デフォルト)'}")

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

    # Environment Information
    print("\n[環境情報]")
    is_container = is_running_in_container()
    print(f"  実行環境: {'コンテナ内' if is_container else 'ホスト環境'}")

    # Check all available backends
    backends = get_available_backends()
    print("  利用可能なバックエンド:")
    for backend, available in backends.items():
        status = "利用可能" if available else "未検出"
        print(f"    - {backend}: {status}")

    print("=" * 60)
