"""Tests for core.environment (container detection)."""

from unittest.mock import patch, mock_open


from orchestragent.core.environment import is_running_in_container


class TestIsRunningInContainer:
    """Tests for is_running_in_container."""

    def test_returns_true_when_dockerenv_exists(self):
        """Return True when /.dockerenv exists (boundary: inside Docker)."""
        with patch("os.path.exists") as m_exists:
            m_exists.side_effect = lambda p: p == "/.dockerenv"
            assert is_running_in_container() is True
            m_exists.assert_any_call("/.dockerenv")

    def test_returns_true_when_cgroup_contains_docker(self):
        """Return True when cgroup contains 'docker' even without /.dockerenv."""
        with patch("os.path.exists", return_value=False):
            with patch(
                "builtins.open",
                mock_open(read_data="0::/docker/abc123\n"),
            ):
                assert is_running_in_container() is True

    def test_returns_false_when_cgroup_has_no_docker(self):
        """Return False when cgroup does not contain 'docker'."""
        with patch("os.path.exists", return_value=False):
            with patch(
                "builtins.open",
                mock_open(read_data="0::/user.slice\n"),
            ):
                assert is_running_in_container() is False

    def test_returns_false_when_cgroup_file_not_found(self):
        """When /proc/self/cgroup not found (open raises), return False."""
        with patch("os.path.exists", return_value=False):
            with patch("builtins.open", side_effect=FileNotFoundError):
                assert is_running_in_container() is False

    def test_returns_false_when_cgroup_read_raises(self):
        """When cgroup read raises, return False."""
        with patch("os.path.exists", return_value=False):
            with patch("builtins.open", side_effect=PermissionError):
                assert is_running_in_container() is False
