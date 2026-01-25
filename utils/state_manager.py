"""State management utilities for the agent system."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime


class StateManager:
    """Manages state files for the agent system."""
    
    def __init__(self, state_dir: str = "state"):
        """
        Initialize StateManager.
        
        Args:
            state_dir: Directory path for state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure subdirectories exist
        (self.state_dir / "results").mkdir(exist_ok=True)
    
    def load_json(self, filename: str) -> Dict[str, Any]:
        """
        Load JSON file from state directory.
        
        Args:
            filename: JSON filename (e.g., "tasks.json")
        
        Returns:
            Dictionary containing the JSON data, or empty dict if file doesn't exist
        """
        filepath = self.state_dir / filename
        if not filepath.exists():
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filepath}: {e}")
    
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
