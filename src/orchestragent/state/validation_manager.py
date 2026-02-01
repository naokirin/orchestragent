"""State validation and recovery from corruption."""

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from orchestragent.models import ValidationResult

if TYPE_CHECKING:
    from .checkpoint_manager import CheckpointManager
    from .file_manager import FileManager


class ValidationManager:
    """Validates state integrity and attempts recovery from corruption."""

    def __init__(
        self,
        state_dir: Path,
        file_manager: "FileManager",
        checkpoint_manager: "CheckpointManager",
    ) -> None:
        """
        Initialize ValidationManager.

        Args:
            state_dir: Path to the state directory.
            file_manager: FileManager for loading JSON (validation).
            checkpoint_manager: CheckpointManager for list/restore (recovery).
        """
        self.state_dir = Path(state_dir)
        self._file = file_manager
        self._checkpoint = checkpoint_manager

    def validate_state(self) -> ValidationResult:
        """
        Validate state files for integrity.

        Returns:
            ValidationResult with errors and warnings.
        """
        from orchestragent.core.exceptions import StateCorruptionError

        result = ValidationResult()

        for filename in ["tasks.json", "status.json"]:
            filepath = self.state_dir / filename
            if not filepath.exists():
                result.add_warning(f"File not found: {filename}")
                continue

            try:
                data = self._file.load_json(filename)
                if filename == "tasks.json" and "tasks" not in data:
                    result.add_error("tasks.json missing 'tasks' key")
            except StateCorruptionError as e:
                result.add_error(f"Corrupted file: {filename} - {e}")
            except Exception as e:
                result.add_error(f"Error loading {filename}: {e}")

        return result

    def recover_from_corruption(self) -> bool:
        """
        Attempt to recover from state corruption (checkpoint then backup).

        Returns:
            True if recovery succeeded, False otherwise.
        """
        checkpoints = self._checkpoint.list_checkpoints()
        if checkpoints:
            latest = checkpoints[0].checkpoint_name
            try:
                self._checkpoint.restore_checkpoint(latest)
                return True
            except Exception:
                pass

        backup_dir = self._checkpoint.backup_dir
        if backup_dir.exists():
            backups = sorted(
                backup_dir.iterdir(),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )
            if backups:
                latest_backup = backups[0]
                try:
                    for f in latest_backup.iterdir():
                        if f.is_file() and f.suffix in [".json", ".md"]:
                            shutil.copy2(f, self.state_dir / f.name)
                        elif f.is_dir() and f.name == "results":
                            results_dest = self.state_dir / "results"
                            if results_dest.exists():
                                shutil.rmtree(results_dest)
                            shutil.copytree(f, results_dest)
                    return True
                except Exception:
                    pass

        return False
