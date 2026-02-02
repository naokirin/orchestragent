"""Tests for tracking.intent_manager (IntentManager)."""

import pytest
import yaml
from pathlib import Path

from orchestragent.tracking.intent_manager import IntentManager


class TestIntentManagerInit:
    """Tests for IntentManager initialization."""

    def test_init_creates_intents_directory(self, temp_dir):
        """Create intents directory on init."""
        manager = IntentManager(state_dir=str(temp_dir))

        intents_dir = temp_dir / "intents"
        assert intents_dir.exists()


class TestIntentManagerSaveIntent:
    """Tests for IntentManager.save_intent."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_save_intent_creates_file(self, intent_manager, temp_dir):
        """Create Intent file."""
        intent_data = {
            "task_id": "task-001",
            "goal": "Add new feature",
        }
        filepath = intent_manager.save_intent(intent_data)

        assert Path(filepath).exists()

    def test_save_intent_returns_filepath(self, intent_manager):
        """Return file path."""
        intent_data = {"task_id": "task-002"}
        filepath = intent_manager.save_intent(intent_data)

        assert "intent_task-002.yaml" in filepath

    def test_save_intent_adds_updated_at(self, intent_manager, temp_dir):
        """Add updated_at timestamp."""
        intent_data = {"task_id": "task-003"}
        intent_manager.save_intent(intent_data)

        saved = intent_manager.get_intent("task-003")
        assert "updated_at" in saved

    def test_save_intent_overwrites_existing(self, intent_manager):
        """Overwrite existing file."""
        intent_manager.save_intent({"task_id": "task-004", "goal": "Old goal"})
        intent_manager.save_intent({"task_id": "task-004", "goal": "New goal"})

        saved = intent_manager.get_intent("task-004")
        assert saved["goal"] == "New goal"

    def test_save_intent_uses_unknown_for_missing_task_id(self, intent_manager, temp_dir):
        """Use 'unknown' when task_id is missing."""
        filepath = intent_manager.save_intent({"goal": "Some goal"})

        assert "intent_unknown.yaml" in filepath


class TestIntentManagerGetIntent:
    """Tests for IntentManager.get_intent."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_get_intent_returns_saved_data(self, intent_manager):
        """Retrieve saved Intent."""
        intent_manager.save_intent({
            "task_id": "task-001",
            "goal": "Test goal",
            "rationale": "Test rationale",
        })

        intent = intent_manager.get_intent("task-001")

        assert intent["task_id"] == "task-001"
        assert intent["goal"] == "Test goal"

    def test_get_intent_nonexistent_returns_none(self, intent_manager):
        """Return None for nonexistent Intent."""
        intent = intent_manager.get_intent("nonexistent")

        assert intent is None


class TestIntentManagerGetAllIntents:
    """Tests for IntentManager.get_all_intents."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_get_all_intents_empty(self, intent_manager):
        """Return empty list when no Intents."""
        intents = intent_manager.get_all_intents()

        assert intents == []

    def test_get_all_intents_returns_all(self, intent_manager):
        """Return all Intents."""
        intent_manager.save_intent({"task_id": "task-001", "created_at": "2025-01-01"})
        intent_manager.save_intent({"task_id": "task-002", "created_at": "2025-01-02"})

        intents = intent_manager.get_all_intents()

        assert len(intents) == 2

    def test_get_all_intents_sorted_by_created_at(self, intent_manager):
        """Sorted by created_at descending."""
        intent_manager.save_intent({"task_id": "old", "created_at": "2025-01-01"})
        intent_manager.save_intent({"task_id": "new", "created_at": "2025-01-02"})

        intents = intent_manager.get_all_intents()

        assert intents[0]["task_id"] == "new"

    def test_get_all_intents_skips_invalid_yaml(self, intent_manager, temp_dir):
        """Skip invalid YAML files."""
        intent_manager.save_intent({"task_id": "valid"})
        # Create invalid YAML file
        invalid_file = temp_dir / "intents" / "intent_invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: {")

        intents = intent_manager.get_all_intents()

        assert len(intents) == 1
        assert intents[0]["task_id"] == "valid"


class TestIntentManagerAddCommitToIntent:
    """Tests for IntentManager.add_commit_to_intent."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_add_commit_to_intent_success(self, intent_manager):
        """Can add commit info."""
        intent_manager.save_intent({"task_id": "task-001"})

        result = intent_manager.add_commit_to_intent(
            "task-001",
            "abc1234",
            "Add new feature",
        )

        assert result is True
        intent = intent_manager.get_intent("task-001")
        assert len(intent["commits"]) == 1
        assert intent["commits"][0]["hash"] == "abc1234"

    def test_add_commit_to_intent_multiple(self, intent_manager):
        """Can add multiple commits."""
        intent_manager.save_intent({"task_id": "task-001"})

        intent_manager.add_commit_to_intent("task-001", "abc1234", "First")
        intent_manager.add_commit_to_intent("task-001", "def5678", "Second")

        intent = intent_manager.get_intent("task-001")
        assert len(intent["commits"]) == 2

    def test_add_commit_to_intent_duplicate_skipped(self, intent_manager):
        """Duplicate commits are skipped."""
        intent_manager.save_intent({"task_id": "task-001"})

        intent_manager.add_commit_to_intent("task-001", "abc1234", "First")
        result = intent_manager.add_commit_to_intent("task-001", "abc1234", "First again")

        assert result is True  # treated as success
        intent = intent_manager.get_intent("task-001")
        assert len(intent["commits"]) == 1

    def test_add_commit_to_intent_nonexistent_returns_false(self, intent_manager):
        """Return False when adding to nonexistent Intent."""
        result = intent_manager.add_commit_to_intent("nonexistent", "abc", "msg")

        assert result is False


