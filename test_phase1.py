"""Test script for Phase 1 - Basic functionality test without Cursor CLI."""

import sys
from pathlib import Path
from utils.state_manager import StateManager
from utils.logger import AgentLogger


def test_state_manager():
    """Test StateManager functionality."""
    print("=" * 60)
    print("Test 1: StateManager")
    print("=" * 60)
    
    state_manager = StateManager(state_dir="state")
    
    # Test JSON operations
    print("\n[Test] JSON operations...")
    test_data = {"test": "value", "number": 42}
    state_manager.save_json("test.json", test_data)
    loaded = state_manager.load_json("test.json")
    assert loaded == test_data, "JSON save/load failed"
    print("✓ JSON save/load: OK")
    
    # Test text operations
    print("\n[Test] Text operations...")
    test_text = "# Test Plan\n\nThis is a test plan."
    state_manager.save_text("test.md", test_text)
    loaded_text = state_manager.load_text("test.md")
    assert loaded_text == test_text, "Text save/load failed"
    print("✓ Text save/load: OK")
    
    # Test task operations
    print("\n[Test] Task operations...")
    task = {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": "high"
    }
    task_id = state_manager.add_task(task)
    print(f"✓ Task added: {task_id}")
    
    tasks = state_manager.get_tasks()
    assert len(tasks.get("tasks", [])) > 0, "Task not added"
    print("✓ Task retrieval: OK")
    
    # Cleanup
    (Path("state") / "test.json").unlink(missing_ok=True)
    (Path("state") / "test.md").unlink(missing_ok=True)
    
    print("\n[Result] StateManager: All tests passed ✓")


def test_logger():
    """Test Logger functionality."""
    print("\n" + "=" * 60)
    print("Test 2: Logger")
    print("=" * 60)
    
    logger = AgentLogger(log_dir="logs", log_level="INFO")
    
    # Test logging
    print("\n[Test] Logging operations...")
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.debug("Test debug message")
    print("✓ Log messages: OK")
    
    # Test agent run logging
    print("\n[Test] Agent run logging...")
    logger.log_agent_run(
        agent_name="TestAgent",
        iteration=0,
        prompt="Test prompt",
        response="Test response",
        duration=1.5
    )
    print("✓ Agent run logging: OK")
    
    print("\n[Result] Logger: All tests passed ✓")


def test_imports():
    """Test all imports."""
    print("\n" + "=" * 60)
    print("Test 3: Imports")
    print("=" * 60)
    
    try:
        from utils.llm_client import LLMClient
        from utils.cursor_cli_client import CursorCLIClient
        from utils.llm_client_factory import LLMClientFactory
        from agents.base import BaseAgent
        from agents.planner import PlannerAgent
        print("✓ All imports successful")
        print("\n[Result] Imports: All tests passed ✓")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        sys.exit(1)


def test_config():
    """Test configuration loading."""
    print("\n" + "=" * 60)
    print("Test 4: Configuration")
    print("=" * 60)
    
    try:
        import config
        print(f"✓ PROJECT_ROOT: {config.PROJECT_ROOT}")
        print(f"✓ LLM_BACKEND: {config.LLM_BACKEND}")
        print(f"✓ STATE_DIR: {config.STATE_DIR}")
        print(f"✓ LOG_DIR: {config.LOG_DIR}")
        print("\n[Result] Configuration: All tests passed ✓")
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        sys.exit(1)


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 1: Basic Functionality Tests")
    print("(Without Cursor CLI)")
    print("=" * 60)
    
    try:
        test_imports()
        test_config()
        test_state_manager()
        test_logger()
        
        print("\n" + "=" * 60)
        print("All Phase 1 basic tests passed! ✓")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Set up Docker environment (Dockerfile and docker-compose.yml)")
        print("2. Build Docker image: docker-compose build")
        print("3. Authenticate Cursor CLI: docker-compose run --rm agent agent --help")
        print("4. Run Phase 1 test: docker-compose run --rm agent python main.py")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
