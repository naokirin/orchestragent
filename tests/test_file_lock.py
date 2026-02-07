"""Tests for FileLockManager class."""

import pytest

from orchestragent.state.file_lock import FileLockManager


class TestFileLockManager:
    """Tests for FileLockManager class."""

    @pytest.fixture
    def lock_manager(self, tmp_path):
        """Create a FileLockManager with temp directory."""
        lock_dir = tmp_path / "locks"
        return FileLockManager(lock_dir=str(lock_dir))

    def test_init(self, tmp_path):
        """Test FileLockManager initialization."""
        lock_dir = tmp_path / "locks"
        manager = FileLockManager(lock_dir=str(lock_dir))
        assert manager.lock_dir == lock_dir
        assert lock_dir.exists()

    def test_init_creates_directory(self, tmp_path):
        """Test that init creates lock directory."""
        lock_dir = tmp_path / "nested" / "locks"
        assert not lock_dir.exists()
        FileLockManager(lock_dir=str(lock_dir))
        assert lock_dir.exists()


class TestAcquireReleaseLock:
    """Tests for acquire_lock and release_lock methods."""

    @pytest.fixture
    def lock_manager(self, tmp_path):
        lock_dir = tmp_path / "locks"
        return FileLockManager(lock_dir=str(lock_dir))

    def test_acquire_lock_success(self, lock_manager):
        """Test acquiring a lock successfully."""
        result = lock_manager.acquire_lock("src/main.py", "task-001")
        assert result is True
        assert "src/main.py" in lock_manager._active_locks or "src_main.py" in str(lock_manager._active_locks)

    def test_acquire_lock_same_file_fails(self, lock_manager):
        """Test acquiring lock on already locked file fails."""
        lock_manager.acquire_lock("src/main.py", "task-001")
        result = lock_manager.acquire_lock("src/main.py", "task-002", timeout=0.5)
        assert result is False

    def test_release_lock(self, lock_manager):
        """Test releasing a lock."""
        lock_manager.acquire_lock("src/main.py", "task-001")
        lock_manager.release_lock("src/main.py")
        assert lock_manager.is_locked("src/main.py") is False

    def test_release_nonexistent_lock(self, lock_manager):
        """Test releasing a lock that doesn't exist."""
        # Should not raise an error
        lock_manager.release_lock("nonexistent.py")

    def test_release_all_locks(self, lock_manager):
        """Test releasing all locks."""
        lock_manager.acquire_lock("file1.py", "task-001")
        lock_manager.acquire_lock("file2.py", "task-001")
        lock_manager.acquire_lock("file3.py", "task-001")

        lock_manager.release_all_locks()

        assert lock_manager.is_locked("file1.py") is False
        assert lock_manager.is_locked("file2.py") is False
        assert lock_manager.is_locked("file3.py") is False


class TestIsLocked:
    """Tests for is_locked method."""

    @pytest.fixture
    def lock_manager(self, tmp_path):
        lock_dir = tmp_path / "locks"
        return FileLockManager(lock_dir=str(lock_dir))

    def test_is_locked_true(self, lock_manager):
        """Test is_locked returns True for locked file."""
        lock_manager.acquire_lock("src/main.py", "task-001")
        assert lock_manager.is_locked("src/main.py") is True

    def test_is_locked_false(self, lock_manager):
        """Test is_locked returns False for unlocked file."""
        assert lock_manager.is_locked("src/main.py") is False

    def test_is_locked_after_release(self, lock_manager):
        """Test is_locked returns False after releasing lock."""
        lock_manager.acquire_lock("src/main.py", "task-001")
        lock_manager.release_lock("src/main.py")
        assert lock_manager.is_locked("src/main.py") is False


class TestGetLockedFiles:
    """Tests for get_locked_files method."""

    @pytest.fixture
    def lock_manager(self, tmp_path):
        lock_dir = tmp_path / "locks"
        return FileLockManager(lock_dir=str(lock_dir))

    def test_get_locked_files_empty(self, lock_manager):
        """Test get_locked_files returns empty list when no locks."""
        result = lock_manager.get_locked_files()
        assert result == []

    def test_get_locked_files(self, lock_manager):
        """Test get_locked_files returns locked files."""
        lock_manager.acquire_lock("file1.py", "task-001")
        lock_manager.acquire_lock("file2.py", "task-002")

        result = lock_manager.get_locked_files()
        assert len(result) == 2
        assert "file1.py" in result
        assert "file2.py" in result


