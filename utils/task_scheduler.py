"""Task scheduling utilities for parallel execution."""

import re
from typing import List, Dict, Any, Set, Optional
from pathlib import Path
from .file_lock import FileLockManager
from .state_manager import StateManager


class TaskScheduler:
    """Schedules tasks for parallel execution while avoiding conflicts."""
    
    def __init__(self, state_manager: StateManager, file_lock_manager: FileLockManager):
        """
        Initialize task scheduler.
        
        Args:
            state_manager: State manager instance
            file_lock_manager: File lock manager instance
        """
        self.state_manager = state_manager
        self.file_lock_manager = file_lock_manager
    
    def get_parallelizable_tasks(self, max_workers: int = 3) -> List[Dict[str, Any]]:
        """
        Get list of tasks that can be executed in parallel.
        
        Args:
            max_workers: Maximum number of parallel workers
        
        Returns:
            List of tasks that can be executed in parallel
        """
        # Get all pending tasks
        pending_tasks = self.state_manager.get_pending_tasks()
        
        if not pending_tasks:
            return []
        
        # Filter tasks that have all dependencies completed
        ready_tasks = self._filter_ready_tasks(pending_tasks)
        
        # Sort by priority
        ready_tasks.sort(key=lambda t: self._get_priority_score(t), reverse=True)
        
        # Select tasks that don't conflict with each other
        selected_tasks = []
        locked_files: Set[str] = set()
        
        for task in ready_tasks:
            # Extract files that this task will modify
            task_files = self._extract_task_files(task)
            
            # Check if any files are already locked
            conflicts = False
            for filepath in task_files:
                if filepath in locked_files or self.file_lock_manager.is_locked(filepath):
                    conflicts = True
                    break
            
            if not conflicts:
                # Add task and lock its files
                selected_tasks.append(task)
                for filepath in task_files:
                    locked_files.add(filepath)
                
                # Stop if we have enough tasks
                if len(selected_tasks) >= max_workers:
                    break
        
        return selected_tasks
    
    def _filter_ready_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter tasks that have all dependencies completed.
        Loads dependency status from individual task files.
        
        Args:
            tasks: List of tasks to filter
        
        Returns:
            List of tasks with all dependencies completed
        """
        ready_tasks = []
        for task in tasks:
            dependencies = task.get("dependencies", [])
            if not dependencies:
                # No dependencies, ready to execute
                ready_tasks.append(task)
                continue
            
            # Check if all dependencies are completed (load from individual files)
            all_completed = True
            for dep_id in dependencies:
                dep_task = self.state_manager.get_task_by_id(dep_id)
                if not dep_task or dep_task.get("status") != "completed":
                    all_completed = False
                    break
            
            if all_completed:
                ready_tasks.append(task)
        
        return ready_tasks
    
    def _get_priority_score(self, task: Dict[str, Any]) -> int:
        """
        Get priority score for a task (higher is better).
        
        Args:
            task: Task dictionary
        
        Returns:
            Priority score
        """
        priority_map = {"high": 3, "medium": 2, "low": 1}
        priority = task.get("priority", "medium")
        return priority_map.get(priority, 2)
    
    def _extract_task_files(self, task: Dict[str, Any]) -> List[str]:
        """
        Extract file paths that a task will modify.
        
        Args:
            task: Task dictionary
        
        Returns:
            List of file paths
        """
        files = []
        
        # Check if task has explicit files field
        if "files" in task:
            files.extend(task["files"])
        
        # Extract from description
        description = task.get("description", "")
        
        # Look for file patterns
        # Pattern 1: Explicit file mentions (e.g., "file: src/main.py")
        explicit_pattern = r'file:\s*([^\s\n]+\.(py|ts|js|md|json|yml|yaml|txt|html|css))'
        matches = re.findall(explicit_pattern, description, re.IGNORECASE)
        files.extend([m[0] for m in matches])
        
        # Pattern 2: File paths in quotes or backticks
        quoted_pattern = r'["\'`]([^\'"`]+\.(py|ts|js|md|json|yml|yaml|txt|html|css))["\'`]'
        matches = re.findall(quoted_pattern, description, re.IGNORECASE)
        files.extend([m[0] for m in matches])
        
        # Pattern 3: Common file patterns
        common_pattern = r'([\w\-_/]+\.(py|ts|js|md|json|yml|yaml|txt|html|css))'
        matches = re.findall(common_pattern, description)
        files.extend([m[0] for m in matches])
        
        # Normalize and deduplicate
        normalized_files = []
        seen = set()
        for filepath in files:
            normalized = filepath.strip().strip('"\'`')
            if normalized and normalized not in seen:
                normalized_files.append(normalized)
                seen.add(normalized)
        
        return normalized_files
    
    def can_tasks_run_parallel(self, task1: Dict[str, Any], task2: Dict[str, Any]) -> bool:
        """
        Check if two tasks can run in parallel without conflicts.
        
        Args:
            task1: First task
            task2: Second task
        
        Returns:
            True if tasks can run in parallel
        """
        files1 = set(self._extract_task_files(task1))
        files2 = set(self._extract_task_files(task2))
        
        # Check for file overlap
        if files1 and files2:
            overlap = files1.intersection(files2)
            if overlap:
                return False
        
        # Check dependencies
        deps1 = set(task1.get("dependencies", []))
        deps2 = set(task2.get("dependencies", []))
        
        # If one task depends on the other, they can't run in parallel
        if task1.get("id") in deps2 or task2.get("id") in deps1:
            return False
        
        return True
