"""Dashboard widgets for each tab."""

import sys
from textual.widgets import Static, DataTable, RichLog
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual import events
from typing import Dict, Any, List, Optional
from pathlib import Path
import config
from utils.state_manager import StateManager


class OverviewWidget(ScrollableContainer):
    """Overview tab widget showing project goal, task statistics, and progress."""
    
    def __init__(self, state_manager: StateManager):
        super().__init__()
        self.state_manager = state_manager
        self.id = "overview-widget"
    
    def compose(self):
        """Create overview content."""
        with Vertical():
            yield Static("[bold]プロジェクト目標[/bold]", classes="section-title")
            yield Static(id="project-goal", classes="content")
            
            yield Static("", classes="spacer")
            yield Static("[bold]進行状況[/bold]", classes="section-title")
            yield Static(id="progress-info", classes="content")
            
            yield Static("", classes="spacer")
            yield Static("[bold]タスク統計[/bold]", classes="section-title")
            yield Static(id="task-stats", classes="content")
    
    def on_mount(self) -> None:
        """Update content when mounted."""
        self.update_content()
    
    def update_content(self) -> None:
        """Update overview content from state."""
        # Project goal
        goal_widget = self.query_one("#project-goal", Static)
        goal = config.AGENT_CONFIG.get('project_goal', '未設定')
        goal_widget.update(f"[cyan]{goal}[/cyan]")
        
        # Progress info
        progress_widget = self.query_one("#progress-info", Static)
        status = self.state_manager.get_status()
        iteration = status.get('current_iteration', 0)
        max_iterations = config.MAX_ITERATIONS
        should_continue = status.get('should_continue', True)
        
        progress_text = f"""
イテレーション: [bold]{iteration}[/bold] / {max_iterations}
継続判定: [{'green' if should_continue else 'red'}]{'継続' if should_continue else '停止'}[/{'green' if should_continue else 'red'}]
理由: {status.get('reason', 'N/A')}
        """.strip()
        progress_widget.update(progress_text)
        
        # Task statistics
        stats_widget = self.query_one("#task-stats", Static)
        task_stats = self.state_manager.get_task_statistics()
        total = task_stats.get('total', 0)
        completed = task_stats.get('completed', 0)
        failed = task_stats.get('failed', 0)
        pending = task_stats.get('pending', 0)
        in_progress = task_stats.get('in_progress', 0)
        
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        stats_text = f"""
総タスク数: [bold]{total}[/bold]
完了: [green]{completed}[/green]
失敗: [red]{failed}[/red]
保留中: [yellow]{pending}[/yellow]
実行中: [cyan]{in_progress}[/cyan]
完了率: [bold]{completion_rate:.1f}%[/bold]
        """.strip()
        stats_widget.update(stats_text)


