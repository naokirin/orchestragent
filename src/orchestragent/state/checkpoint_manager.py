"""Checkpoint and backup operations for state directory."""

import io
import json
import logging
import shutil
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from orchestragent.models import CheckpointMetadata

logger = logging.getLogger(__name__)

# Archive extension used when compressing old checkpoints
CHECKPOINT_ARCHIVE_SUFFIX = ".tar.gz"


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
            checkpoint_name = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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
        with open(checkpoint_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

        return str(checkpoint_dir)

    def restore_checkpoint(self, checkpoint_name: str) -> None:
        """
        Restore state from a checkpoint.
        If the checkpoint is a directory, restore as-is. If it is a .tar.gz archive,
        extract to a temp dir, restore, then remove the temp dir.

        Args:
            checkpoint_name: Name of the checkpoint to restore.

        Raises:
            StateError: If checkpoint is missing or restore fails.
        """
        from orchestragent.core.exceptions import StateError

        checkpoints_dir = self.state_dir / "checkpoints"
        checkpoint_dir = checkpoints_dir / checkpoint_name
        archive_path = checkpoints_dir / (checkpoint_name + CHECKPOINT_ARCHIVE_SUFFIX)

        if checkpoint_dir.exists():
            source_dir = checkpoint_dir
        elif archive_path.exists():
            # Extract compressed archive to a temp dir, then restore
            with tempfile.TemporaryDirectory(
                prefix="checkpoint_restore_", dir=str(checkpoints_dir)
            ) as tmpdir:
                with tarfile.open(archive_path, "r:gz") as tar:
                    # Python 3.12+ uses filter='data' for safe extraction
                    if sys.version_info >= (3, 12):
                        tar.extractall(tmpdir, filter="data")
                    else:
                        tar.extractall(tmpdir)
                # After extraction, expect a subdirectory named checkpoint_name
                extracted = Path(tmpdir) / checkpoint_name
                if not extracted.exists():
                    source_dir = Path(tmpdir)
                else:
                    source_dir = extracted
                metadata_file = source_dir / "metadata.json"
                if not metadata_file.exists():
                    raise StateError(
                        f"Checkpoint metadata not found: {checkpoint_name}"
                    )
                backup_name = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.create_backup(backup_name)
                self._restore_from_dir(source_dir)
            return
        else:
            raise StateError(f"Checkpoint not found: {checkpoint_name}")

        metadata_file = source_dir / "metadata.json"
        if not metadata_file.exists():
            raise StateError(f"Checkpoint metadata not found: {checkpoint_name}")

        try:
            backup_name = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.create_backup(backup_name)
            self._restore_from_dir(source_dir)
        except Exception as e:
            raise StateError(
                f"Failed to restore checkpoint {checkpoint_name}: {e}"
            ) from e

    def _restore_from_dir(self, checkpoint_dir: Path) -> None:
        """Checkpoint ディレクトリの内容を state_dir に復元する。"""
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

    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """
        Create a backup of current state.

        Args:
            backup_name: Optional name (default: timestamp-based).

        Returns:
            Backup directory path as string.
        """
        if backup_name is None:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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
        """List all available checkpoints (newest first). Includes both directories and .tar.gz archives."""
        checkpoints: List[CheckpointMetadata] = []
        checkpoints_dir = self.state_dir / "checkpoints"

        if not checkpoints_dir.exists():
            return checkpoints

        for path in checkpoints_dir.iterdir():
            if path.is_dir():
                metadata_file = path / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            metadata_dict = json.load(f)
                            checkpoints.append(
                                CheckpointMetadata.from_dict(metadata_dict)
                            )
                    except (json.JSONDecodeError, KeyError, OSError) as e:
                        logger.debug(
                            "Failed to read checkpoint metadata %s: %s", path.name, e
                        )
                        continue
            elif path.suffix == ".gz" and path.name.endswith(CHECKPOINT_ARCHIVE_SUFFIX):
                # Compressed archive: read metadata.json from inside the archive
                stem = path.name[: -len(CHECKPOINT_ARCHIVE_SUFFIX)]
                try:
                    with tarfile.open(path, "r:gz") as tar:
                        meta_member = f"{stem}/metadata.json"
                        try:
                            member = tar.getmember(meta_member)
                        except KeyError:
                            logger.debug("Metadata not found in archive %s", path.name)
                            continue
                        fp = tar.extractfile(member)
                        if fp is None:
                            continue
                        metadata_dict = json.load(
                            io.TextIOWrapper(fp, encoding="utf-8")
                        )
                        checkpoints.append(CheckpointMetadata.from_dict(metadata_dict))
                except (tarfile.TarError, json.JSONDecodeError, KeyError, OSError) as e:
                    logger.debug(
                        "Failed to read compressed checkpoint %s: %s", path.name, e
                    )
                    continue

        checkpoints.sort(key=lambda x: x.created_at, reverse=True)
        return checkpoints

    def compress_old_checkpoints(self, keep_latest_n: int = 1) -> int:
        """
        Compress checkpoints older than the latest keep_latest_n into .tar.gz and remove
        the original directories to reduce disk usage.

        Args:
            keep_latest_n: Number of latest checkpoints to leave uncompressed (1 = only the latest).

        Returns:
            Number of checkpoints compressed.
        """
        checkpoints_dir = self.state_dir / "checkpoints"
        if not checkpoints_dir.exists():
            return 0

        listed = self.list_checkpoints()
        # Compress checkpoints older than keep_latest_n that exist as directories
        to_compress = listed[keep_latest_n:]
        compressed_count = 0

        for meta in to_compress:
            name = meta.checkpoint_name
            checkpoint_dir = checkpoints_dir / name
            archive_path = checkpoints_dir / (name + CHECKPOINT_ARCHIVE_SUFFIX)
            if not checkpoint_dir.is_dir():
                continue
            if archive_path.exists():
                # Skip if archive already exists (avoid double compression)
                continue
            try:
                with tarfile.open(archive_path, "w:gz") as tar:
                    for item in checkpoint_dir.rglob("*"):
                        if item.is_file():
                            arcname = (
                                name + "/" + item.relative_to(checkpoint_dir).as_posix()
                            )
                            tar.add(item, arcname=arcname)
                shutil.rmtree(checkpoint_dir)
                compressed_count += 1
            except Exception:
                if archive_path.exists():
                    archive_path.unlink()
                raise

        return compressed_count
