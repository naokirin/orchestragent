"""Tests for state.ValidationManager."""

import pytest
from unittest.mock import MagicMock

from orchestragent.state.validation_manager import ValidationManager


class TestValidationManagerInit:
    """Tests for ValidationManager initialization."""

    def test_init_stores_dependencies(self, temp_dir):
        """Hold state_dir, file_manager, checkpoint_manager."""
        fm = MagicMock()
        cm = MagicMock()
        vm = ValidationManager(temp_dir, fm, cm)
        assert vm.state_dir == temp_dir
        assert vm._file is fm
        assert vm._checkpoint is cm


class TestValidateState:
    """Tests for validate_state."""

    @pytest.fixture
    def file_manager(self):
        m = MagicMock()
        return m

    @pytest.fixture
    def checkpoint_manager(self):
        return MagicMock()

    @pytest.fixture
    def validation_manager(self, temp_dir, file_manager, checkpoint_manager):
        return ValidationManager(temp_dir, file_manager, checkpoint_manager)

    def test_validate_state_file_not_found_adds_warning(self, validation_manager, temp_dir):
        """Add warning when file not found (boundary)."""
        # tasks.json / status.json missing
        result = validation_manager.validate_state()
        assert result.valid is True
        assert any("not found" in w.lower() for w in result.warnings)
        assert len(result.warnings) >= 1

    def test_validate_state_tasks_json_missing_tasks_key_adds_error(self, validation_manager, temp_dir):
        """Add error when tasks.json has no 'tasks' key."""
        (temp_dir / "tasks.json").write_text("{}")
        (temp_dir / "status.json").write_text("{}")

        def load_side_effect(name):
            if name == "tasks.json":
                return {}
            if name == "status.json":
                return {}
            return {}

        validation_manager._file.load_json.side_effect = load_side_effect
        result = validation_manager.validate_state()
        assert result.valid is False
        assert any("tasks" in e and "key" in e.lower() for e in result.errors)

    def test_validate_state_corruption_error_adds_error(self, validation_manager, temp_dir):
        """StateCorruptionError adds error."""
        from orchestragent.core.exceptions import StateCorruptionError

        (temp_dir / "tasks.json").touch()
        validation_manager._file.load_json.side_effect = StateCorruptionError("corrupt")
        result = validation_manager.validate_state()
        assert result.valid is False
        assert any("corrupt" in e.lower() or "corrupted" in e.lower() for e in result.errors)

    def test_validate_state_generic_exception_adds_error(self, validation_manager, temp_dir):
        """Other exceptions also add error."""
        (temp_dir / "tasks.json").touch()
        validation_manager._file.load_json.side_effect = RuntimeError("load failed")
        result = validation_manager.validate_state()
        assert result.valid is False
        assert any("load failed" in e or "error" in e.lower() for e in result.errors)

    def test_validate_state_all_ok(self, validation_manager, temp_dir):
        """When all files exist and valid, valid=True."""
        (temp_dir / "tasks.json").touch()
        (temp_dir / "status.json").touch()

        def load_side_effect(name):
            if name == "tasks.json":
                return {"tasks": [], "next_task_id": 1}
            return {}

        validation_manager._file.load_json.side_effect = load_side_effect
        result = validation_manager.validate_state()
        assert result.valid is True
        assert len(result.errors) == 0


class TestRecoverFromCorruption:
    """Tests for recover_from_corruption."""

    @pytest.fixture
    def file_manager(self):
        return MagicMock()

    @pytest.fixture
    def checkpoint_manager(self):
        return MagicMock()

    @pytest.fixture
    def validation_manager(self, temp_dir, file_manager, checkpoint_manager):
        return ValidationManager(temp_dir, file_manager, checkpoint_manager)

    def test_recover_from_checkpoint_success(self, validation_manager):
        """Return True when checkpoint exists and restore succeeds."""
        validation_manager._checkpoint.list_checkpoints.return_value = [
            MagicMock(checkpoint_name="latest")
        ]
        validation_manager._checkpoint.restore_checkpoint.return_value = None
        assert validation_manager.recover_from_corruption() is True
        validation_manager._checkpoint.restore_checkpoint.assert_called_once_with("latest")

    def test_recover_from_checkpoint_restore_raises_tries_backup(self, validation_manager, temp_dir):
        """When checkpoint restore fails, try backup."""
        validation_manager._checkpoint.list_checkpoints.return_value = [
            MagicMock(checkpoint_name="latest")
        ]
        validation_manager._checkpoint.restore_checkpoint.side_effect = RuntimeError("restore failed")
        validation_manager._checkpoint.backup_dir = temp_dir / "backups"
        validation_manager._checkpoint.backup_dir.mkdir(parents=True, exist_ok=True)
        # Backup dir exists but is empty
        assert validation_manager.recover_from_corruption() is False

    def test_recover_no_checkpoint_no_backup_returns_false(self, validation_manager, temp_dir):
        """Return False when no checkpoint and no backup (boundary)."""
        validation_manager._checkpoint.list_checkpoints.return_value = []
        validation_manager._checkpoint.backup_dir = temp_dir / "backups"
        assert validation_manager.recover_from_corruption() is False
