"""Tests for json_parser utility."""

from orchestragent.utils.json_parser import extract_json_from_response


class TestExtractJsonFromResponse:
    """Tests for extract_json_from_response function."""

    def test_empty_response(self):
        """Test with empty response."""
        assert extract_json_from_response("") is None
        assert extract_json_from_response(None) is None

    def test_json_code_block(self):
        """Test extraction from JSON code block."""
        response = """Here is the result:
```json
{"key": "value", "number": 42}
```
That's all."""
        result = extract_json_from_response(response)
        assert result == {"key": "value", "number": 42}

    def test_direct_json_object(self):
        """Test extraction of direct JSON object."""
        response = 'The result is {"status": "ok", "count": 5} and more text.'
        result = extract_json_from_response(response)
        assert result == {"status": "ok", "count": 5}

    def test_nested_json(self):
        """Test extraction of nested JSON."""
        response = """```json
{"outer": {"inner": "value"}, "list": [1, 2, 3]}
```"""
        result = extract_json_from_response(response)
        assert result == {"outer": {"inner": "value"}, "list": [1, 2, 3]}

    def test_multiline_json(self):
        """Test extraction of multiline JSON."""
        response = """```json
{
    "plan_update": "New plan",
    "new_tasks": [
        {"id": "task-001", "title": "First task"}
    ]
}
```"""
        result = extract_json_from_response(response)
        assert result["plan_update"] == "New plan"
        assert len(result["new_tasks"]) == 1

    def test_invalid_json(self):
        """Test with invalid JSON."""
        response = '{"key": invalid}'
        result = extract_json_from_response(response)
        assert result is None

    def test_no_json(self):
        """Test with no JSON in response."""
        response = "This is just plain text without any JSON."
        result = extract_json_from_response(response)
        assert result is None

    def test_prefers_code_block(self):
        """Test that code block is preferred over direct JSON."""
        response = """{"direct": true}
```json
{"block": true}
```"""
        result = extract_json_from_response(response)
        assert result == {"block": True}

    def test_japanese_content(self):
        """Test with Japanese content in JSON."""
        response = """```json
{"message": "タスクが完了しました", "status": "成功"}
```"""
        result = extract_json_from_response(response)
        assert result["message"] == "タスクが完了しました"
        assert result["status"] == "成功"

    def test_json_code_block_invalid_json_falls_back_to_direct(self):
        """When ```json block is invalid, parse fails and tries direct JSON after it."""
        # Avoid { in code block so {"fallback": true} after it matches alone
        response = """```json
not valid json
```
{"fallback": true}"""
        result = extract_json_from_response(response)
        assert result == {"fallback": True}

    def test_json_code_block_invalid_json_no_direct_returns_none(self):
        """When ```json block is invalid and no direct JSON, return None."""
        response = """```json
{broken
```"""
        result = extract_json_from_response(response)
        assert result is None
