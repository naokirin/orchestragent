"""Render the single-page dashboard HTML (tabs + API-driven content)."""

from pathlib import Path

# モジュール読み込み時に HTML テンプレートをファイルから読み込む
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_DASHBOARD_HTML_PATH = _TEMPLATES_DIR / "dashboard.html"

with open(_DASHBOARD_HTML_PATH, encoding="utf-8") as _f:
    _DASHBOARD_HTML = _f.read()


def render_dashboard() -> str:
    """Return full HTML for the dashboard (overview, logs, tasks, intents, settings tabs)."""
    return _DASHBOARD_HTML
