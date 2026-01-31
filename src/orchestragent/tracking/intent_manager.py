"""Intent management utilities."""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class IntentManager:
    """Manages Intent files for the agent system."""

    def __init__(self, state_dir: str = "state"):
        """
        Initialize IntentManager.

        Args:
            state_dir: State directory path
        """
        self.state_dir = Path(state_dir)
        self.intents_dir = self.state_dir / "intents"
        self.intents_dir.mkdir(parents=True, exist_ok=True)

    def save_intent(self, intent_data: Dict[str, Any]) -> str:
        """
        Save Intent data to file.

        Args:
            intent_data: Intent dictionary from parser

        Returns:
            Path to saved file
        """
        task_id = intent_data.get("task_id", "unknown")
        filename = f"intent_{task_id}.yaml"
        filepath = self.intents_dir / filename

        # Update timestamp
        intent_data["updated_at"] = datetime.now().isoformat()

        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(
                intent_data,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False
            )

        return str(filepath)

    def get_intent(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Intent by task ID.

        Args:
            task_id: Task ID

        Returns:
            Intent dictionary or None
        """
        filename = f"intent_{task_id}.yaml"
        filepath = self.intents_dir / filename

        if not filepath.exists():
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get_all_intents(self) -> List[Dict[str, Any]]:
        """
        Get all Intents.

        Returns:
            List of Intent dictionaries
        """
        intents = []
        for filepath in self.intents_dir.glob("intent_*.yaml"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    intent = yaml.safe_load(f)
                    if intent:
                        intents.append(intent)
            except Exception:
                continue

        # Sort by created_at (newest first)
        intents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return intents

    def add_commit_to_intent(
        self,
        task_id: str,
        commit_hash: str,
        commit_message: str
    ) -> bool:
        """
        Add commit information to existing Intent.

        Args:
            task_id: Task ID
            commit_hash: Git commit hash
            commit_message: Commit message

        Returns:
            True if successful
        """
        intent = self.get_intent(task_id)
        if not intent:
            return False

        if "commits" not in intent:
            intent["commits"] = []

        # Check if commit already exists
        existing_hashes = [c.get("hash") for c in intent["commits"]]
        if commit_hash in existing_hashes:
            return True  # Already recorded

        intent["commits"].append({
            "hash": commit_hash,
            "message": commit_message,
            "timestamp": datetime.now().isoformat(),
        })
        intent["updated_at"] = datetime.now().isoformat()

        self.save_intent(intent)
        return True

    def link_adr(self, task_id: str, adr_number: str) -> bool:
        """
        Link ADR to Intent.

        Args:
            task_id: Task ID
            adr_number: ADR number (e.g., "0002")

        Returns:
            True if successful
        """
        intent = self.get_intent(task_id)
        if not intent:
            return False

        intent["related_adr"] = adr_number
        intent["updated_at"] = datetime.now().isoformat()

        self.save_intent(intent)
        return True

    def update_intent_field(
        self,
        task_id: str,
        field: str,
        value: Any
    ) -> bool:
        """
        Update a specific field in Intent.

        Args:
            task_id: Task ID
            field: Field name in intent (e.g., "goal", "rationale")
            value: New value

        Returns:
            True if successful
        """
        intent = self.get_intent(task_id)
        if not intent:
            return False

        if "intent" not in intent:
            intent["intent"] = {}

        intent["intent"][field] = value
        intent["updated_at"] = datetime.now().isoformat()

        self.save_intent(intent)
        return True

    def delete_intent(self, task_id: str) -> bool:
        """
        Delete Intent file.

        Args:
            task_id: Task ID

        Returns:
            True if successful
        """
        filename = f"intent_{task_id}.yaml"
        filepath = self.intents_dir / filename

        if not filepath.exists():
            return False

        filepath.unlink()
        return True

    def get_intents_by_adr(self, adr_number: str) -> List[Dict[str, Any]]:
        """
        Get all Intents linked to a specific ADR.

        Args:
            adr_number: ADR number (e.g., "0002")

        Returns:
            List of Intent dictionaries
        """
        all_intents = self.get_all_intents()
        return [
            intent for intent in all_intents
            if intent.get("related_adr") == adr_number
        ]

    def search_intents(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Search Intents by keyword in goal or rationale.

        Args:
            keyword: Search keyword

        Returns:
            List of matching Intent dictionaries
        """
        all_intents = self.get_all_intents()
        keyword_lower = keyword.lower()

        results = []
        for intent in all_intents:
            intent_data = intent.get("intent", {})
            goal = intent_data.get("goal", "") or ""
            rationale = intent_data.get("rationale", "") or ""

            if keyword_lower in goal.lower() or keyword_lower in rationale.lower():
                results.append(intent)

        return results
