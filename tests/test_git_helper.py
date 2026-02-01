"""Tests for GitHelper class."""

import pytest
from unittest.mock import patch, MagicMock
import subprocess

from orchestragent.tracking.git_helper import GitHelper


class TestGitHelper:
    """Tests for GitHelper class."""

    @pytest.fixture
    def git_helper(self, tmp_path):
        """Create GitHelper with temp path."""
        return GitHelper(repo_path=str(tmp_path))

    def test_init(self, tmp_path):
        """Test GitHelper initialization."""
        helper = GitHelper(repo_path=str(tmp_path))
        assert helper.repo_path == tmp_path

    def test_init_default_path(self):
        """Test GitHelper default path is current directory."""
        helper = GitHelper()
        assert helper.repo_path.is_absolute()


class TestIsGitRepo:
    """Tests for is_git_repo method."""

    @pytest.fixture
    def git_helper(self, tmp_path):
        return GitHelper(repo_path=str(tmp_path))

    @patch("subprocess.run")
    def test_is_git_repo_true(self, mock_run, git_helper):
        """Test is_git_repo returns True for git repo."""
        mock_run.return_value = MagicMock(returncode=0)
        assert git_helper.is_git_repo() is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_is_git_repo_false(self, mock_run, git_helper):
        """Test is_git_repo returns False for non-git repo."""
        mock_run.return_value = MagicMock(returncode=128)
        assert git_helper.is_git_repo() is False

    @patch("subprocess.run")
    def test_is_git_repo_exception(self, mock_run, git_helper):
        """Test is_git_repo returns False on exception."""
        mock_run.side_effect = subprocess.SubprocessError("Error")
        assert git_helper.is_git_repo() is False


class TestGetCommitInfo:
    """Tests for get_commit_info method."""

    @pytest.fixture
    def git_helper(self, tmp_path):
        return GitHelper(repo_path=str(tmp_path))

    @patch("subprocess.run")
    def test_get_commit_info_success(self, mock_run, git_helper):
        """Test get_commit_info returns commit details."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123def456\nCommit message\nBody text\n2024-01-15 10:00:00 +0900\nJohn Doe"
        )
        result = git_helper.get_commit_info("abc123")
        assert result is not None
        assert result["hash"] == "abc123def456"
        assert result["message"] == "Commit message"
        assert result["author"] == "John Doe"

    @patch("subprocess.run")
    def test_get_commit_info_not_found(self, mock_run, git_helper):
        """Test get_commit_info returns None for non-existent commit."""
        mock_run.return_value = MagicMock(returncode=128)
        result = git_helper.get_commit_info("nonexistent")
        assert result is None

    @patch("subprocess.run")
    def test_get_commit_info_exception(self, mock_run, git_helper):
        """Test get_commit_info returns None on exception."""
        mock_run.side_effect = subprocess.SubprocessError("Error")
        result = git_helper.get_commit_info("abc123")
        assert result is None

    @patch("subprocess.run")
    def test_get_commit_info_insufficient_lines(self, mock_run, git_helper):
        """Test get_commit_info returns None with insufficient output."""
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\ndef")
        result = git_helper.get_commit_info("abc123")
        assert result is None


class TestGetCommitDiff:
    """Tests for get_commit_diff method."""

    @pytest.fixture
    def git_helper(self, tmp_path):
        return GitHelper(repo_path=str(tmp_path))

    @patch("subprocess.run")
    def test_get_commit_diff_success(self, mock_run, git_helper):
        """Test get_commit_diff returns diff."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="diff --git a/file.py b/file.py\n+added line"
        )
        result = git_helper.get_commit_diff("abc123")
        assert result is not None
        assert "+added line" in result

    @patch("subprocess.run")
    def test_get_commit_diff_truncated(self, mock_run, git_helper):
        """Test get_commit_diff truncates long diffs."""
        long_diff = "\n".join([f"line {i}" for i in range(2000)])
        mock_run.return_value = MagicMock(returncode=0, stdout=long_diff)
        result = git_helper.get_commit_diff("abc123", max_lines=100)
        assert result is not None
        assert "truncated" in result

    @patch("subprocess.run")
    def test_get_commit_diff_not_found(self, mock_run, git_helper):
        """Test get_commit_diff returns None for non-existent commit."""
        mock_run.return_value = MagicMock(returncode=128)
        result = git_helper.get_commit_diff("nonexistent")
        assert result is None


class TestGetCommitFiles:
    """Tests for get_commit_files method."""

    @pytest.fixture
    def git_helper(self, tmp_path):
        return GitHelper(repo_path=str(tmp_path))

    @patch("subprocess.run")
    def test_get_commit_files_success(self, mock_run, git_helper):
        """Test get_commit_files returns file list."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="src/main.py\ntests/test_main.py\nREADME.md"
        )
        result = git_helper.get_commit_files("abc123")
        assert len(result) == 3
        assert "src/main.py" in result
        assert "README.md" in result

    @patch("subprocess.run")
    def test_get_commit_files_empty(self, mock_run, git_helper):
        """Test get_commit_files returns empty list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        result = git_helper.get_commit_files("abc123")
        assert result == []

    @patch("subprocess.run")
    def test_get_commit_files_error(self, mock_run, git_helper):
        """Test get_commit_files returns empty list on error."""
        mock_run.return_value = MagicMock(returncode=128)
        result = git_helper.get_commit_files("nonexistent")
        assert result == []


