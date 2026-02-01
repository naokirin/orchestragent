"""JSON parsing utilities for LLM responses."""

import json
import re
from typing import Any, Dict, Optional


def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response.

    Tries to extract JSON from:
    1. Code block with ```json ... ```
    2. Direct JSON object { ... }

    Args:
        response: LLM response string

    Returns:
        Parsed JSON dictionary, or None if extraction failed
    """
    if not response:
        return None

    # Try to extract from JSON code block
    json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find JSON object directly
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None