class TestGetLockOwner:
    """Tests for get_lock_owner method."""

    @pytest.fixture
    def lock_manager(self, tmp_path):
        lock_dir = tmp_path / "locks"
        return FileLockManager(lock_dir=str(lock_dir))

    def test_get_lock_owner(self, lock_manager):
        """Test get_lock_owner returns task ID."""
        lock_manager.acquire_lock("src/main.py", "task-001")
        result = lock_manager.get_lock_owner("src/main.py")
        assert result == "task-001"

    def test_get_lock_owner_no_lock(self, lock_manager):
        """Test get_lock_owner returns None when no lock."""
        result = lock_manager.get_lock_owner("src/main.py")
        assert result is None


class TestNormalizePath:
    """Tests for _normalize_path method."""

    @pytest.fixture
    def lock_manager(self, tmp_path):
        lock_dir = tmp_path / "locks"
        return FileLockManager(lock_dir=str(lock_dir))

    def test_normalize_path_strips_slashes(self, lock_manager):
        """Test that leading/trailing slashes are stripped."""
        result = lock_manager._normalize_path("/src/main.py/")
        assert result == "src/main.py"

    def test_normalize_path_replaces_backslashes(self, lock_manager):
        """Test that backslashes are replaced with forward slashes."""
        result = lock_manager._normalize_path("src\\main.py")
        assert result == "src/main.py"


class TestStaleLocks:
    """Tests for stale lock handling."""

    @pytest.fixture
    def lock_manager(self, tmp_path):
        lock_dir = tmp_path / "locks"
        return FileLockManager(lock_dir=str(lock_dir))

    def test_is_lock_stale_false(self, lock_manager):
        """Test that recent lock is not stale."""
        lock_manager.acquire_lock("src/main.py", "task-001")
        lock_file = lock_manager.lock_dir / "src_main.py.lock"
        result = lock_manager._is_lock_stale(lock_file, timeout=30.0)
        assert result is False

    def test_cleanup_stale_locks_none(self, lock_manager):
        """Test cleanup_stale_locks when no stale locks."""
        lock_manager.acquire_lock("src/main.py", "task-001")
        removed = lock_manager.cleanup_stale_locks(timeout=300.0)
        # The lock is recent, so nothing should be removed
        assert removed == 0

    def test_cleanup_stale_locks_no_directory(self, tmp_path):
        """Test cleanup_stale_locks when lock directory doesn't exist."""
        lock_dir = tmp_path / "nonexistent_locks"
        manager = FileLockManager.__new__(FileLockManager)
        manager.lock_dir = lock_dir
        manager._active_locks = set()
        removed = manager.cleanup_stale_locks()
        assert removed == 0


class TestLockFile:
    """Tests for lock file content and format."""

    @pytest.fixture
    def lock_manager(self, tmp_path):
        lock_dir = tmp_path / "locks"
        return FileLockManager(lock_dir=str(lock_dir))

    def test_lock_file_content(self, lock_manager):
        """Test that lock file contains correct metadata."""
        lock_manager.acquire_lock("src/main.py", "task-001")
        lock_file = lock_manager.lock_dir / "src_main.py.lock"

        content = lock_file.read_text()
        assert "task_id=task-001" in content
        assert "filepath=src/main.py" in content
        assert "timestamp=" in content

    def test_multiple_locks_different_files(self, lock_manager):
        """Test acquiring locks on multiple different files."""
        assert lock_manager.acquire_lock("file1.py", "task-001") is True
        assert lock_manager.acquire_lock("file2.py", "task-001") is True
        assert lock_manager.acquire_lock("file3.py", "task-001") is True

        assert lock_manager.is_locked("file1.py") is True
        assert lock_manager.is_locked("file2.py") is True
        assert lock_manager.is_locked("file3.py") is True
