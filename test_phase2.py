"""Test script for Phase 2 - Basic loop test without Cursor CLI."""

import sys
from pathlib import Path
from utils.state_manager import StateManager
from utils.logger import AgentLogger


def test_state_manager_extensions():
    """Test StateManager extended functionality."""
    print("=" * 60)
    print("Test 1: StateManager Extended Functions")
    print("=" * 60)
    
    state_manager = StateManager(state_dir="state")
    
    # Test get_pending_tasks
    print("\n[Test] get_pending_tasks()...")
    pending = state_manager.get_pending_tasks()
    print(f"✓ Pending tasks: {len(pending)}")
    
    # Test get_task_by_id
    print("\n[Test] get_task_by_id()...")
    if pending:
        task_id = pending[0].get("id")
        task = state_manager.get_task_by_id(task_id)
        assert task is not None, f"Task {task_id} not found"
        print(f"✓ Task found: {task.get('title', 'No title')}")
    
    # Test assign_task
    print("\n[Test] assign_task()...")
    if pending:
        task_id = pending[0].get("id")
        state_manager.assign_task(task_id, "test_worker")
        task = state_manager.get_task_by_id(task_id)
        assert task.get("status") == "in_progress", "Task not assigned"
        assert task.get("assigned_to") == "test_worker", "Worker not assigned"
        print(f"✓ Task {task_id} assigned")
    
    # Test complete_task
    print("\n[Test] complete_task()...")
    if pending:
        task_id = pending[0].get("id")
        result = {
            "report": "# Test Report\n\nTask completed successfully."
        }
        state_manager.complete_task(task_id, result)
        task = state_manager.get_task_by_id(task_id)
        assert task.get("status") == "completed", "Task not completed"
        print(f"✓ Task {task_id} completed")
    
    # Test fail_task
    print("\n[Test] fail_task()...")
    # Add a new task to fail
    test_task = {
        "title": "Test Task to Fail",
        "description": "This task will be failed",
        "priority": "low"
    }
    task_id = state_manager.add_task(test_task)
    state_manager.fail_task(task_id, "Test error")
    task = state_manager.get_task_by_id(task_id)
    assert task.get("status") == "failed", "Task not failed"
    print(f"✓ Task {task_id} failed")
    
    print("\n[Result] StateManager Extended Functions: All tests passed ✓")


def test_agent_imports():
    """Test all agent imports."""
    print("\n" + "=" * 60)
    print("Test 2: Agent Imports")
    print("=" * 60)
    
    try:
        from agents.planner import PlannerAgent
        from agents.worker import WorkerAgent
        from agents.judge import JudgeAgent
        print("✓ All agent imports successful")
        print("\n[Result] Agent Imports: All tests passed ✓")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        sys.exit(1)


def test_prompt_templates():
    """Test prompt template files."""
    print("\n" + "=" * 60)
    print("Test 3: Prompt Templates")
    print("=" * 60)
    
    templates = [
        "prompts/planner.md",
        "prompts/worker.md",
        "prompts/judge.md"
    ]
    
    for template in templates:
        path = Path(template)
        if path.exists():
            content = path.read_text(encoding='utf-8')
            print(f"✓ {template} exists ({len(content)} chars)")
        else:
            print(f"✗ {template} not found")
            sys.exit(1)
    
    print("\n[Result] Prompt Templates: All tests passed ✓")


def test_main_loop_structure():
    """Test main loop structure (without execution)."""
    print("\n" + "=" * 60)
    print("Test 4: Main Loop Structure")
    print("=" * 60)
    
    # Check if main loop code exists
    with open("main.py", 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    required_patterns = [
        ("planner.run", "Planner execution"),
        ("worker.run", "Worker execution"),
        ("judge.run", "Judge execution"),
        ("should_continue", "Continue check"),
        ("iteration", "Iteration loop")
    ]
    
    for pattern, description in required_patterns:
        if pattern in main_content:
            print(f"✓ Found: {description} ({pattern})")
        else:
            print(f"✗ Missing: {description} ({pattern})")
            sys.exit(1)
    
    print("\n[Result] Main Loop Structure: All tests passed ✓")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 2: Basic Loop Tests")
    print("(Without Cursor CLI)")
    print("=" * 60)
    
    try:
        test_agent_imports()
        test_prompt_templates()
        test_state_manager_extensions()
        test_main_loop_structure()
        
        print("\n" + "=" * 60)
        print("All Phase 2 basic tests passed! ✓")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Ensure Cursor CLI is authenticated in Docker")
        print("2. Run Phase 2: docker compose run --rm agent python main.py")
        print("3. Monitor the main loop execution")
        print("4. Check state files and logs for results")
        
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