class TestIntentManagerLinkAdr:
    """Tests for IntentManager.link_adr."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_link_adr_success(self, intent_manager):
        """Can link ADR."""
        intent_manager.save_intent({"task_id": "task-001"})

        result = intent_manager.link_adr("task-001", "0001")

        assert result is True
        intent = intent_manager.get_intent("task-001")
        assert intent["related_adr"] == "0001"

    def test_link_adr_nonexistent_returns_false(self, intent_manager):
        """Return False when linking to nonexistent Intent."""
        result = intent_manager.link_adr("nonexistent", "0001")

        assert result is False


class TestIntentManagerUpdateIntentField:
    """Tests for IntentManager.update_intent_field."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_update_intent_field_success(self, intent_manager):
        """Can update Intent fields."""
        intent_manager.save_intent({"task_id": "task-001"})

        result = intent_manager.update_intent_field("task-001", "goal", "Updated goal")

        assert result is True
        intent = intent_manager.get_intent("task-001")
        assert intent["intent"]["goal"] == "Updated goal"

    def test_update_intent_field_creates_intent_dict(self, intent_manager):
        """Create intent dict when missing."""
        intent_manager.save_intent({"task_id": "task-001"})

        intent_manager.update_intent_field("task-001", "rationale", "New rationale")

        intent = intent_manager.get_intent("task-001")
        assert "intent" in intent
        assert intent["intent"]["rationale"] == "New rationale"

    def test_update_intent_field_nonexistent_returns_false(self, intent_manager):
        """Return False when updating nonexistent Intent."""
        result = intent_manager.update_intent_field("nonexistent", "goal", "value")

        assert result is False


class TestIntentManagerDeleteIntent:
    """Tests for IntentManager.delete_intent."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_delete_intent_success(self, intent_manager):
        """Can delete Intent."""
        intent_manager.save_intent({"task_id": "task-001"})

        result = intent_manager.delete_intent("task-001")

        assert result is True
        assert intent_manager.get_intent("task-001") is None

    def test_delete_intent_nonexistent_returns_false(self, intent_manager):
        """Return False when deleting nonexistent Intent."""
        result = intent_manager.delete_intent("nonexistent")

        assert result is False


class TestIntentManagerGetIntentsByAdr:
    """Tests for IntentManager.get_intents_by_adr."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_get_intents_by_adr_returns_matching(self, intent_manager):
        """Return Intents linked to ADR."""
        intent_manager.save_intent({"task_id": "task-001", "related_adr": "0001"})
        intent_manager.save_intent({"task_id": "task-002", "related_adr": "0002"})
        intent_manager.save_intent({"task_id": "task-003", "related_adr": "0001"})

        intents = intent_manager.get_intents_by_adr("0001")

        assert len(intents) == 2
        task_ids = [i["task_id"] for i in intents]
        assert "task-001" in task_ids
        assert "task-003" in task_ids

    def test_get_intents_by_adr_empty(self, intent_manager):
        """Return empty list when no matching Intent."""
        intent_manager.save_intent({"task_id": "task-001", "related_adr": "0001"})

        intents = intent_manager.get_intents_by_adr("9999")

        assert intents == []


class TestIntentManagerSearchIntents:
    """Tests for IntentManager.search_intents."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_search_intents_matches_goal(self, intent_manager):
        """Return Intents matching goal."""
        intent_manager.save_intent({
            "task_id": "task-001",
            "intent": {"goal": "Add authentication feature"},
        })
        intent_manager.save_intent({
            "task_id": "task-002",
            "intent": {"goal": "Fix bug"},
        })

        intents = intent_manager.search_intents("authentication")

        assert len(intents) == 1
        assert intents[0]["task_id"] == "task-001"

    def test_search_intents_matches_rationale(self, intent_manager):
        """Return Intents matching rationale."""
        intent_manager.save_intent({
            "task_id": "task-001",
            "intent": {"rationale": "Improve security"},
        })

        intents = intent_manager.search_intents("security")

        assert len(intents) == 1

    def test_search_intents_case_insensitive(self, intent_manager):
        """Search is case-insensitive."""
        intent_manager.save_intent({
            "task_id": "task-001",
            "intent": {"goal": "Add AUTHENTICATION"},
        })

        intents = intent_manager.search_intents("authentication")

        assert len(intents) == 1

    def test_search_intents_no_match(self, intent_manager):
        """Return empty list when no match."""
        intent_manager.save_intent({
            "task_id": "task-001",
            "intent": {"goal": "Something else"},
        })

        intents = intent_manager.search_intents("nonexistent")

        assert intents == []
