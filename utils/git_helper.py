"""Git operations helper for Intent tracking."""

import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path


class GitHelper:
    """Helper class for Git operations."""

    def __init__(self, repo_path: str = "."):
        """
        Initialize GitHelper.

        Args:
            repo_path: Path to Git repository
        """
        self.repo_path = Path(repo_path).resolve()

    def is_git_repo(self) -> bool:
        """
        Check if the path is a Git repository.

        Returns:
            True if Git repository
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--is-inside-work-tree'],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_commit_info(self, commit_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get commit information.

        Args:
            commit_hash: Git commit hash (full or short)

        Returns:
            Commit info dictionary or None
        """
        try:
            # Get commit details
            result = subprocess.run(
                ['git', 'show', '--no-patch', '--format=%H%n%s%n%b%n%ai%n%an', commit_hash],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
                timeout=10
            )

            if result.returncode != 0:
                return None

            lines = result.stdout.strip().split('\n')
            if len(lines) < 4:
                return None

            return {
                "hash": lines[0],
                "message": lines[1],
                "body": '\n'.join(lines[2:-2]).strip() if len(lines) > 4 else "",
                "timestamp": lines[-2],
                "author": lines[-1],
            }
        except Exception:
            return None

    def get_commit_diff(self, commit_hash: str, max_lines: int = 1000) -> Optional[str]:
        """
        Get diff for a commit.

        Args:
            commit_hash: Git commit hash
            max_lines: Maximum lines to return (default: 1000)

        Returns:
            Diff string or None
        """
        try:
            result = subprocess.run(
                ['git', 'show', '--format=', commit_hash],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
                timeout=30
            )

            if result.returncode != 0:
                return None

            diff = result.stdout
            lines = diff.split('\n')

            if len(lines) > max_lines:
                truncated = '\n'.join(lines[:max_lines])
                return truncated + f"\n\n... ({len(lines) - max_lines} more lines truncated)"

            return diff
        except Exception:
            return None

    def get_commit_files(self, commit_hash: str) -> List[str]:
        """
        Get list of files changed in a commit.

        Args:
            commit_hash: Git commit hash

        Returns:
            List of file paths
        """
        try:
            result = subprocess.run(
                ['git', 'show', '--name-only', '--format=', commit_hash],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
                timeout=10
            )

            if result.returncode != 0:
                return []

            return [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
        except Exception:
            return []

    def get_recent_commits(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent commits.

        Args:
            count: Number of commits to retrieve

        Returns:
            List of commit info dictionaries
        """
        try:
            result = subprocess.run(
                ['git', 'log', f'-{count}', '--format=%H|%s|%ai|%an'],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
                timeout=10
            )

            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|', 3)
                if len(parts) >= 4:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "timestamp": parts[2],
                        "author": parts[3],
                    })

            return commits
        except Exception:
            return []

    def get_commits_for_task(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get commits mentioning a task ID in message.

        Args:
            task_id: Task ID to search for

        Returns:
            List of commit info dictionaries
        """
        try:
            result = subprocess.run(
                ['git', 'log', '--all', f'--grep={task_id}', '--format=%H|%s|%ai|%an'],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
                timeout=10
            )

            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|', 3)
                if len(parts) >= 4:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "timestamp": parts[2],
                        "author": parts[3],
                    })

            return commits
        except Exception:
            return []

    def get_diff_between_commits(
        self,
        commit1: str,
        commit2: str,
        max_lines: int = 1000
    ) -> Optional[str]:
        """
        Get diff between two commits.

        Args:
            commit1: First commit hash
            commit2: Second commit hash
            max_lines: Maximum lines to return

        Returns:
            Diff string or None
        """
        try:
            result = subprocess.run(
                ['git', 'diff', commit1, commit2],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
                timeout=30
            )

            if result.returncode != 0:
                return None

            diff = result.stdout
            lines = diff.split('\n')

            if len(lines) > max_lines:
                truncated = '\n'.join(lines[:max_lines])
                return truncated + f"\n\n... ({len(lines) - max_lines} more lines truncated)"

            return diff
        except Exception:
            return None

    def get_file_at_commit(self, commit_hash: str, file_path: str) -> Optional[str]:
        """
        Get file content at a specific commit.

        Args:
            commit_hash: Git commit hash
            file_path: Path to file

        Returns:
            File content or None
        """
        try:
            result = subprocess.run(
                ['git', 'show', f'{commit_hash}:{file_path}'],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
                timeout=10
            )

            if result.returncode != 0:
                return None

            return result.stdout
        except Exception:
            return None

    def get_current_branch(self) -> Optional[str]:
        """
        Get current branch name.

        Returns:
            Branch name or None
        """
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
                timeout=5
            )

            if result.returncode != 0:
                return None

            return result.stdout.strip()
        except Exception:
            return None

    def get_head_commit(self) -> Optional[str]:
        """
        Get HEAD commit hash.

        Returns:
            Commit hash or None
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
                timeout=5
            )

            if result.returncode != 0:
                return None

            return result.stdout.strip()
        except Exception:
            return None