class TestGetRecentCommits:
    """Tests for get_recent_commits method."""

    @pytest.fixture
    def git_helper(self, tmp_path):
        return GitHelper(repo_path=str(tmp_path))

    @patch("subprocess.run")
    def test_get_recent_commits_success(self, mock_run, git_helper):
        """Test get_recent_commits returns commit list."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123|First commit|2024-01-15 10:00:00|John\ndef456|Second commit|2024-01-14 10:00:00|Jane"
        )
        result = git_helper.get_recent_commits(count=2)
        assert len(result) == 2
        assert result[0]["hash"] == "abc123"
        assert result[0]["message"] == "First commit"
        assert result[1]["hash"] == "def456"

    @patch("subprocess.run")
    def test_get_recent_commits_empty(self, mock_run, git_helper):
        """Test get_recent_commits returns empty list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        result = git_helper.get_recent_commits()
        assert result == []

    @patch("subprocess.run")
    def test_get_recent_commits_error(self, mock_run, git_helper):
        """Test get_recent_commits returns empty list on error."""
        mock_run.return_value = MagicMock(returncode=128)
        result = git_helper.get_recent_commits()
        assert result == []


class TestGetCommitsForTask:
    """Tests for get_commits_for_task method."""

    @pytest.fixture
    def git_helper(self, tmp_path):
        return GitHelper(repo_path=str(tmp_path))

    @patch("subprocess.run")
    def test_get_commits_for_task_success(self, mock_run, git_helper):
        """Test get_commits_for_task returns commits."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123|task-001: Fix bug|2024-01-15|John"
        )
        result = git_helper.get_commits_for_task("task-001")
        assert len(result) == 1
        assert "task-001" in result[0]["message"]

    @patch("subprocess.run")
    def test_get_commits_for_task_none(self, mock_run, git_helper):
        """Test get_commits_for_task returns empty for no matches."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        result = git_helper.get_commits_for_task("task-999")
        assert result == []


class TestGetDiffBetweenCommits:
    """Tests for get_diff_between_commits method."""

    @pytest.fixture
    def git_helper(self, tmp_path):
        return GitHelper(repo_path=str(tmp_path))

    @patch("subprocess.run")
    def test_get_diff_between_commits_success(self, mock_run, git_helper):
        """Test get_diff_between_commits returns diff."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="diff --git a/file.py b/file.py\n-old\n+new"
        )
        result = git_helper.get_diff_between_commits("abc123", "def456")
        assert result is not None
        assert "-old" in result
        assert "+new" in result

    @patch("subprocess.run")
    def test_get_diff_between_commits_error(self, mock_run, git_helper):
        """Test get_diff_between_commits returns None on error."""
        mock_run.return_value = MagicMock(returncode=128)
        result = git_helper.get_diff_between_commits("abc", "def")
        assert result is None


class TestGetFileAtCommit:
    """Tests for get_file_at_commit method."""

    @pytest.fixture
    def git_helper(self, tmp_path):
        return GitHelper(repo_path=str(tmp_path))

    @patch("subprocess.run")
    def test_get_file_at_commit_success(self, mock_run, git_helper):
        """Test get_file_at_commit returns file content."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="def hello():\n    print('hello')"
        )
        result = git_helper.get_file_at_commit("abc123", "src/main.py")
        assert result is not None
        assert "def hello" in result

    @patch("subprocess.run")
    def test_get_file_at_commit_not_found(self, mock_run, git_helper):
        """Test get_file_at_commit returns None for missing file."""
        mock_run.return_value = MagicMock(returncode=128)
        result = git_helper.get_file_at_commit("abc123", "nonexistent.py")
        assert result is None


class TestGetCurrentBranch:
    """Tests for get_current_branch method."""

    @pytest.fixture
    def git_helper(self, tmp_path):
        return GitHelper(repo_path=str(tmp_path))

    @patch("subprocess.run")
    def test_get_current_branch_success(self, mock_run, git_helper):
        """Test get_current_branch returns branch name."""
        mock_run.return_value = MagicMock(returncode=0, stdout="main\n")
        result = git_helper.get_current_branch()
        assert result == "main"

    @patch("subprocess.run")
    def test_get_current_branch_error(self, mock_run, git_helper):
        """Test get_current_branch returns None on error."""
        mock_run.return_value = MagicMock(returncode=128)
        result = git_helper.get_current_branch()
        assert result is None


class TestGetHeadCommit:
    """Tests for get_head_commit method."""

    @pytest.fixture
    def git_helper(self, tmp_path):
        return GitHelper(repo_path=str(tmp_path))

    @patch("subprocess.run")
    def test_get_head_commit_success(self, mock_run, git_helper):
        """Test get_head_commit returns commit hash."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123def456789\n"
        )
        result = git_helper.get_head_commit()
        assert result == "abc123def456789"

    @patch("subprocess.run")
    def test_get_head_commit_error(self, mock_run, git_helper):
        """Test get_head_commit returns None on error."""
        mock_run.return_value = MagicMock(returncode=128)
        result = git_helper.get_head_commit()
        assert result is None
