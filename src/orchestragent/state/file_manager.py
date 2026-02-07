"""File I/O operations for state directory (JSON and text)."""

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, cast


class FileManager:
    """Handles JSON and text file I/O under a state directory."""

    def __init__(self, state_dir: Path) -> None:
        """
        Initialize FileManager.

        Args:
            state_dir: Path to the state directory (must already exist).
        """
        self.state_dir = Path(state_dir)

    def load_json(self, filename: str) -> Dict[str, Any]:
        """
        Load JSON file from state directory.

        Args:
            filename: Relative filename (e.g. "tasks.json", "tasks/task_001.json").

        Returns:
            Parsed data, or empty dict if file does not exist.

        Raises:
            StateCorruptionError: If JSON is corrupted.
        """
        filepath = self.state_dir / filename
        if not filepath.exists():
            return {}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return cast(Dict[str, Any], json.load(f))
        except json.JSONDecodeError as e:
            from orchestragent.core.exceptions import StateCorruptionError

            raise StateCorruptionError(filename, e)

    def save_json(
        self, filename: str, data: Dict[str, Any], *, sync: bool = False
    ) -> None:
        """
        Save dictionary to JSON file in state directory.

        Args:
            filename: Relative filename.
            data: Data to serialize.
            sync: If True, flush and fsync after write (for durability).
        """
        filepath = self.state_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            if sync:
                f.flush()
                os.fsync(f.fileno())

    def load_text(self, filename: str) -> str:
        """
        Load text file from state directory.

        Args:
            filename: Relative filename.

        Returns:
            File content, or empty string if file does not exist.
        """
        filepath = self.state_dir / filename
        if not filepath.exists():
            return ""

        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def save_text(self, filename: str, content: str) -> None:
        """
        Save string to text file in state directory.

        Args:
            filename: Relative filename.
            content: Content to write.
        """
        filepath = self.state_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def update_json(
        self,
        filename: str,
        update_func: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Update JSON file using a function (optimistic concurrency).

        Args:
            filename: Relative filename.
            update_func: Function that takes current data and returns updated data.

        Returns:
            Updated data dictionary.

        Raises:
            RuntimeError: If update fails after retries.
        """
        filepath = self.state_dir / filename
        max_retries = 5

        for attempt in range(max_retries):
            try:
                current_data = self.load_json(filename)
                version = current_data.get("version", 0)

                updated_data = update_func(current_data.copy())
                updated_data["version"] = version + 1

                try:
                    if filepath.exists():
                        with open(filepath, "r", encoding="utf-8") as f:
                            check_data = json.load(f)
                        if check_data.get("version", 0) != version:
                            if attempt < max_retries - 1:
                                time.sleep(0.1 * (2**attempt))
                                continue
                            raise RuntimeError(
                                f"Failed to update {filename} after {max_retries} attempts (version conflict)"
                            )

                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(updated_data, f, indent=2, ensure_ascii=False)
                        f.flush()
                        os.fsync(f.fileno())
                    return updated_data
                except FileNotFoundError:
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(updated_data, f, indent=2, ensure_ascii=False)
                    return updated_data
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                raise

        raise RuntimeError(f"Failed to update {filename} after {max_retries} attempts")
