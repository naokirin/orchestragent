"""Main dashboard application using Textual."""

import threading
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Tabs, Tab, Static, Log
from textual import events
from typing import Optional, Any
import sys
import os

# Try to import on decorator (different versions have different import paths)
try:
    from textual.on import on
except ImportError:
    try:
        from textual import on
    except ImportError:
        # Fallback: define a simple decorator that works with message handlers
        def on(message_type, selector=None):
            def decorator(func):
                func._textual_on = (message_type, selector)
                return func
            return decorator

# Add parent directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import run_main_loop


class DashboardApp(App):
    """Main dashboard application."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #header-bar {
        height: 1;
        dock: top;
        background: $primary;
        color: $text;
        text-align: center;
    }
    
    #footer-bar {
        height: 1;
        dock: bottom;
        background: $primary;
        color: $text;
    }
    
    #tabs {
        margin-top: 0;
    }
    
    #content {
        height: 1fr;
        width: 1fr;
    }
    
    .tab-content {
        height: 1fr;
        width: 1fr;
        padding: 1;
    }
    
    .section-title {
        margin: 1;
        text-style: bold;
    }
    
    .content {
        margin: 1;
        padding: 1;
    }
    
    .spacer {
        height: 1;
    }
    
    .task-list-container {
        width: 50%;
        height: 1fr;
    }
    
    .task-detail-container {
        width: 50%;
        height: 1fr;
    }
    
    #task-detail-scroll {
        height: 1fr;
        width: 1fr;
    }
    """
    
    TITLE = "orchestragent ダッシュボード"
    BINDINGS = [
        ("q", "quit", "終了"),
        ("d", "toggle_dark", "ダークモード切替"),
    ]
    
    def __init__(self):
        super().__init__()
        self.main_loop_thread: Optional[threading.Thread] = None
        self._main_loop_running = False
        self.logs_widget: Optional[Any] = None
        self.tasks_widget: Optional[Any] = None
        self.settings_widget: Optional[Any] = None
        self.current_tab: Optional[str] = None
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Static("orchestragent ダッシュボード", id="header-bar")
        yield Tabs(
            Tab("概要", id="overview"),
            Tab("ログ", id="logs"),
            Tab("タスク", id="tasks"),
            Tab("設定", id="settings"),
            id="tabs"
        )
        yield Container(id="content")
        yield Static("[q] 終了  [d] ダークモード切替  [tab] タブ/コンテンツ切替", id="footer-bar", markup=False)
    
    def on_mount(self) -> None:
        """Called when app starts."""
        # Start main loop in background thread
        self._main_loop_running = True
        self.main_loop_thread = threading.Thread(
            target=self._run_main_loop,
            daemon=True,
            name="MainLoop"
        )
        self.main_loop_thread.start()
        
        # Set up periodic updates
        self.set_interval(0.5, self.update_display)
        
        # Show overview tab by default
        tabs_widget = self.query_one("#tabs", Tabs)
        tabs_widget.active = "overview"
        self.current_tab = "overview"
        self._show_overview()
    
    def _run_main_loop(self) -> None:
        """Run the main loop in a background thread."""
        try:
            # Redirect stdout/stderr to capture output
            # Note: This is a simplified approach. In production, you might want
            # to use a more sophisticated logging capture mechanism.
            run_main_loop()
        except Exception as e:
            self.log(f"Main loop error: {e}")
        finally:
            self._main_loop_running = False
    
    def update_display(self) -> None:
        """Update the display with current state."""
        # Check for tab changes
        try:
            tabs_widget = self.query_one("#tabs", Tabs)
            active_tab = tabs_widget.active
            if active_tab != self.current_tab:
                self.watch_tabs_active(active_tab)
        except Exception:
            pass
        
        # Update logs if logs widget is visible and mounted
        if self.logs_widget and hasattr(self.logs_widget, 'update_logs'):
            try:
                # Check if widget is still in the DOM (has a parent)
                if self.logs_widget._parent is not None:
                    self.logs_widget.update_logs()
            except Exception:
                pass  # Silently ignore update errors
        
        # Update tasks if tasks widget is visible
        if self.tasks_widget and hasattr(self.tasks_widget, 'update_tasks'):
            try:
                self.tasks_widget.update_tasks()
            except Exception:
                pass
        
        # Update overview if visible
        try:
            overview = self.query_one("#overview-widget", default=None)
            if overview and hasattr(overview, 'update_content'):
                overview.update_content()
        except Exception:
            pass
        
        # Update settings if visible
        if self.settings_widget and hasattr(self.settings_widget, 'update_content'):
            try:
                self.settings_widget.update_content()
            except Exception:
                pass
    
    def watch_tabs_active(self, active_tab: str) -> None:
        """Handle tab changes."""
        if active_tab == self.current_tab:
            return  # No change
        
        self.current_tab = active_tab
        
        # Clear widget references before switching (important to avoid NoActiveAppError)
        self.logs_widget = None
        self.tasks_widget = None
        self.settings_widget = None
        
        try:
            content = self.query_one("#content", Container)
            content.remove_children()
            
            if active_tab == "overview":
                self._show_overview()
            elif active_tab == "logs":
                self._show_logs()
            elif active_tab == "tasks":
                self._show_tasks()
            elif active_tab == "settings":
                self._show_settings()
        except Exception:
            pass  # Silently ignore errors during tab switching
    
    def _show_overview(self) -> None:
        """Show overview tab content."""
        from dashboard.widgets import OverviewWidget
        from utils.state_manager import StateManager
        import config
        
        content = self.query_one("#content", Container)
        state_manager = StateManager(state_dir=config.STATE_DIR)
        overview = OverviewWidget(state_manager)
        content.mount(overview)
    
    def _show_logs(self) -> None:
        """Show logs tab content."""
        from dashboard.widgets import LogsWidget
        
        content = self.query_one("#content", Container)
        log_widget = LogsWidget()
        content.mount(log_widget)
        self.logs_widget = log_widget  # Store reference for updates
    
    def _show_tasks(self) -> None:
        """Show tasks tab content."""
        from dashboard.widgets import TasksWidget
        from utils.state_manager import StateManager
        import config
        
        content = self.query_one("#content", Container)
        state_manager = StateManager(state_dir=config.STATE_DIR)
        tasks = TasksWidget(state_manager)
        content.mount(tasks)
        self.tasks_widget = tasks  # Store reference for updates
    
    def _show_settings(self) -> None:
        """Show settings tab content."""
        from dashboard.widgets import SettingsWidget
        
        content = self.query_one("#content", Container)
        settings = SettingsWidget()
        content.mount(settings)
        self.settings_widget = settings  # Store reference for updates
    
    def action_quit(self) -> None:
        """Handle quit action."""
        self._main_loop_running = False
        self.exit()
    
    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        # Toggle dark mode by adding/removing the dark class
        if "-dark-mode" in self.classes:
            self.remove_class("-dark-mode")
        else:
            self.add_class("-dark-mode")
