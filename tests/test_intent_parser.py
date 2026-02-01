"""Tests for IntentParser class."""

import pytest
from datetime import datetime

from orchestragent.tracking.intent_parser import IntentParser


class TestIntentParser:
    """Tests for IntentParser class."""

    def test_parse_full_intent_section(self):
        """Test parsing response with full Intent section."""
        response = """
## 変更意図 (Intent)

### 目標 (Goal)
Add user authentication feature

### 理由 (Rationale)
Security requirement from client

### 期待される変更 (Expected Change)
- Add login endpoint
- Add logout endpoint
- Add session management

### 非目標 (Non-Goals)
- OAuth integration
- Social login

### リスク (Risk)
- Session handling complexity

## 実装内容
Implementation details here

コミットハッシュ: abc123def
コミットメッセージ: Add authentication
"""
        result = IntentParser.parse(response, "task-001")

        assert result is not None
        assert result["task_id"] == "task-001"
        assert result["version"] == 1
        assert "authentication" in result["intent"]["goal"].lower()
        assert "security" in result["intent"]["rationale"].lower()
        assert len(result["intent"]["expected_change"]) == 3
        assert "login" in result["intent"]["expected_change"][0].lower()
        assert len(result["intent"]["non_goals"]) == 2
        assert len(result["intent"]["risk"]) == 1
        assert len(result["commits"]) == 1
        assert result["commits"][0]["hash"] == "abc123def"

    def test_parse_with_multiple_commits(self):
        """Test parsing response with multiple commits."""
        response = """
## 変更意図 (Intent)

### 目標 (Goal)
Refactor database layer

## 実装内容

コミットハッシュ: abc123
コミットメッセージ: First commit

コミットハッシュ: def456
コミットメッセージ: Second commit

コミットハッシュ: fed789
コミットメッセージ: Third commit
"""
        result = IntentParser.parse(response, "task-002")

        assert result is not None
        assert len(result["commits"]) == 3
        assert result["commits"][0]["hash"] == "abc123"
        assert result["commits"][1]["hash"] == "def456"
        assert result["commits"][2]["hash"] == "fed789"

    def test_parse_with_related_adr(self):
        """Test parsing response with related ADR reference."""
        response = """
## 変更意図 (Intent)

### 目標 (Goal)
Implement caching

関連ADR: ADR-005

コミットハッシュ: abc123
コミットメッセージ: Add caching
"""
        result = IntentParser.parse(response, "task-003")

        assert result is not None
        assert result["related_adr"] == "005"

    def test_parse_fallback_no_intent_section(self):
        """Test fallback parsing when no Intent section."""
        response = """
## 実装内容
Fixed the bug in the authentication module

コミットハッシュ: abc123
コミットメッセージ: Fix auth bug
"""
        result = IntentParser.parse(response, "task-004")

        assert result is not None
        assert result["task_id"] == "task-004"
        assert len(result["commits"]) == 1
        assert result["intent"]["goal"] is not None
        assert "authentication" in result["intent"]["goal"].lower() or "bug" in result["intent"]["goal"].lower()

    def test_parse_fallback_no_commits(self):
        """Test fallback returns None when no commits found."""
        response = """
## 実装内容
Just some notes, no actual commits
"""
        result = IntentParser.parse(response, "task-005")

        assert result is None

    def test_parse_new_adr_section(self):
        """Test parsing response with new ADR section."""
        response = """
## 変更意図 (Intent)

### 目標 (Goal)
New architecture decision

## 新規ADR

### タイトル
Use PostgreSQL for persistence

### コンテキスト
We need a reliable database solution

### 決定
We will use PostgreSQL

### 理由
Best fit for our use case

### 結果
Migration required from SQLite

コミットハッシュ: abc123
コミットメッセージ: Switch to PostgreSQL
"""
        result = IntentParser.parse(response, "task-006")

        assert result is not None
        assert result["adr_to_create"] is not None
        assert "PostgreSQL" in result["adr_to_create"]["title"]
        assert "reliable" in result["adr_to_create"]["context"]
        assert "PostgreSQL" in result["adr_to_create"]["decision"]
        assert "fit" in result["adr_to_create"]["rationale"]
        assert "Migration" in result["adr_to_create"]["consequences"]

    def test_parse_new_adr_section_none(self):
        """Test parsing response with 'なし' in new ADR section."""
        response = """
## 変更意図 (Intent)

### 目標 (Goal)
Minor fix

## 新規ADR

### タイトル
なし

コミットハッシュ: abc123
コミットメッセージ: Minor fix
"""
        result = IntentParser.parse(response, "task-007")

        assert result is not None
        assert result["adr_to_create"] is None

    def test_has_intent_section_true(self):
        """Test has_intent_section returns True when section exists."""
        response = """
## 変更意図 (Intent)

### 目標 (Goal)
Some goal
"""
        assert IntentParser.has_intent_section(response) is True

    def test_has_intent_section_false(self):
        """Test has_intent_section returns False when section missing."""
        response = """
## 実装内容
Just implementation details
"""
        assert IntentParser.has_intent_section(response) is False

    def test_parse_commit_format_variations(self):
        """Test parsing various commit format variations."""
        response = """
## 変更意図 (Intent)

### 目標 (Goal)
Test various formats

- **コミットハッシュ:** `abc123`
- **コミットメッセージ:** `First message`

* **コミットハッシュ:** def456
* **コミットメッセージ:** Second message
"""
        result = IntentParser.parse(response, "task-008")

        assert result is not None
        assert len(result["commits"]) >= 1
        # Check at least first commit is parsed
        assert result["commits"][0]["hash"] in ["abc123", "def456"]

    def test_parse_timestamps_set(self):
        """Test that timestamps are set in parsed result."""
        response = """
## 変更意図 (Intent)

### 目標 (Goal)
Test timestamps

コミットハッシュ: abc123
コミットメッセージ: Test
"""
        result = IntentParser.parse(response, "task-009")

        assert result is not None
        assert "created_at" in result
        assert "updated_at" in result
        # Verify they are valid ISO format timestamps
        datetime.fromisoformat(result["created_at"])
        datetime.fromisoformat(result["updated_at"])


