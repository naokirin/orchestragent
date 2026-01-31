"""Intent information parser from Worker response."""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime


class IntentParser:
    """Parse Intent information from Worker agent response."""

    # Regular expression pattern definitions
    INTENT_SECTION_PATTERN = re.compile(
        r'## 変更意図 \(Intent\)(.*?)(?=## 実装内容|## 変更したファイル|$)',
        re.DOTALL
    )
    GOAL_PATTERN = re.compile(r'### 目標 \(Goal\)\s*\n(.+?)(?=###|$)', re.DOTALL)
    RATIONALE_PATTERN = re.compile(r'### 理由 \(Rationale\)\s*\n(.+?)(?=###|$)', re.DOTALL)
    EXPECTED_CHANGE_PATTERN = re.compile(r'### 期待される変更 \(Expected Change\)\s*\n(.+?)(?=###|$)', re.DOTALL)
    NON_GOALS_PATTERN = re.compile(r'### 非目標 \(Non-Goals\)\s*\n(.+?)(?=###|$)', re.DOTALL)
    RISK_PATTERN = re.compile(r'### リスク \(Risk\)\s*\n(.+?)(?=###|##|$)', re.DOTALL)
    # Support formats: "コミットハッシュ: xxx" and "- **コミットハッシュ:** xxx"
    COMMIT_HASH_PATTERN = re.compile(r'[-*]*\s*\**コミットハッシュ\**[:\s]+([a-f0-9]+)', re.IGNORECASE)
    COMMIT_MSG_PATTERN = re.compile(r'[-*]*\s*\**コミットメッセージ\**[:\s]+(.+)', re.MULTILINE)
    RELATED_ADR_PATTERN = re.compile(r'関連ADR[:\s]+(ADR-)?(\d+)', re.IGNORECASE)

    @classmethod
    def parse(cls, response: str, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Parse Worker response and extract Intent information.

        Args:
            response: Worker agent response text
            task_id: Task ID

        Returns:
            Intent dictionary or None if parsing fails
        """
        intent_match = cls.INTENT_SECTION_PATTERN.search(response)
        if not intent_match:
            # Try alternative parsing without explicit Intent section
            return cls._parse_fallback(response, task_id)

        intent_section = intent_match.group(1)

        # Extract each component
        goal = cls._extract_single(cls.GOAL_PATTERN, intent_section)
        rationale = cls._extract_single(cls.RATIONALE_PATTERN, intent_section)
        expected_change = cls._extract_list(cls.EXPECTED_CHANGE_PATTERN, intent_section)
        non_goals = cls._extract_list(cls.NON_GOALS_PATTERN, intent_section)
        risk = cls._extract_list(cls.RISK_PATTERN, intent_section)

        # Extract commit info from full response
        commit_hash = cls._extract_single(cls.COMMIT_HASH_PATTERN, response)
        commit_message = cls._extract_single(cls.COMMIT_MSG_PATTERN, response)

        # Extract related ADR
        adr_match = cls.RELATED_ADR_PATTERN.search(response)
        related_adr = adr_match.group(2) if adr_match else None

        now = datetime.now().isoformat()

        return {
            "version": 1,
            "task_id": task_id,
            "created_at": now,
            "updated_at": now,
            "intent": {
                "goal": goal,
                "rationale": rationale,
                "expected_change": expected_change,
                "non_goals": non_goals,
                "risk": risk,
            },
            "commits": [
                {
                    "hash": commit_hash,
                    "message": commit_message,
                    "timestamp": now,
                }
            ] if commit_hash else [],
            "related_adr": related_adr,
        }

    @classmethod
    def _parse_fallback(cls, response: str, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Fallback parsing when no explicit Intent section is found.
        Tries to extract information from the general response structure.

        Args:
            response: Worker agent response text
            task_id: Task ID

        Returns:
            Intent dictionary with partial data or None
        """
        # Extract commit info
        commit_hash = cls._extract_single(cls.COMMIT_HASH_PATTERN, response)
        commit_message = cls._extract_single(cls.COMMIT_MSG_PATTERN, response)

        # If we have at least commit info, create a minimal intent record
        if not commit_hash:
            return None

        now = datetime.now().isoformat()

        # Try to extract goal from "実装内容" section
        impl_match = re.search(r'## 実装内容\s*\n(.+?)(?=##|$)', response, re.DOTALL)
        goal = impl_match.group(1).strip()[:200] if impl_match else None

        return {
            "version": 1,
            "task_id": task_id,
            "created_at": now,
            "updated_at": now,
            "intent": {
                "goal": goal,
                "rationale": None,
                "expected_change": [],
                "non_goals": [],
                "risk": [],
            },
            "commits": [
                {
                    "hash": commit_hash,
                    "message": commit_message,
                    "timestamp": now,
                }
            ],
            "related_adr": None,
        }

    @classmethod
    def _extract_single(cls, pattern: re.Pattern, text: str) -> Optional[str]:
        """Extract single value from pattern match."""
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def _extract_list(cls, pattern: re.Pattern, text: str) -> List[str]:
        """Extract list items from pattern match (markdown list)."""
        match = pattern.search(text)
        if not match:
            return []

        content = match.group(1)
        # Parse markdown list items (both - and * markers)
        items = re.findall(r'^[-*]\s+(.+)$', content, re.MULTILINE)
        return [item.strip() for item in items if item.strip()]

    @classmethod
    def has_intent_section(cls, response: str) -> bool:
        """
        Check if response contains an Intent section.

        Args:
            response: Worker agent response text

        Returns:
            True if Intent section exists
        """
        return cls.INTENT_SECTION_PATTERN.search(response) is not None
