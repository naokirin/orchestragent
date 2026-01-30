"""ADR (Architecture Decision Records) management utilities."""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class ADRManager:
    """Manages ADR files."""

    ADR_PATTERN = re.compile(r'^(\d{4})-(.+)\.md$')

    def __init__(self, adr_dir: str = "docs/adr"):
        """
        Initialize ADRManager.

        Args:
            adr_dir: ADR directory path
        """
        self.adr_dir = Path(adr_dir)
        self.adr_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_template()

    def _ensure_template(self) -> None:
        """Ensure ADR template exists."""
        template_path = self.adr_dir / "template.md"
        if not template_path.exists():
            template = '''# ADR-{number}: {title}

## ステータス
Proposed / Accepted / Deprecated / Superseded

## コンテキスト
[決定の背景となる状況や問題を記述してください]

## 決定
[採用した決定の内容を記述してください]

## 理由
[決定の理由を記述してください]

## 結果
[決定による影響・結果を記述してください]

## 関連Intent
- [関連するタスクIDをリストしてください]
'''
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(template)

    def get_next_number(self) -> int:
        """Get next ADR number."""
        existing_numbers = []
        for filepath in self.adr_dir.glob("*.md"):
            match = self.ADR_PATTERN.match(filepath.name)
            if match:
                existing_numbers.append(int(match.group(1)))

        return max(existing_numbers, default=0) + 1

    def create_adr(
        self,
        title: str,
        context: str = "",
        decision: str = "",
        rationale: str = "",
        consequences: str = "",
        related_intents: List[str] = None,
        status: str = "Proposed"
    ) -> str:
        """
        Create new ADR file.

        Args:
            title: ADR title
            context: Context section
            decision: Decision section
            rationale: Rationale section
            consequences: Consequences section
            related_intents: List of related task IDs
            status: Initial status (default: Proposed)

        Returns:
            ADR number as string (e.g., "0001")
        """
        number = self.get_next_number()
        number_str = f"{number:04d}"
        slug = self._slugify(title)
        filename = f"{number_str}-{slug}.md"

        intents_text = ""
        if related_intents:
            intents_text = "\n".join([f"- {task_id}" for task_id in related_intents])
        else:
            intents_text = "- なし"

        content = f'''# ADR-{number_str}: {title}

## ステータス
{status}

## コンテキスト
{context if context else "[決定の背景となる状況や問題]"}

## 決定
{decision if decision else "[採用した決定の内容]"}

## 理由
{rationale if rationale else "[決定の理由]"}

## 結果
{consequences if consequences else "[決定による影響・結果]"}

## 関連Intent
{intents_text}
'''

        filepath = self.adr_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return number_str

    def get_adr(self, number: str) -> Optional[Dict[str, Any]]:
        """
        Get ADR by number.

        Args:
            number: ADR number (e.g., "0001")

        Returns:
            ADR dictionary or None
        """
        # Normalize number format
        number = number.zfill(4)

        for filepath in self.adr_dir.glob(f"{number}-*.md"):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse title
            title_match = re.search(r'^# ADR-\d+: (.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else "Unknown"

            # Parse status
            status_match = re.search(
                r'^## ステータス\s*\n(.+?)(?=\n##|\Z)',
                content,
                re.MULTILINE | re.DOTALL
            )
            status = status_match.group(1).strip().split('\n')[0] if status_match else "Unknown"

            # Parse context
            context_match = re.search(
                r'^## コンテキスト\s*\n(.+?)(?=\n##|\Z)',
                content,
                re.MULTILINE | re.DOTALL
            )
            context = context_match.group(1).strip() if context_match else ""

            # Parse decision
            decision_match = re.search(
                r'^## 決定\s*\n(.+?)(?=\n##|\Z)',
                content,
                re.MULTILINE | re.DOTALL
            )
            decision = decision_match.group(1).strip() if decision_match else ""

            # Parse rationale
            rationale_match = re.search(
                r'^## 理由\s*\n(.+?)(?=\n##|\Z)',
                content,
                re.MULTILINE | re.DOTALL
            )
            rationale = rationale_match.group(1).strip() if rationale_match else ""

            # Parse consequences
            consequences_match = re.search(
                r'^## 結果\s*\n(.+?)(?=\n##|\Z)',
                content,
                re.MULTILINE | re.DOTALL
            )
            consequences = consequences_match.group(1).strip() if consequences_match else ""

            # Parse related intents
            intents_match = re.search(
                r'^## 関連Intent\s*\n(.+?)(?=\n##|\Z)',
                content,
                re.MULTILINE | re.DOTALL
            )
            related_intents = []
            if intents_match:
                intents_text = intents_match.group(1)
                related_intents = re.findall(r'^[-*]\s+(.+)$', intents_text, re.MULTILINE)
                related_intents = [i.strip() for i in related_intents if i.strip() != "なし"]

            return {
                "number": number,
                "title": title,
                "status": status,
                "context": context,
                "decision": decision,
                "rationale": rationale,
                "consequences": consequences,
                "related_intents": related_intents,
                "filepath": str(filepath),
                "content": content,
            }

        return None

    def get_all_adrs(self) -> List[Dict[str, Any]]:
        """Get all ADRs."""
        adrs = []
        for filepath in self.adr_dir.glob("*.md"):
            match = self.ADR_PATTERN.match(filepath.name)
            if not match:
                continue

            number = match.group(1)
            adr = self.get_adr(number)
            if adr:
                adrs.append(adr)

        # Sort by number
        adrs.sort(key=lambda x: x.get("number", "0"))
        return adrs

    def update_adr_status(self, number: str, new_status: str) -> bool:
        """
        Update ADR status.

        Args:
            number: ADR number
            new_status: New status (Proposed, Accepted, Deprecated, Superseded)

        Returns:
            True if successful
        """
        adr = self.get_adr(number)
        if not adr:
            return False

        filepath = Path(adr["filepath"])
        content = adr["content"]

        # Replace status
        new_content = re.sub(
            r'(^## ステータス\s*\n)(.+?)(?=\n##|\Z)',
            f'\\g<1>{new_status}',
            content,
            flags=re.MULTILINE | re.DOTALL
        )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    def add_related_intent(self, number: str, task_id: str) -> bool:
        """
        Add related intent to ADR.

        Args:
            number: ADR number
            task_id: Task ID to add

        Returns:
            True if successful
        """
        adr = self.get_adr(number)
        if not adr:
            return False

        # Check if already added
        if task_id in adr.get("related_intents", []):
            return True

        filepath = Path(adr["filepath"])
        content = adr["content"]

        # Find the related intents section and add new task
        intents_match = re.search(
            r'(^## 関連Intent\s*\n)(.+?)(?=\n##|\Z)',
            content,
            re.MULTILINE | re.DOTALL
        )

        if intents_match:
            existing = intents_match.group(2).strip()
            if existing == "- なし":
                new_intents = f"- {task_id}"
            else:
                new_intents = f"{existing}\n- {task_id}"

            new_content = content[:intents_match.start(2)] + new_intents + content[intents_match.end(2):]
        else:
            # Add section at end
            new_content = content.rstrip() + f"\n\n## 関連Intent\n- {task_id}\n"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to slug for filename."""
        # Replace Japanese characters with romanji or keep simple chars
        text = text.lower()
        # Remove special characters, keep alphanumeric, hyphens, and underscores
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')[:50]
