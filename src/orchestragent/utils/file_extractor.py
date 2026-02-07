"""File path extraction utilities from task descriptions and text."""

import re
from typing import List

# Patterns shared by planner, task_scheduler, and worker
_EXPLICIT_PATTERN = re.compile(
    r"file:\s*([^\s\n]+\.(?:py|ts|js|md|json|yml|yaml|txt|html|css))",
    re.IGNORECASE,
)
_QUOTED_PATTERN = re.compile(
    r'["\'`]([^\'"`]+\.(?:py|ts|js|md|json|yml|yaml|txt|html|css))["\'`]',
    re.IGNORECASE,
)
_COMMON_PATTERN = re.compile(
    r"([\w\-_/]+\.(?:py|ts|js|md|json|yml|yaml|txt|html|css))",
)


def extract_file_paths_from_text(
    text: str,
    *,
    include_common_pattern: bool = False,
) -> List[str]:
    """
    Extract file paths from text (e.g. task description).

    Tries:
    1. Explicit "file: path/to/file.py"
    2. Quoted paths '"path/to/file.py"', '`src/main.ts`'
    3. If include_common_pattern is True, common path-like strings

    Args:
        text: Source text (e.g. task description)
        include_common_pattern: Whether to also match path-like words (e.g. src/main.py)

    Returns:
        Normalized, deduplicated list of file paths
    """
    if not text:
        return []

    files: List[str] = []

    for match in _EXPLICIT_PATTERN.finditer(text):
        files.append(match.group(1))

    for match in _QUOTED_PATTERN.finditer(text):
        files.append(match.group(1))

    if include_common_pattern:
        for match in _COMMON_PATTERN.finditer(text):
            files.append(match.group(1))

    # Normalize and deduplicate
    normalized: List[str] = []
    seen = set()
    for filepath in files:
        normalized_path = filepath.strip().strip("\"'`")
        if normalized_path and normalized_path not in seen:
            normalized.append(normalized_path)
            seen.add(normalized_path)

    return normalized
