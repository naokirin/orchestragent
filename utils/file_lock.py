"""File locking utilities for preventing concurrent edits."""

import os
import time
import fcntl
from pathlib import Path
from typing import Set, Optional, List
from datetime import datetime
from .exceptions import StateError


class FileLockManager:
    """Manages file locks to prevent concurrent edits by multiple workers."""
    
    def __init__(self, lock_dir: str = "state/locks"):
        """
        Initialize file lock manager.
        
        Args:
            lock_dir: Directory for lock files
        """
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self._active_locks: Set[str] = set()  # Track locks in this process
    
    def acquire_lock(self, filepath: str, task_id: str, timeout: float = 30.0) -> bool:
        """
        Acquire a lock on a file.
        
        Args:
            filepath: Path to the file to lock (relative to project root)
            task_id: Task ID requesting the lock
            timeout: Maximum time to wait for lock (seconds)
        
        Returns:
            True if lock was acquired, False if timeout
        """
        # Normalize filepath
        normalized_path = self._normalize_path(filepath)
        lock_file = self.lock_dir / f"{normalized_path.replace('/', '_')}.lock"
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try to create and lock the file
                lock_file.parent.mkdir(parents=True, exist_ok=True)
                lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                
                # Write lock metadata
                lock_info = f"task_id={task_id}\ntimestamp={datetime.now().isoformat()}\nfilepath={filepath}\n"
                os.write(lock_fd, lock_info.encode('utf-8'))
                os.close(lock_fd)
                
                # Track in this process
                self._active_locks.add(normalized_path)
                return True
            except FileExistsError:
                # Lock file exists, check if it's stale
                if self._is_lock_stale(lock_file, timeout):
                    # Remove stale lock
                    try:
                        lock_file.unlink()
                    except Exception:
                        pass
                    continue
                # Wait a bit before retrying
                time.sleep(0.1)
            except Exception as e:
                # Other errors
                return False
        
        return False
    
    def release_lock(self, filepath: str) -> None:
        """
        Release a lock on a file.
        
        Args:
            filepath: Path to the file to unlock
        """
        normalized_path = self._normalize_path(filepath)
        lock_file = self.lock_dir / f"{normalized_path.replace('/', '_')}.lock"
        
        try:
            if lock_file.exists():
                lock_file.unlink()
            self._active_locks.discard(normalized_path)
        except Exception:
            pass
    
    def release_all_locks(self) -> None:
        """Release all locks held by this process."""
        for filepath in list(self._active_locks):
            self.release_lock(filepath)
    
    def is_locked(self, filepath: str) -> bool:
        """
        Check if a file is currently locked.
        
        Args:
            filepath: Path to the file to check
        
        Returns:
            True if file is locked
        """
        normalized_path = self._normalize_path(filepath)
        lock_file = self.lock_dir / f"{normalized_path.replace('/', '_')}.lock"
        return lock_file.exists() and not self._is_lock_stale(lock_file, timeout=30.0)
    
    def get_locked_files(self) -> List[str]:
        """
        Get list of currently locked files.
        
        Returns:
            List of locked file paths
        """
        locked_files = []
        if not self.lock_dir.exists():
            return locked_files
        
        for lock_file in self.lock_dir.glob("*.lock"):
            try:
                with open(lock_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract filepath from lock file
                    for line in content.split('\n'):
                        if line.startswith('filepath='):
                            filepath = line.split('=', 1)[1]
                            if not self._is_lock_stale(lock_file, timeout=30.0):
                                locked_files.append(filepath)
            except Exception:
                pass
        
        return locked_files
    
    def get_lock_owner(self, filepath: str) -> Optional[str]:
        """
        Get the task ID that owns the lock on a file.
        
        Args:
            filepath: Path to the file
        
        Returns:
            Task ID if locked, None otherwise
        """
        normalized_path = self._normalize_path(filepath)
        lock_file = self.lock_dir / f"{normalized_path.replace('/', '_')}.lock"
        
        if not lock_file.exists():
            return None
        
        try:
            with open(lock_file, 'r', encoding='utf-8') as f:
                content = f.read()
                for line in content.split('\n'):
                    if line.startswith('task_id='):
                        return line.split('=', 1)[1]
        except Exception:
            pass
        
        return None
    
    def _normalize_path(self, filepath: str) -> str:
        """Normalize file path for consistent locking."""
        # Remove leading/trailing slashes and normalize
        normalized = filepath.strip('/').replace('\\', '/')
        return normalized
    
    def _is_lock_stale(self, lock_file: Path, timeout: float) -> bool:
        """
        Check if a lock file is stale (older than timeout).
        
        Args:
            lock_file: Path to lock file
            timeout: Timeout in seconds
        
        Returns:
            True if lock is stale
        """
        try:
            # Check file modification time
            mtime = lock_file.stat().st_mtime
            age = time.time() - mtime
            return age > timeout
        except Exception:
            return True
    
    def cleanup_stale_locks(self, timeout: float = 300.0) -> int:
        """
        Clean up stale lock files.
        
        Args:
            timeout: Consider locks older than this as stale (seconds)
        
        Returns:
            Number of stale locks removed
        """
        if not self.lock_dir.exists():
            return 0
        
        removed = 0
        for lock_file in self.lock_dir.glob("*.lock"):
            if self._is_lock_stale(lock_file, timeout):
                try:
                    lock_file.unlink()
                    removed += 1
                except Exception:
                    pass
        
        return removed
