"""State management utilities for the agent system."""

import json
import os
import shutil
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Union
from datetime import datetime

from .models import (
    Task,
    TaskIndex,
    TasksFile,
    TaskStatistics,
    TaskStatus,
    TaskPriority,
    TaskResult,
    CheckpointMetadata,
    ValidationResult,
)


class StateManager:
    """Manages state files for the agent system."""
    
    def __init__(self, state_dir: str = "state", backup_dir: str = "state/backups"):
        """
        Initialize StateManager.
        
        Args:
            state_dir: Directory path for state files
            backup_dir: Directory path for backups
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Backup directory for state recovery
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure subdirectories exist
        (self.state_dir / "results").mkdir(exist_ok=True)
        (self.state_dir / "checkpoints").mkdir(exist_ok=True)
        (self.state_dir / "tasks").mkdir(exist_ok=True)  # Individual task files
    
    def load_json(self, filename: str) -> Dict[str, Any]:
        """
        Load JSON file from state directory.
        
        Args:
            filename: JSON filename (e.g., "tasks.json")
        
        Returns:
            Dictionary containing the JSON data, or empty dict if file doesn't exist
        
        Raises:
            StateCorruptionError: If JSON file is corrupted
        """
        filepath = self.state_dir / filename
        if not filepath.exists():
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # Import here to avoid circular import
            from .exceptions import StateCorruptionError
            raise StateCorruptionError(filename, e)
    
    def save_json(self, filename: str, data: Dict[str, Any]) -> None:
        """
        Save dictionary to JSON file in state directory.
        
        Args:
            filename: JSON filename (e.g., "tasks.json")
            data: Dictionary to save
        """
        filepath = self.state_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_text(self, filename: str) -> str:
        """
        Load text file from state directory.
        
        Args:
            filename: Text filename (e.g., "plan.md")
        
        Returns:
            String content of the file, or empty string if file doesn't exist
        """
        filepath = self.state_dir / filename
        if not filepath.exists():
            return ""
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def save_text(self, filename: str, content: str) -> None:
        """
        Save string to text file in state directory.
        
        Args:
            filename: Text filename (e.g., "plan.md")
            content: String content to save
        """
        filepath = self.state_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def update_json(
        self, 
        filename: str, 
        update_func: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update JSON file using a function with optimistic concurrency control.
        Note: For task-specific updates, use update_task() which uses individual files.
        This is mainly for index files (tasks.json) and status.json.
        
        Args:
            filename: JSON filename
            update_func: Function that takes current data and returns updated data
        
        Returns:
            Updated data dictionary
        """
        filepath = self.state_dir / filename
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                # Load current state
                current_data = self.load_json(filename)
                version = current_data.get('version', 0)
                
                # Apply update
                updated_data = update_func(current_data.copy())
                updated_data['version'] = version + 1
                
                # Try to save (with version check)
                try:
                    # Re-read to check version (optimistic concurrency control)
                    if filepath.exists():
                        with open(filepath, 'r', encoding='utf-8') as f:
                            check_data = json.load(f)
                        
                        if check_data.get('version', 0) != version:
                            # Conflict detected, retry
                            if attempt < max_retries - 1:
                                time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                                continue
                            else:
                                raise RuntimeError(f"Failed to update {filename} after {max_retries} attempts (version conflict)")
                    
                    # Save updated data
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(updated_data, f, indent=2, ensure_ascii=False)
                        f.flush()
                        os.fsync(f.fileno())  # Force write to disk
                    
                    return updated_data
                except FileNotFoundError:
                    # File doesn't exist, create it
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(updated_data, f, indent=2, ensure_ascii=False)
                    return updated_data
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                raise
        
        raise RuntimeError(f"Failed to update {filename} after {max_retries} attempts")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return self.load_json("status.json")
    
    def update_status(self, **kwargs) -> None:
        """Update status with given fields."""
        def update(data: Dict[str, Any]) -> Dict[str, Any]:
            data.update(kwargs)
            data['last_updated'] = datetime.now().isoformat()
            return data
        
        self.update_json("status.json", update)
    
    def get_tasks(self) -> Dict[str, Any]:
        """
        Get current tasks index as dictionary (read-only, for backward compatibility).
        This is a lightweight index for ID and metadata only.
        Status and other dynamic fields are stored in individual task files.
        """
        return self.load_json("tasks.json")

    def get_tasks_file(self) -> TasksFile:
        """
        Get current tasks index as TasksFile object (read-only).
        This is a lightweight index for ID and metadata only.
        Status and other dynamic fields are stored in individual task files.

        Returns:
            TasksFile object containing task index entries
        """
        data = self.load_json("tasks.json")
        return TasksFile.from_dict(data)
    
    def _get_task_file_path(self, task_id: str) -> Path:
        """Get path to individual task state file."""
        return self.state_dir / "tasks" / f"{task_id}.json"
    
    def _load_task_state(self, task_id: str) -> Dict[str, Any]:
        """Load individual task state from its own file."""
        task_file = self._get_task_file_path(task_id)
        if task_file.exists():
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def _save_task_state(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Save individual task state to its own file."""
        task_file = self._get_task_file_path(task_id)
        # Ensure directory exists
        task_file.parent.mkdir(parents=True, exist_ok=True)
        # Save directly (no locking needed - each task has its own file)
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk
    
    def add_task(self, task: Union[Task, Dict[str, Any]]) -> str:
        """
        Add a new task.
        Creates both index entry and individual task file.

        Args:
            task: Task object or dictionary

        Returns:
            Task ID
        """
        # Convert dict to Task if needed
        task_dict = task.to_dict() if isinstance(task, Task) else task.copy()

        def update(data: Dict[str, Any]) -> Dict[str, Any]:
            if 'tasks' not in data:
                data['tasks'] = []
            if 'next_task_id' not in data:
                data['next_task_id'] = 1

            task_id = f"task_{data['next_task_id']:03d}"
            task_dict['id'] = task_id
            task_dict['status'] = TaskStatus.PENDING.value
            task_dict['created_at'] = datetime.now().isoformat()

            # Add to index (lightweight metadata only - ID and index info only)
            # Status is stored in individual task files, not in index
            index_entry = TaskIndex(
                id=task_id,
                title=task_dict.get('title', 'No title'),
                priority=TaskPriority.from_string(task_dict.get('priority', 'medium')),
                created_at=task_dict['created_at']
            )
            data['tasks'].append(index_entry.to_dict())
            data['next_task_id'] += 1
            return data

        # Update index
        updated = self.update_json("tasks.json", update)
        task_id = task_dict['id']

        # Save full task data to individual file
        self._save_task_state(task_id, task_dict)

        return task_id
    
    def get_plan(self) -> str:
        """Get current plan."""
        return self.load_text("plan.md")
    
    def save_plan(self, plan: str) -> None:
        """Save plan."""
        self.save_text("plan.md", plan)
    
    def get_pending_tasks(self) -> List[Task]:
        """
        Get all pending tasks.
        Loads full task data from individual files.

        Returns:
            List of Task objects with pending status
        """
        tasks_file = self.get_tasks_file()
        pending = []

        for task_index in tasks_file.tasks:
            task = self.get_task_by_id(task_index.id)
            if task and task.is_pending():
                pending.append(task)

        return pending
    
    def get_all_tasks_from_files(self) -> List[Task]:
        """
        Get all tasks by loading from individual task files.
        This is the source of truth for task status.

        Returns:
            List of all Task objects with their current status from individual files
        """
        tasks_file = self.get_tasks_file()
        all_tasks = []

        for task_index in tasks_file.tasks:
            task = self.get_task_by_id(task_index.id)
            if task:
                all_tasks.append(task)
            else:
                # If individual file doesn't exist, create Task from index data
                all_tasks.append(Task(
                    id=task_index.id,
                    title=task_index.title,
                    priority=task_index.priority,
                    created_at=task_index.created_at,
                ))

        return all_tasks
    
    def get_task_statistics(self) -> TaskStatistics:
        """
        Get task statistics by loading from individual task files.
        This ensures accurate counts based on actual task states.

        Returns:
            TaskStatistics object with counts
        """
        all_tasks = self.get_all_tasks_from_files()
        return TaskStatistics.from_tasks(all_tasks)
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        Get task by ID (loads from individual task file only).
        Index is only used to verify task exists.

        Args:
            task_id: Task ID

        Returns:
            Task object from individual file, or None if not found
        """
        # Check if task exists in index (quick check)
        tasks_file = self.get_tasks_file()
        task_index = tasks_file.get_task_index(task_id)

        if not task_index:
            return None

        # Load from individual task file (source of truth)
        task_state = self._load_task_state(task_id)

        # If task file doesn't exist but is in index, return basic Task from index
        if not task_state:
            return Task(
                id=task_index.id,
                title=task_index.title,
                priority=task_index.priority,
                created_at=task_index.created_at,
            )

        return Task.from_dict(task_state)
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> None:
        """
        Update task with given fields.
        Updates only the individual task file (no conflict with other workers).
        Index (tasks.json) is not updated - it's read-only after task creation.
        
        Args:
            task_id: Task ID
            updates: Fields to update
        """
        # Load current task state
        task_state = self._load_task_state(task_id)
        
        # Apply updates
        task_state.update(updates)
        if "status" in updates:
            task_state["updated_at"] = datetime.now().isoformat()
        
        # Save to individual task file only
        self._save_task_state(task_id, task_state)
    
    def assign_task(self, task_id: str, worker_id: str = "worker") -> None:
        """Assign task to worker."""
        self.update_task(task_id, {
            "status": TaskStatus.IN_PROGRESS.value,
            "assigned_to": worker_id,
            "started_at": datetime.now().isoformat()
        })
    
    def complete_task(self, task_id: str, result: Union[TaskResult, Dict[str, Any]]) -> None:
        """
        Mark task as completed with result.
        Updates only the individual task file (no conflict).

        Args:
            task_id: Task ID
            result: TaskResult object or dictionary with result data
        """
        # Convert to dict if TaskResult
        result_dict = result.to_dict() if isinstance(result, TaskResult) else result

        result_file = f"results/{task_id}.md"
        self.save_text(result_file, result_dict.get("report", ""))

        # Update individual task file only
        self.update_task(task_id, {
            "status": TaskStatus.COMPLETED.value,
            "completed_at": datetime.now().isoformat(),
            "result_file": result_file,
            "result": result_dict  # Store full result in task file
        })
    
    def fail_task(self, task_id: str, error: str) -> None:
        """Mark task as failed."""
        self.update_task(task_id, {
            "status": TaskStatus.FAILED.value,
            "failed_at": datetime.now().isoformat(),
            "error": error
        })

    def recover_in_progress_tasks(self) -> List[str]:
        """
        Recover tasks that are stuck in 'in_progress' state.

        This is typically called at system startup to reset tasks that were
        interrupted due to system crash, user interruption, or other failures.

        Returns:
            List of task IDs that were recovered (reset to 'pending')
        """
        recovered = []
        all_tasks = self.get_all_tasks_from_files()

        for task in all_tasks:
            if task.is_in_progress():
                self.update_task(task.id, {
                    "status": TaskStatus.PENDING.value,
                    "recovered_at": datetime.now().isoformat(),
                    "recovery_reason": "System restart - task was in_progress"
                })
                recovered.append(task.id)

        return recovered
    
    def create_checkpoint(self, checkpoint_name: Optional[str] = None) -> str:
        """
        Create a checkpoint of current state.

        Args:
            checkpoint_name: Optional checkpoint name (default: timestamp-based)

        Returns:
            Checkpoint directory path
        """
        if checkpoint_name is None:
            checkpoint_name = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        checkpoint_dir = self.state_dir / "checkpoints" / checkpoint_name
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Copy all state files
        state_files = ["plan.md", "tasks.json", "status.json"]
        for filename in state_files:
            source = self.state_dir / filename
            if source.exists():
                shutil.copy2(source, checkpoint_dir / filename)

        # Copy individual task files directory
        tasks_source = self.state_dir / "tasks"
        if tasks_source.exists():
            tasks_dest = checkpoint_dir / "tasks"
            if tasks_dest.exists():
                shutil.rmtree(tasks_dest)
            shutil.copytree(tasks_source, tasks_dest)

        # Copy results directory
        results_source = self.state_dir / "results"
        if results_source.exists():
            results_dest = checkpoint_dir / "results"
            if results_dest.exists():
                shutil.rmtree(results_dest)
            shutil.copytree(results_source, results_dest)

        # Save checkpoint metadata
        metadata = CheckpointMetadata(
            checkpoint_name=checkpoint_name,
            created_at=datetime.now().isoformat(),
            files=state_files
        )
        with open(checkpoint_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

        return str(checkpoint_dir)
    
    def restore_checkpoint(self, checkpoint_name: str) -> None:
        """
        Restore state from a checkpoint.
        
        Args:
            checkpoint_name: Name of the checkpoint to restore
        
        Raises:
            StateError: If checkpoint doesn't exist or restore fails
        """
        checkpoint_dir = self.state_dir / "checkpoints" / checkpoint_name
        if not checkpoint_dir.exists():
            from .exceptions import StateError
            raise StateError(f"Checkpoint not found: {checkpoint_name}")
        
        # Load metadata
        metadata_file = checkpoint_dir / "metadata.json"
        if not metadata_file.exists():
            from .exceptions import StateError
            raise StateError(f"Checkpoint metadata not found: {checkpoint_name}")
        
        try:
            # Backup current state before restore
            backup_name = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.create_backup(backup_name)
            
            # Restore state files
            state_files = ["plan.md", "tasks.json", "status.json"]
            for filename in state_files:
                source = checkpoint_dir / filename
                if source.exists():
                    dest = self.state_dir / filename
                    shutil.copy2(source, dest)
            
            # Restore individual task files directory
            tasks_source = checkpoint_dir / "tasks"
            if tasks_source.exists():
                tasks_dest = self.state_dir / "tasks"
                if tasks_dest.exists():
                    shutil.rmtree(tasks_dest)
                shutil.copytree(tasks_source, tasks_dest)
            
            # Restore results directory
            results_source = checkpoint_dir / "results"
            if results_source.exists():
                results_dest = self.state_dir / "results"
                if results_dest.exists():
                    shutil.rmtree(results_dest)
                shutil.copytree(results_source, results_dest)
        except Exception as e:
            from .exceptions import StateError
            raise StateError(f"Failed to restore checkpoint {checkpoint_name}: {e}")
    
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """
        Create a backup of current state.
        
        Args:
            backup_name: Optional backup name (default: timestamp-based)
        
        Returns:
            Backup directory path
        """
        if backup_name is None:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Copy all state files
        state_files = ["plan.md", "tasks.json", "status.json"]
        for filename in state_files:
            source = self.state_dir / filename
            if source.exists():
                shutil.copy2(source, backup_path / filename)
        
        # Copy individual task files directory
        tasks_source = self.state_dir / "tasks"
        if tasks_source.exists():
            tasks_dest = backup_path / "tasks"
            if tasks_dest.exists():
                shutil.rmtree(tasks_dest)
            shutil.copytree(tasks_source, tasks_dest)
        
        # Copy results directory
        results_source = self.state_dir / "results"
        if results_source.exists():
            results_dest = backup_path / "results"
            if results_dest.exists():
                shutil.rmtree(results_dest)
            shutil.copytree(results_source, results_dest)
        
        return str(backup_path)
    
    def list_checkpoints(self) -> List[CheckpointMetadata]:
        """
        List all available checkpoints.

        Returns:
            List of CheckpointMetadata objects
        """
        checkpoints = []
        checkpoints_dir = self.state_dir / "checkpoints"

        if not checkpoints_dir.exists():
            return checkpoints

        for checkpoint_dir in checkpoints_dir.iterdir():
            if checkpoint_dir.is_dir():
                metadata_file = checkpoint_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata_dict = json.load(f)
                            checkpoints.append(CheckpointMetadata.from_dict(metadata_dict))
                    except Exception:
                        # Skip corrupted checkpoints
                        continue

        # Sort by creation time (newest first)
        checkpoints.sort(key=lambda x: x.created_at, reverse=True)
        return checkpoints
    
    def validate_state(self) -> ValidationResult:
        """
        Validate state files for integrity.

        Returns:
            ValidationResult object with validation results
        """
        result = ValidationResult()

        # Check required files
        required_files = ["tasks.json", "status.json"]
        for filename in required_files:
            filepath = self.state_dir / filename
            if not filepath.exists():
                result.add_warning(f"File not found: {filename}")
                continue

            # Try to load JSON
            try:
                data = self.load_json(filename)
                if filename == "tasks.json":
                    # Validate tasks structure
                    if "tasks" not in data:
                        result.add_error("tasks.json missing 'tasks' key")
            except Exception as e:
                from .exceptions import StateCorruptionError
                if isinstance(e, StateCorruptionError):
                    result.add_error(f"Corrupted file: {filename} - {e}")
                else:
                    result.add_error(f"Error loading {filename}: {e}")

        return result
    
    def recover_from_corruption(self) -> bool:
        """
        Attempt to recover from state corruption.

        Returns:
            True if recovery was successful, False otherwise
        """
        # Try to restore from latest checkpoint
        checkpoints = self.list_checkpoints()
        if checkpoints:
            latest_checkpoint = checkpoints[0].checkpoint_name
            try:
                self.restore_checkpoint(latest_checkpoint)
                return True
            except Exception:
                pass

        # Try to restore from latest backup
        backup_dir = self.backup_dir
        if backup_dir.exists():
            backups = sorted(backup_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
            if backups:
                latest_backup = backups[0]
                try:
                    # Copy backup files to state directory
                    for file in latest_backup.iterdir():
                        if file.is_file() and file.suffix in ['.json', '.md']:
                            shutil.copy2(file, self.state_dir / file.name)
                        elif file.is_dir() and file.name == "results":
                            results_dest = self.state_dir / "results"
                            if results_dest.exists():
                                shutil.rmtree(results_dest)
                            shutil.copytree(file, results_dest)
                    return True
                except Exception:
                    pass

        return False