class LogsWidget(RichLog):
    """Logs tab widget showing real-time logs."""
    
    def __init__(self):
        super().__init__(id="logs-widget", max_lines=1000, markup=True)
        self.log_file_path: Optional[Path] = None
    
    def on_mount(self) -> None:
        """Set up log file monitoring and load existing logs."""
        from datetime import datetime
        log_dir = Path(config.LOG_DIR)
        log_file = log_dir / f"execution_{datetime.now().strftime('%Y%m%d')}.log"
        self.log_file_path = log_file
        
        # Load existing log content when tab is opened
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    if all_lines:
                        # Process and display all existing lines
                        processed_lines = []
                        for line in all_lines:
                            line = line.rstrip('\n\r')
                            if not line:
                                continue
                            
                            # Remove timestamp prefix for cleaner display
                            parts = line.split(' - ', 2)
                            if len(parts) >= 3:
                                level = parts[1]
                                message = parts[2].strip()
                                # Color code by level
                                if level == "ERROR":
                                    processed_lines.append(f"[red]{message}[/red]")
                                elif level == "WARNING":
                                    processed_lines.append(f"[yellow]{message}[/yellow]")
                                elif level == "INFO":
                                    processed_lines.append(f"[cyan]{message}[/cyan]")
                                else:
                                    processed_lines.append(message)
                            else:
                                processed_lines.append(line)
                        
                        # Write all existing lines
                        if processed_lines and self._parent is not None:
                            for line in processed_lines:
                                self.write(line)
                    
                    # Set last_position to end of file for future updates
                    f.seek(0, 2)  # Seek to end
                    self.last_position = f.tell()
            except Exception:
                self.last_position = 0
        else:
            self.last_position = 0
    
    def update_logs(self) -> None:
        """Read new log entries from file."""
        # Check if widget is still mounted (has a parent)
        if self._parent is None:
            return
        
        if not self.log_file_path or not self.log_file_path.exists():
            return
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                if new_lines:
                    # Process all lines first
                    processed_lines = []
                    for line in new_lines:
                        # Remove newline character and process
                        line = line.rstrip('\n\r')
                        if not line:
                            continue
                        
                        # Remove timestamp prefix for cleaner display
                        # Format: "2024-01-01 12:00:00 - INFO - message"
                        parts = line.split(' - ', 2)
                        if len(parts) >= 3:
                            level = parts[1]
                            message = parts[2].strip()
                            # Color code by level
                            if level == "ERROR":
                                processed_lines.append(f"[red]{message}[/red]")
                            elif level == "WARNING":
                                processed_lines.append(f"[yellow]{message}[/yellow]")
                            elif level == "INFO":
                                processed_lines.append(f"[cyan]{message}[/cyan]")
                            else:
                                processed_lines.append(message)
                        else:
                            # If format doesn't match, just write the line as-is
                            processed_lines.append(line)
                    
                    # Write each line using RichLog.write()
                    # Check again if still mounted before writing
                    if processed_lines and self._parent is not None:
                        for line in processed_lines:
                            self.write(line)
                    
                    self.last_position = f.tell()
        except Exception as e:
            # Silently ignore read errors (including NoActiveAppError)
            pass


