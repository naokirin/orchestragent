"""State management utilities for the agent system."""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime


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
        
        # Ensure subdirectories exist
        (self.state_dir / "results").mkdir(exist_ok=True)
        (self.state_dir / "checkpoints").mkdir(exist_ok=True)
        
        # Backup directory
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
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
        Update JSON file using a function (optimistic concurrency control).
        
        Args:
            filename: JSON filename
            update_func: Function that takes current data and returns updated data
        
        Returns:
            Updated data dictionary
        """
        max_retries = 5
        for attempt in range(max_retries):
            # Load current state
            current_data = self.load_json(filename)
            version = current_data.get('version', 0)
            
            # Apply update
            updated_data = update_func(current_data)
            updated_data['version'] = version + 1
            
            # Try to save (with version check)
            filepath = self.state_dir / filename
            try:
                # Re-read to check version
                with open(filepath, 'r', encoding='utf-8') as f:
                    check_data = json.load(f)
                
                if check_data.get('version', 0) != version:
                    # Conflict detected, retry
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        raise RuntimeError(f"Failed to update {filename} after {max_retries} attempts")
                
                # Save updated data
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(updated_data, f, indent=2, ensure_ascii=False)
                
                return updated_data
            except FileNotFoundError:
                # File doesn't exist, create it
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(updated_data, f, indent=2, ensure_ascii=False)
                return updated_data
        
        raise RuntimeError(f"Failed to update {filename}")
    
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
        """Get current tasks."""
        return self.load_json("tasks.json")
    
    def add_task(self, task: Dict[str, Any]) -> str:
        """
        Add a new task.
        
        Args:
            task: Task dictionary
        
        Returns:
            Task ID
        """
        def update(data: Dict[str, Any]) -> Dict[str, Any]:
            if 'tasks' not in data:
                data['tasks'] = []
            if 'next_task_id' not in data:
                data['next_task_id'] = 1
            
            task_id = f"task_{data['next_task_id']:03d}"
            task['id'] = task_id
            task['status'] = 'pending'
            task['created_at'] = datetime.now().isoformat()
            
            data['tasks'].append(task)
            data['next_task_id'] += 1
            return data
        
        updated = self.update_json("tasks.json", update)
        return task['id']
    
    def get_plan(self) -> str:
        """Get current plan."""
        return self.load_text("plan.md")
    
    def save_plan(self, plan: str) -> None:
        """Save plan."""
        self.save_text("plan.md", plan)
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get all pending tasks."""
        tasks = self.get_tasks()
        return [t for t in tasks.get("tasks", []) if t.get("status") == "pending"]
    
    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID."""
        tasks = self.get_tasks()
        for task in tasks.get("tasks", []):
            if task.get("id") == task_id:
                return task
        return None
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> None:
        """Update task with given fields."""
        def update(data: Dict[str, Any]) -> Dict[str, Any]:
            for task in data.get("tasks", []):
                if task.get("id") == task_id:
                    task.update(updates)
                    if "status" in updates:
                        task["updated_at"] = datetime.now().isoformat()
                    break
            return data
        
        self.update_json("tasks.json", update)
    
    def assign_task(self, task_id: str, worker_id: str = "worker") -> None:
        """Assign task to worker."""
        self.update_task(task_id, {
            "status": "in_progress",
            "assigned_to": worker_id,
            "started_at": datetime.now().isoformat()
        })
    
    def complete_task(self, task_id: str, result: Dict[str, Any]) -> None:
        """Mark task as completed with result."""
        result_file = f"results/{task_id}.md"
        self.save_text(result_file, result.get("report", ""))
        
        self.update_task(task_id, {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "result_file": result_file
        })
    
    def fail_task(self, task_id: str, error: str) -> None:
        """Mark task as failed."""
        self.update_task(task_id, {
            "status": "failed",
            "failed_at": datetime.now().isoformat(),
            "error": error
        })
    
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
        
        # Copy results directory
        results_source = self.state_dir / "results"
        if results_source.exists():
            results_dest = checkpoint_dir / "results"
            if results_dest.exists():
                shutil.rmtree(results_dest)
            shutil.copytree(results_source, results_dest)
        
        # Save checkpoint metadata
        metadata = {
            "checkpoint_name": checkpoint_name,
            "created_at": datetime.now().isoformat(),
            "files": state_files
        }
        with open(checkpoint_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
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
        
        # Copy results directory
        results_source = self.state_dir / "results"
        if results_source.exists():
            results_dest = backup_path / "results"
            if results_dest.exists():
                shutil.rmtree(results_dest)
            shutil.copytree(results_source, results_dest)
        
        return str(backup_path)
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        List all available checkpoints.
        
        Returns:
            List of checkpoint metadata dictionaries
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
                            metadata = json.load(f)
                            checkpoints.append(metadata)
                    except Exception:
                        # Skip corrupted checkpoints
                        continue
        
        # Sort by creation time (newest first)
        checkpoints.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return checkpoints
    
    def validate_state(self) -> Dict[str, Any]:
        """
        Validate state files for integrity.
        
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required files
        required_files = ["tasks.json", "status.json"]
        for filename in required_files:
            filepath = self.state_dir / filename
            if not filepath.exists():
                validation_result["warnings"].append(f"File not found: {filename}")
                continue
            
            # Try to load JSON
            try:
                data = self.load_json(filename)
                if filename == "tasks.json":
                    # Validate tasks structure
                    if "tasks" not in data:
                        validation_result["errors"].append("tasks.json missing 'tasks' key")
                        validation_result["valid"] = False
            except Exception as e:
                from .exceptions import StateCorruptionError
                if isinstance(e, StateCorruptionError):
                    validation_result["errors"].append(f"Corrupted file: {filename} - {e}")
                else:
                    validation_result["errors"].append(f"Error loading {filename}: {e}")
                validation_result["valid"] = False
        
        return validation_result
    
    def recover_from_corruption(self) -> bool:
        """
        Attempt to recover from state corruption.
        
        Returns:
            True if recovery was successful, False otherwise
        """
        # Try to restore from latest checkpoint
        checkpoints = self.list_checkpoints()
        if checkpoints:
            latest_checkpoint = checkpoints[0]["checkpoint_name"]
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