class TestExtractMethods:
    """Tests for internal extraction methods."""

    def test_extract_single(self):
        """Test _extract_single method."""
        import re
        pattern = re.compile(r'Name: (.+)')
        text = "Name: John Doe"
        result = IntentParser._extract_single(pattern, text)
        assert result == "John Doe"

    def test_extract_single_no_match(self):
        """Test _extract_single returns None when no match."""
        import re
        pattern = re.compile(r'Name: (.+)')
        text = "No name here"
        result = IntentParser._extract_single(pattern, text)
        assert result is None

    def test_extract_list(self):
        """Test _extract_list method."""
        import re
        pattern = re.compile(r'Items:\n(.+?)(?=\n\n|$)', re.DOTALL)
        text = """Items:
- First item
- Second item
- Third item

Other content
"""
        result = IntentParser._extract_list(pattern, text)
        assert len(result) == 3
        assert "First item" in result
        assert "Second item" in result
        assert "Third item" in result

    def test_extract_list_no_match(self):
        """Test _extract_list returns empty list when no match."""
        import re
        pattern = re.compile(r'Items:\n(.+?)(?=\n\n|$)', re.DOTALL)
        text = "No items section"
        result = IntentParser._extract_list(pattern, text)
        assert result == []

    def test_extract_all(self):
        """Test _extract_all method."""
        import re
        pattern = re.compile(r'@(\w+)')
        text = "Hello @alice and @bob and @charlie"
        result = IntentParser._extract_all(pattern, text)
        assert len(result) == 3
        assert "alice" in result
        assert "bob" in result
        assert "charlie" in result

    def test_extract_commits(self):
        """Test _extract_commits method."""
        response = """
コミットハッシュ: abc123
コミットメッセージ: First commit

コミットハッシュ: def456
コミットメッセージ: Second commit
"""
        result = IntentParser._extract_commits(response)
        assert len(result) == 2
        assert result[0]["hash"] == "abc123"
        assert result[0]["message"] == "First commit"
        assert result[1]["hash"] == "def456"
        assert result[1]["message"] == "Second commit"
        # Each commit should have a timestamp
        for commit in result:
            assert "timestamp" in commit