class TasksWidget(ScrollableContainer):
    """Tasks tab widget showing task list and details."""
    
    def __init__(self, state_manager: StateManager):
        super().__init__()
        self.state_manager = state_manager
        self.id = "tasks-widget"
        self.selected_task_id: Optional[str] = None
        self._updating = False
        self._last_task_ids: List[str] = []  # Track task IDs for diff update
    
    def compose(self):
        """Create tasks content."""
        with Horizontal():
            with Vertical(classes="task-list-container"):
                yield Static("[bold]タスク一覧[/bold]", classes="section-title")
                yield DataTable(id="task-table")
            
            with Vertical(classes="task-detail-container"):
                yield Static("[bold]タスク詳細[/bold]", classes="section-title")
                with ScrollableContainer(id="task-detail-scroll"):
                    yield Static(id="task-detail", classes="content")
    
    def on_mount(self) -> None:
        """Set up task table."""
        table = self.query_one("#task-table", DataTable)
        # Column order: Status, ID, Title, Priority
        table.add_columns("ステータス", "ID", "タイトル", "優先度")
        table.cursor_type = "row"
        self.update_tasks()
    
    def _get_status_colored(self, status: str) -> str:
        """Get colored status text."""
        return {
            'pending': '[yellow]保留中[/yellow]',
            'in_progress': '[cyan]実行中[/cyan]',
            'completed': '[green]完了[/green]',
            'failed': '[red]失敗[/red]'
        }.get(status, status)
    
    def update_tasks(self) -> None:
        """Update task list from state using diff update to preserve cursor position."""
        # Skip update if we're already updating
        if self._updating:
            return
        
        self._updating = True
        try:
            table = self.query_one("#task-table", DataTable)
            all_tasks = self.state_manager.get_all_tasks_from_files()
            
            # Build current task data
            current_task_ids = []
            task_data_map = {}
            for task in all_tasks:
                task_id = task.get('id', 'N/A')
                current_task_ids.append(task_id)
                task_data_map[task_id] = {
                    'title': task.get('title', 'No title')[:30],
                    'status': task.get('status', 'unknown'),
                    'priority': task.get('priority', 'medium')
                }
            
            # Get existing row keys
            existing_keys = set()
            for row_key in table.rows.keys():
                existing_keys.add(str(row_key.value))
            
            # If table is empty (first load), just add all rows
            if not existing_keys:
                for task_id in current_task_ids:
                    data = task_data_map[task_id]
                    table.add_row(
                        self._get_status_colored(data['status']),
                        task_id,
                        data['title'],
                        data['priority'],
                        key=task_id
                    )
                self._last_task_ids = current_task_ids
                return
            
            # Update existing rows (only status changes are likely)
            for task_id in current_task_ids:
                if task_id in existing_keys:
                    # Update existing row - use update_cell for each column
                    data = task_data_map[task_id]
                    try:
                        # Update status (column 0)
                        table.update_cell(task_id, "ステータス", self._get_status_colored(data['status']))
                        # Update ID (column 1) - should stay in sync with row key
                        table.update_cell(task_id, "ID", task_id)
                        # Update title (column 2)
                        table.update_cell(task_id, "タイトル", data['title'])
                        # Update priority (column 3)
                        table.update_cell(task_id, "優先度", data['priority'])
                    except Exception:
                        pass  # Ignore errors during update
            
            # Add new rows
            new_task_ids = set(current_task_ids) - existing_keys
            for task_id in current_task_ids:
                if task_id in new_task_ids:
                    data = task_data_map[task_id]
                    table.add_row(
                        self._get_status_colored(data['status']),
                        task_id,
                        data['title'],
                        data['priority'],
                        key=task_id
                    )
            
            # Remove deleted rows
            deleted_task_ids = existing_keys - set(current_task_ids)
            for task_id in deleted_task_ids:
                try:
                    table.remove_row(task_id)
                except Exception:
                    pass  # Ignore errors during removal
            
            self._last_task_ids = current_task_ids
        finally:
            self._updating = False
    
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle cursor movement - track which row is highlighted."""
        if event.row_key:
            self.selected_task_id = str(event.row_key.value)
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle task selection (Enter key)."""
        task_id = event.row_key.value
        self.selected_task_id = task_id
        self._show_task_detail(task_id)
    
    def _show_task_detail(self, task_id: str) -> None:
        """Show task detail."""
        task = self.state_manager.get_task_by_id(task_id)
        if not task:
            return
        
        detail_widget = self.query_one("#task-detail", Static)
        
        updated_at = task.get('updated_at', task.get('completed_at', task.get('failed_at', 'N/A')))
        detail_text = f"""
[bold]ID:[/bold] {task.get('id', 'N/A')}
[bold]タイトル:[/bold] {task.get('title', 'No title')}
[bold]ステータス:[/bold] {task.get('status', 'unknown')}
[bold]優先度:[/bold] {task.get('priority', 'medium')}
[bold]作成日時:[/bold] {task.get('created_at', 'N/A')}
[bold]更新日時:[/bold] {updated_at}

[bold]説明:[/bold]
{task.get('description', '説明なし')}

[bold]ファイル:[/bold]
{', '.join(task.get('files', [])) if task.get('files') else 'なし'}
        """.strip()
        
        if task.get('status') == 'completed' and task.get('result'):
            detail_text += f"\n\n[bold]結果:[/bold]\n{task.get('result', {}).get('report', 'N/A')}"
        elif task.get('status') == 'failed' and task.get('error'):
            detail_text += f"\n\n[bold]エラー:[/bold]\n[red]{task.get('error', 'N/A')}[/red]"
        
        detail_widget.update(detail_text)


