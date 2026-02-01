"""Task scheduling utilities for parallel execution."""

from typing import List, Set

from orchestragent.models import Task
from orchestragent.state.file_lock import FileLockManager
from orchestragent.state.manager import StateManager
from orchestragent.utils.file_extractor import extract_file_paths_from_text


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

    def get_parallelizable_tasks(self, max_workers: int = 3) -> List[Task]:
        """
        Get list of tasks that can be executed in parallel.

        Args:
            max_workers: Maximum number of parallel workers

        Returns:
            List of Task objects that can be executed in parallel
        """
        # Get all pending tasks
        pending_tasks = self.state_manager.get_pending_tasks()

        if not pending_tasks:
            return []

        # Filter tasks that have all dependencies completed
        ready_tasks = self._filter_ready_tasks(pending_tasks)

        # Sort by priority
        ready_tasks.sort(key=lambda t: t.priority.to_score(), reverse=True)

        # Select tasks that don't conflict with each other
        selected_tasks: List[Task] = []
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

    def _filter_ready_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Filter tasks that have all dependencies completed.
        Loads dependency status from individual task files.

        Args:
            tasks: List of Task objects to filter

        Returns:
            List of Task objects with all dependencies completed
        """
        ready_tasks: List[Task] = []
        for task in tasks:
            if not task.dependencies:
                # No dependencies, ready to execute
                ready_tasks.append(task)
                continue

            # Check if all dependencies are completed (load from individual files)
            all_completed = True
            for dep_id in task.dependencies:
                dep_task = self.state_manager.get_task_by_id(dep_id)
                if not dep_task or not dep_task.is_completed():
                    all_completed = False
                    break

            if all_completed:
                ready_tasks.append(task)

        return ready_tasks

    def _extract_task_files(self, task: Task) -> List[str]:
        """
        Extract file paths that a task will modify.

        Args:
            task: Task object

        Returns:
            List of file paths
        """
        files: List[str] = []

        # Check if task has explicit files field
        if task.files:
            files.extend(task.files)

        # Extract from description (include common path-like patterns for scheduling)
        from_description = extract_file_paths_from_text(
            task.description,
            include_common_pattern=True,
        )
        seen = set(files)
        for filepath in from_description:
            if filepath not in seen:
                files.append(filepath)
                seen.add(filepath)

        return files

    def can_tasks_run_parallel(self, task1: Task, task2: Task) -> bool:
        """
        Check if two tasks can run in parallel without conflicts.

        Args:
            task1: First Task object
            task2: Second Task object

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
        deps1 = set(task1.dependencies)
        deps2 = set(task2.dependencies)

        # If one task depends on the other, they can't run in parallel
        if task1.id in deps2 or task2.id in deps1:
            return False

        return True
