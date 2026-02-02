# -*- coding: utf-8 -*-
"""Intent information parser from Worker response."""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime


class IntentParser:
    """Parse Intent information from Worker agent response."""

    # Regular expression pattern definitions (English and Japanese headers)
    INTENT_SECTION_PATTERN = re.compile(
        r'## (?:Intent|変更意図\s*\(Intent\))\s*\n(.*?)(?=## (?:Implementation|実装内容)|## (?:Changed Files|変更したファイル)|$)',
        re.DOTALL | re.IGNORECASE
    )
    GOAL_PATTERN = re.compile(
        r'### (?:Goal|目標\s*\(Goal\))\s*\n(.+?)(?=###|$)', re.DOTALL | re.IGNORECASE
    )
    RATIONALE_PATTERN = re.compile(
        r'### (?:Rationale|理由\s*\(Rationale\))\s*\n(.+?)(?=###|$)', re.DOTALL | re.IGNORECASE
    )
    EXPECTED_CHANGE_PATTERN = re.compile(
        r'### (?:Expected Change|期待される変更\s*\(Expected Change\))\s*\n(.+?)(?=###|$)', re.DOTALL | re.IGNORECASE
    )
    NON_GOALS_PATTERN = re.compile(
        r'### (?:Non-Goals|非目標\s*\(Non-Goals\))\s*\n(.+?)(?=###|$)', re.DOTALL | re.IGNORECASE
    )
    RISK_PATTERN = re.compile(
        r'### (?:Risk|リスク\s*\(Risk\))\s*\n(.+?)(?=###|##|$)', re.DOTALL | re.IGNORECASE
    )
    # Commit info: "Commit hash: xxx" / "コミットハッシュ: xxx" and similar
    COMMIT_HASH_PATTERN = re.compile(
        r'[-*]*\s*\**(?:Commit hash|コミットハッシュ)[:\*\s]+`?([a-f0-9]+)`?', re.IGNORECASE
    )
    COMMIT_MSG_PATTERN = re.compile(
        r'[-*]*\s*\**(?:Commit message|コミットメッセージ)[:\*\s]+`?(.+)`?', re.MULTILINE | re.IGNORECASE
    )
    RELATED_ADR_PATTERN = re.compile(
        r'(?:Related ADR|関連ADR)[:\s]+(ADR-)?(\d+)', re.IGNORECASE
    )

    # New ADR section (when Worker proposes an architecture/design decision)
    ADR_SECTION_PATTERN = re.compile(
        r'## (?:New ADR|新規ADR).*?(?=\n## |\Z)', re.DOTALL | re.IGNORECASE
    )
    ADR_TITLE_PATTERN = re.compile(
        r'### (?:Title|タイトル)\s*\n(.+?)(?=###|$)', re.DOTALL | re.IGNORECASE
    )
    ADR_CONTEXT_PATTERN = re.compile(
        r'### (?:Context|コンテキスト)\s*\n(.+?)(?=###|$)', re.DOTALL | re.IGNORECASE
    )
    ADR_DECISION_PATTERN = re.compile(
        r'### (?:Decision|決定)\s*\n(.+?)(?=###|$)', re.DOTALL | re.IGNORECASE
    )
    ADR_RATIONALE_PATTERN = re.compile(
        r'### (?:Rationale|理由)\s*\n(.+?)(?=###|$)', re.DOTALL | re.IGNORECASE
    )
    ADR_CONSEQUENCES_PATTERN = re.compile(
        r'### (?:Consequences|結果)\s*\n(.+?)(?=###|## |$)', re.DOTALL | re.IGNORECASE
    )

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

        # Extract commit info from full response (supports multiple commits)
        commits = cls._extract_commits(response)

        # Extract related ADR (existing ADR reference)
        adr_match = cls.RELATED_ADR_PATTERN.search(response)
        related_adr = adr_match.group(2) if adr_match else None

        # Extract new ADR to create (when Worker reports an architecture/design decision)
        adr_to_create = cls._parse_new_adr(response)

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
            "commits": commits,
            "related_adr": related_adr,
            "adr_to_create": adr_to_create,
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
        # Extract commit info (supports multiple commits)
        commits = cls._extract_commits(response)

        # If we have at least one commit, create a minimal intent record
        if not commits:
            return None

        now = datetime.now().isoformat()

        # Try to extract goal from "Implementation" / "実装内容" section
        impl_match = re.search(
            r'## (?:Implementation|実装内容)\s*\n(.+?)(?=##|$)', response, re.DOTALL | re.IGNORECASE
        )
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
            "commits": commits,
            "related_adr": None,
            "adr_to_create": None,
        }

    @classmethod
    def _parse_new_adr(cls, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse '新規ADR' section from Worker response.
        Returns a dict with title, context, decision, rationale, consequences for ADRManager.create_adr,
        or None if section is absent or indicates 'なし'.
        """
        section_match = cls.ADR_SECTION_PATTERN.search(response)
        if not section_match:
            return None
        section = section_match.group(0)
        # Skip if section only says "None" / "なし" / "該当しない"
        if re.search(r'^(?:None|なし|該当しない)\s*$', section.strip(), re.IGNORECASE | re.MULTILINE):
            return None
        title = cls._extract_single(cls.ADR_TITLE_PATTERN, section)
        if not title or not title.strip() or title.strip().lower() in ("なし", "none"):
            return None
        context = cls._extract_single(cls.ADR_CONTEXT_PATTERN, section) or ""
        decision = cls._extract_single(cls.ADR_DECISION_PATTERN, section) or ""
        rationale = cls._extract_single(cls.ADR_RATIONALE_PATTERN, section) or ""
        consequences = cls._extract_single(cls.ADR_CONSEQUENCES_PATTERN, section) or ""
        return {
            "title": title.strip(),
            "context": context.strip(),
            "decision": decision.strip(),
            "rationale": rationale.strip(),
            "consequences": consequences.strip(),
        }

    @classmethod
    def _extract_all(cls, pattern: re.Pattern, text: str) -> List[str]:
        """Extract all values from pattern matches (findall)."""
        return [m.strip() for m in pattern.findall(text)]

    @classmethod
    def _extract_commits(cls, response: str) -> List[Dict[str, Any]]:
        """
        Extract all commit hash/message pairs from response.
        Pairs by order: first hash with first message, second hash with second message, etc.
        """
        hashes = cls._extract_all(cls.COMMIT_HASH_PATTERN, response)
        messages = cls._extract_all(cls.COMMIT_MSG_PATTERN, response)
        now = datetime.now().isoformat()
        commits = []
        for i, h in enumerate(hashes):
            msg = messages[i].strip() if i < len(messages) else ""
            commits.append({
                "hash": h,
                "message": msg,
                "timestamp": now,
            })
        return commits

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
