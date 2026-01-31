"""Main entry point for the agent system."""

import sys
import argparse
from pathlib import Path

# Add src to path for package imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


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
            from orchestragent.dashboard.app import DashboardApp
            app = DashboardApp()
            app.run()
        except ImportError as e:
            print(f"エラー: ダッシュボードモードに必要なライブラリがインストールされていません: {e}")
            print("以下のコマンドでインストールしてください:")
            print("  pip install rich textual")
            sys.exit(1)
    else:
        # 通常モード（既存の動作）
        from orchestragent.runner.loop import run_main_loop
        run_main_loop()


if __name__ == "__main__":
    main()
