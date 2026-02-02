"""Tests for core.environment (container detection)."""

import pytest
from unittest.mock import patch, mock_open


from orchestragent.core.environment import is_running_in_container


class TestIsRunningInContainer:
    """Tests for is_running_in_container."""

    def test_returns_true_when_dockerenv_exists(self):
        """/.dockerenv が存在する場合は True を返す（境界: Docker 内）。"""
        with patch("os.path.exists") as m_exists:
            m_exists.side_effect = lambda p: p == "/.dockerenv"
            assert is_running_in_container() is True
            m_exists.assert_any_call("/.dockerenv")

    def test_returns_true_when_cgroup_contains_docker(self):
        """/.dockerenv がなくても cgroup に 'docker' があれば True。"""
        with patch("os.path.exists", return_value=False):
            with patch(
                "builtins.open",
                mock_open(read_data="0::/docker/abc123\n"),
            ):
                assert is_running_in_container() is True

    def test_returns_false_when_cgroup_has_no_docker(self):
        """cgroup に 'docker' が含まれない場合は False。"""
        with patch("os.path.exists", return_value=False):
            with patch(
                "builtins.open",
                mock_open(read_data="0::/user.slice\n"),
            ):
                assert is_running_in_container() is False

    def test_returns_false_when_cgroup_file_not_found(self):
        """異常系: /proc/self/cgroup が存在しない（open が例外）場合は False。"""
        with patch("os.path.exists", return_value=False):
            with patch("builtins.open", side_effect=FileNotFoundError):
                assert is_running_in_container() is False

    def test_returns_false_when_cgroup_read_raises(self):
        """異常系: cgroup 読み取りで例外が発生した場合は False。"""
        with patch("os.path.exists", return_value=False):
            with patch("builtins.open", side_effect=PermissionError):
                assert is_running_in_container() is False
