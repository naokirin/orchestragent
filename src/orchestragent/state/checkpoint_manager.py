"""Checkpoint and backup operations for state directory."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from orchestragent.models import CheckpointMetadata


class CheckpointManager:
    """Handles checkpoint creation/restore and backups (state_dir and backup_dir)."""

    def __init__(self, state_dir: Path, backup_dir: Path) -> None:
        """
        Initialize CheckpointManager.

        Args:
            state_dir: Path to the state directory.
            backup_dir: Path to the backup directory.
        """
        self.state_dir = Path(state_dir)
        self.backup_dir = Path(backup_dir)

    def create_checkpoint(self, checkpoint_name: Optional[str] = None) -> str:
        """
        Create a checkpoint of current state.

        Args:
            checkpoint_name: Optional name (default: timestamp-based).

        Returns:
            Checkpoint directory path as string.
        """
        if checkpoint_name is None:
            checkpoint_name = (
                f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

        checkpoint_dir = self.state_dir / "checkpoints" / checkpoint_name
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        state_files = ["plan.md", "tasks.json", "status.json"]
        for filename in state_files:
            source = self.state_dir / filename
            if source.exists():
                shutil.copy2(source, checkpoint_dir / filename)

        tasks_source = self.state_dir / "tasks"
        if tasks_source.exists():
            tasks_dest = checkpoint_dir / "tasks"
            if tasks_dest.exists():
                shutil.rmtree(tasks_dest)
            shutil.copytree(tasks_source, tasks_dest)

        results_source = self.state_dir / "results"
        if results_source.exists():
            results_dest = checkpoint_dir / "results"
            if results_dest.exists():
                shutil.rmtree(results_dest)
            shutil.copytree(results_source, results_dest)

        metadata = CheckpointMetadata(
            checkpoint_name=checkpoint_name,
            created_at=datetime.now().isoformat(),
            files=state_files,
        )
        with open(
            checkpoint_dir / "metadata.json", "w", encoding="utf-8"
        ) as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

        return str(checkpoint_dir)

    def restore_checkpoint(self, checkpoint_name: str) -> None:
        """
        Restore state from a checkpoint.

        Args:
            checkpoint_name: Name of the checkpoint to restore.

        Raises:
            StateError: If checkpoint is missing or restore fails.
        """
        from orchestragent.core.exceptions import StateError

        checkpoint_dir = self.state_dir / "checkpoints" / checkpoint_name
        if not checkpoint_dir.exists():
            raise StateError(f"Checkpoint not found: {checkpoint_name}")

        metadata_file = checkpoint_dir / "metadata.json"
        if not metadata_file.exists():
            raise StateError(
                f"Checkpoint metadata not found: {checkpoint_name}"
            )

        try:
            backup_name = (
                f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            self.create_backup(backup_name)

            state_files = ["plan.md", "tasks.json", "status.json"]
            for filename in state_files:
                source = checkpoint_dir / filename
                if source.exists():
                    dest = self.state_dir / filename
                    shutil.copy2(source, dest)

            tasks_source = checkpoint_dir / "tasks"
            if tasks_source.exists():
                tasks_dest = self.state_dir / "tasks"
                if tasks_dest.exists():
                    shutil.rmtree(tasks_dest)
                shutil.copytree(tasks_source, tasks_dest)

            results_source = checkpoint_dir / "results"
            if results_source.exists():
                results_dest = self.state_dir / "results"
                if results_dest.exists():
                    shutil.rmtree(results_dest)
                shutil.copytree(results_source, results_dest)
        except Exception as e:
            raise StateError(
                f"Failed to restore checkpoint {checkpoint_name}: {e}"
            ) from e

    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """
        Create a backup of current state.

        Args:
            backup_name: Optional name (default: timestamp-based).

        Returns:
            Backup directory path as string.
        """
        if backup_name is None:
            backup_name = (
                f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        state_files = ["plan.md", "tasks.json", "status.json"]
        for filename in state_files:
            source = self.state_dir / filename
            if source.exists():
                shutil.copy2(source, backup_path / filename)

        tasks_source = self.state_dir / "tasks"
        if tasks_source.exists():
            tasks_dest = backup_path / "tasks"
            if tasks_dest.exists():
                shutil.rmtree(tasks_dest)
            shutil.copytree(tasks_source, tasks_dest)

        results_source = self.state_dir / "results"
        if results_source.exists():
            results_dest = backup_path / "results"
            if results_dest.exists():
                shutil.rmtree(results_dest)
            shutil.copytree(results_source, results_dest)

        return str(backup_path)

    def list_checkpoints(self) -> List[CheckpointMetadata]:
        """List all available checkpoints (newest first)."""
        checkpoints: List[CheckpointMetadata] = []
        checkpoints_dir = self.state_dir / "checkpoints"

        if not checkpoints_dir.exists():
            return checkpoints

        for checkpoint_dir in checkpoints_dir.iterdir():
            if checkpoint_dir.is_dir():
                metadata_file = checkpoint_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(
                            metadata_file, "r", encoding="utf-8"
                        ) as f:
                            metadata_dict = json.load(f)
                            checkpoints.append(
                                CheckpointMetadata.from_dict(metadata_dict)
                            )
                    except Exception:
                        continue

        checkpoints.sort(key=lambda x: x.created_at, reverse=True)
        return checkpoints
