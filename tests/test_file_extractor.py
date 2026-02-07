"""Tests for file_extractor utility."""

from orchestragent.utils.file_extractor import extract_file_paths_from_text


class TestExtractFilePathsFromText:
    """Tests for extract_file_paths_from_text."""

    def test_empty_text_returns_empty_list(self):
        """Empty text returns empty list."""
        assert extract_file_paths_from_text("") == []

    def test_explicit_file_mention(self):
        """Extract from 'file: path' pattern."""
        text = "Modify file: src/main.py and file: tests/test_main.py"
        result = extract_file_paths_from_text(text)
        assert "src/main.py" in result
        assert "tests/test_main.py" in result

    def test_quoted_paths(self):
        """Extract from quoted paths."""
        text = 'Update "src/config.json" and `src/settings.yaml`'
        result = extract_file_paths_from_text(text)
        assert "src/config.json" in result
        assert "src/settings.yaml" in result

    def test_common_pattern_disabled_by_default(self):
        """Without include_common_pattern, path-like words are not extracted."""
        text = "Fix bug in src/app.py"
        result = extract_file_paths_from_text(text, include_common_pattern=False)
        assert "src/app.py" not in result

    def test_common_pattern_enabled(self):
        """With include_common_pattern, path-like words are extracted."""
        text = "Fix bug in src/app.py"
        result = extract_file_paths_from_text(text, include_common_pattern=True)
        assert "src/app.py" in result

    def test_deduplicates_and_normalizes(self):
        """Duplicate paths are removed and quotes stripped."""
        text = 'file: "src/main.py" and `src/main.py`'
        result = extract_file_paths_from_text(text)
        assert result.count("src/main.py") == 1
        assert "src/main.py" in result

    def test_extensions_matched(self):
        """Various extensions are matched."""
        text = (
            "file: a.py file: b.ts file: c.js file: d.md "
            '"e.json" `f.yml` g.yaml h.txt i.html j.css'
        )
        result = extract_file_paths_from_text(text, include_common_pattern=False)
        assert "a.py" in result
        assert "b.ts" in result
        assert "e.json" in result
        assert "f.yml" in result
        # g.yaml might be matched by quoted if in backticks; explicit/file: for others
        assert len(result) >= 6