class SettingsWidget(ScrollableContainer):
    """Settings tab widget showing configuration and environment info."""
    
    def compose(self):
        """Create settings content."""
        with Vertical():
            yield Static("[bold]プロジェクト設定[/bold]", classes="section-title")
            yield Static(id="project-config", classes="content")
            
            yield Static("", classes="spacer")
            yield Static("[bold]LLM設定[/bold]", classes="section-title")
            yield Static(id="llm-config", classes="content")
            yield Static(id="model-config", classes="content")
            
            yield Static("", classes="spacer")
            yield Static("[bold]メインループ設定[/bold]", classes="section-title")
            yield Static(id="loop-config", classes="content")
            
            yield Static("", classes="spacer")
            yield Static("[bold]環境情報[/bold]", classes="section-title")
            yield Static(id="env-info", classes="content")
    
    def on_mount(self) -> None:
        """Update content when mounted."""
        self.update_content()
    
    def update_content(self) -> None:
        """Update settings content."""
        # Project configuration
        project_widget = self.query_one("#project-config", Static)
        target_project_info = f"\n対象プロジェクト: {config.TARGET_PROJECT}" if config.TARGET_PROJECT else ""
        project_text = f"""
プロジェクトルート: {config.PROJECT_ROOT}
プロジェクト目標: {config.AGENT_CONFIG.get('project_goal', '未設定')}{target_project_info}
状態ディレクトリ: {config.STATE_DIR}
ログディレクトリ: {config.LOG_DIR}
ログレベル: {config.LOG_LEVEL}
        """.strip()
        project_widget.update(project_text)
        
        # LLM configuration
        llm_widget = self.query_one("#llm-config", Static)
        llm_text = f"""
バックエンド: {config.LLM_BACKEND}
出力形式: {config.LLM_OUTPUT_FORMAT}
デフォルトモデル (LLM_MODEL): {config.LLM_MODEL or '(未設定)'}
        """.strip()
        llm_widget.update(llm_text)
        
        # Model configuration (per agent & dynamic selection)
        model_widget = self.query_one("#model-config", Static)
        model_text = f"""
[bold]エージェント別モデル[/bold]
Planner モデル: {config.PLANNER_MODEL or '(デフォルト)'}
Worker モデル: {config.WORKER_MODEL or '(デフォルト)'}
Judge モデル: {config.JUDGE_MODEL or '(デフォルト)'}

[bold]Worker 動的モデル選択[/bold]
有効: {'有効' if config.MODEL_SELECTION_ENABLED else '無効'}
軽量タスク用モデル: {config.WORKER_MODEL_LIGHT or '(デフォルト)'}
標準タスク用モデル: {config.WORKER_MODEL_STANDARD or '(デフォルト)'}
複雑タスク用モデル: {config.WORKER_MODEL_POWERFUL or '(デフォルト)'}
軽量判定閾値: {config.MODEL_COMPLEXITY_THRESHOLD_LIGHT}
複雑判定閾値: {config.MODEL_COMPLEXITY_THRESHOLD_POWERFUL}
        """.strip()
        model_widget.update(model_text)
        
        # Main loop configuration
        loop_widget = self.query_one("#loop-config", Static)
        loop_text = f"""
待機時間: {config.WAIT_TIME_SECONDS}秒
最大イテレーション数: {config.MAX_ITERATIONS}
最大リトライ数: {config.MAX_RETRIES}
並列実行: {'有効' if config.ENABLE_PARALLEL_EXECUTION else '無効'}
最大並列Worker数: {config.MAX_PARALLEL_WORKERS if config.ENABLE_PARALLEL_EXECUTION else 'N/A'}
        """.strip()
        loop_widget.update(loop_text)
        
        # Environment information
        env_widget = self.query_one("#env-info", Static)
        import os
        from main import is_running_in_container, check_cursor_cli
        
        is_container = is_running_in_container()
        cursor_available = check_cursor_cli()
        
        env_text = f"""
実行環境: {'コンテナ内' if is_container else 'ホスト環境'}
Cursor CLI: {'利用可能' if cursor_available else '未検出'}
Python バージョン: {sys.version.split()[0]}
        """.strip()
        env_widget.update(env_text)
