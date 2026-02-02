"""Tests for llm.factory (LLMClientFactory)."""

import pytest

from orchestragent.llm.factory import LLMClientFactory
from orchestragent.llm.client import LLMClient
from orchestragent.llm.cursor_cli import CursorCLIClient


class TestLLMClientFactoryCreate:
    """Tests for LLMClientFactory.create."""

    def test_create_cursor_cli_default_kwargs(self):
        """backend='cursor_cli' で CursorCLIClient が返る。"""
        client = LLMClientFactory.create("cursor_cli")
        assert isinstance(client, LLMClient)
        assert isinstance(client, CursorCLIClient)

    def test_create_cursor_cli_with_project_root(self):
        """cursor_cli で project_root を渡せる。"""
        client = LLMClientFactory.create("cursor_cli", project_root=".")
        assert isinstance(client, CursorCLIClient)
        assert client.project_root.resolve() == client.project_root

    def test_create_cursor_cli_with_output_format(self):
        """cursor_cli で output_format を渡せる。"""
        client = LLMClientFactory.create("cursor_cli", output_format="markdown")
        assert isinstance(client, CursorCLIClient)
        assert client.output_format == "markdown"

    def test_create_unknown_backend_raises_value_error(self):
        """異常系: 未対応の backend で ValueError。"""
        with pytest.raises(ValueError) as exc_info:
            LLMClientFactory.create("unknown_backend")
        assert "Unknown backend" in str(exc_info.value)
        assert "cursor_cli" in str(exc_info.value)

    def test_create_empty_backend_raises(self):
        """異常系: 空文字の backend でも ValueError。"""
        with pytest.raises(ValueError):
            LLMClientFactory.create("")
