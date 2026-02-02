"""Tests for tracking.intent_manager (IntentManager)."""

import pytest
import yaml
from pathlib import Path

from orchestragent.tracking.intent_manager import IntentManager


class TestIntentManagerInit:
    """Tests for IntentManager initialization."""

    def test_init_creates_intents_directory(self, temp_dir):
        """初期化時に intents ディレクトリを作成する。"""
        manager = IntentManager(state_dir=str(temp_dir))

        intents_dir = temp_dir / "intents"
        assert intents_dir.exists()


class TestIntentManagerSaveIntent:
    """Tests for IntentManager.save_intent."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_save_intent_creates_file(self, intent_manager, temp_dir):
        """Intent ファイルを作成する。"""
        intent_data = {
            "task_id": "task-001",
            "goal": "Add new feature",
        }
        filepath = intent_manager.save_intent(intent_data)

        assert Path(filepath).exists()

    def test_save_intent_returns_filepath(self, intent_manager):
        """ファイルパスを返す。"""
        intent_data = {"task_id": "task-002"}
        filepath = intent_manager.save_intent(intent_data)

        assert "intent_task-002.yaml" in filepath

    def test_save_intent_adds_updated_at(self, intent_manager, temp_dir):
        """updated_at タイムスタンプを追加する。"""
        intent_data = {"task_id": "task-003"}
        intent_manager.save_intent(intent_data)

        saved = intent_manager.get_intent("task-003")
        assert "updated_at" in saved

    def test_save_intent_overwrites_existing(self, intent_manager):
        """既存ファイルを上書きする。"""
        intent_manager.save_intent({"task_id": "task-004", "goal": "Old goal"})
        intent_manager.save_intent({"task_id": "task-004", "goal": "New goal"})

        saved = intent_manager.get_intent("task-004")
        assert saved["goal"] == "New goal"

    def test_save_intent_uses_unknown_for_missing_task_id(self, intent_manager, temp_dir):
        """task_id がない場合は 'unknown' を使用。"""
        filepath = intent_manager.save_intent({"goal": "Some goal"})

        assert "intent_unknown.yaml" in filepath


class TestIntentManagerGetIntent:
    """Tests for IntentManager.get_intent."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_get_intent_returns_saved_data(self, intent_manager):
        """保存した Intent を取得できる。"""
        intent_manager.save_intent({
            "task_id": "task-001",
            "goal": "Test goal",
            "rationale": "Test rationale",
        })

        intent = intent_manager.get_intent("task-001")

        assert intent["task_id"] == "task-001"
        assert intent["goal"] == "Test goal"

    def test_get_intent_nonexistent_returns_none(self, intent_manager):
        """存在しない Intent は None を返す。"""
        intent = intent_manager.get_intent("nonexistent")

        assert intent is None


class TestIntentManagerGetAllIntents:
    """Tests for IntentManager.get_all_intents."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_get_all_intents_empty(self, intent_manager):
        """Intent がない場合は空リストを返す。"""
        intents = intent_manager.get_all_intents()

        assert intents == []

    def test_get_all_intents_returns_all(self, intent_manager):
        """全ての Intent を返す。"""
        intent_manager.save_intent({"task_id": "task-001", "created_at": "2025-01-01"})
        intent_manager.save_intent({"task_id": "task-002", "created_at": "2025-01-02"})

        intents = intent_manager.get_all_intents()

        assert len(intents) == 2

    def test_get_all_intents_sorted_by_created_at(self, intent_manager):
        """created_at で降順ソートされる。"""
        intent_manager.save_intent({"task_id": "old", "created_at": "2025-01-01"})
        intent_manager.save_intent({"task_id": "new", "created_at": "2025-01-02"})

        intents = intent_manager.get_all_intents()

        assert intents[0]["task_id"] == "new"

    def test_get_all_intents_skips_invalid_yaml(self, intent_manager, temp_dir):
        """不正な YAML ファイルはスキップする。"""
        intent_manager.save_intent({"task_id": "valid"})
        # 不正な YAML ファイルを作成
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
        """コミット情報を追加できる。"""
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
        """複数のコミットを追加できる。"""
        intent_manager.save_intent({"task_id": "task-001"})

        intent_manager.add_commit_to_intent("task-001", "abc1234", "First")
        intent_manager.add_commit_to_intent("task-001", "def5678", "Second")

        intent = intent_manager.get_intent("task-001")
        assert len(intent["commits"]) == 2

    def test_add_commit_to_intent_duplicate_skipped(self, intent_manager):
        """重複コミットはスキップされる。"""
        intent_manager.save_intent({"task_id": "task-001"})

        intent_manager.add_commit_to_intent("task-001", "abc1234", "First")
        result = intent_manager.add_commit_to_intent("task-001", "abc1234", "First again")

        assert result is True  # 成功として扱う
        intent = intent_manager.get_intent("task-001")
        assert len(intent["commits"]) == 1

    def test_add_commit_to_intent_nonexistent_returns_false(self, intent_manager):
        """存在しない Intent への追加は False を返す。"""
        result = intent_manager.add_commit_to_intent("nonexistent", "abc", "msg")

        assert result is False


class TestIntentManagerLinkAdr:
    """Tests for IntentManager.link_adr."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_link_adr_success(self, intent_manager):
        """ADR をリンクできる。"""
        intent_manager.save_intent({"task_id": "task-001"})

        result = intent_manager.link_adr("task-001", "0001")

        assert result is True
        intent = intent_manager.get_intent("task-001")
        assert intent["related_adr"] == "0001"

    def test_link_adr_nonexistent_returns_false(self, intent_manager):
        """存在しない Intent へのリンクは False を返す。"""
        result = intent_manager.link_adr("nonexistent", "0001")

        assert result is False


class TestIntentManagerUpdateIntentField:
    """Tests for IntentManager.update_intent_field."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_update_intent_field_success(self, intent_manager):
        """Intent フィールドを更新できる。"""
        intent_manager.save_intent({"task_id": "task-001"})

        result = intent_manager.update_intent_field("task-001", "goal", "Updated goal")

        assert result is True
        intent = intent_manager.get_intent("task-001")
        assert intent["intent"]["goal"] == "Updated goal"

    def test_update_intent_field_creates_intent_dict(self, intent_manager):
        """intent dict がない場合は作成する。"""
        intent_manager.save_intent({"task_id": "task-001"})

        intent_manager.update_intent_field("task-001", "rationale", "New rationale")

        intent = intent_manager.get_intent("task-001")
        assert "intent" in intent
        assert intent["intent"]["rationale"] == "New rationale"

    def test_update_intent_field_nonexistent_returns_false(self, intent_manager):
        """存在しない Intent の更新は False を返す。"""
        result = intent_manager.update_intent_field("nonexistent", "goal", "value")

        assert result is False


class TestIntentManagerDeleteIntent:
    """Tests for IntentManager.delete_intent."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_delete_intent_success(self, intent_manager):
        """Intent を削除できる。"""
        intent_manager.save_intent({"task_id": "task-001"})

        result = intent_manager.delete_intent("task-001")

        assert result is True
        assert intent_manager.get_intent("task-001") is None

    def test_delete_intent_nonexistent_returns_false(self, intent_manager):
        """存在しない Intent の削除は False を返す。"""
        result = intent_manager.delete_intent("nonexistent")

        assert result is False


class TestIntentManagerGetIntentsByAdr:
    """Tests for IntentManager.get_intents_by_adr."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_get_intents_by_adr_returns_matching(self, intent_manager):
        """ADR にリンクされた Intent を返す。"""
        intent_manager.save_intent({"task_id": "task-001", "related_adr": "0001"})
        intent_manager.save_intent({"task_id": "task-002", "related_adr": "0002"})
        intent_manager.save_intent({"task_id": "task-003", "related_adr": "0001"})

        intents = intent_manager.get_intents_by_adr("0001")

        assert len(intents) == 2
        task_ids = [i["task_id"] for i in intents]
        assert "task-001" in task_ids
        assert "task-003" in task_ids

    def test_get_intents_by_adr_empty(self, intent_manager):
        """マッチする Intent がない場合は空リストを返す。"""
        intent_manager.save_intent({"task_id": "task-001", "related_adr": "0001"})

        intents = intent_manager.get_intents_by_adr("9999")

        assert intents == []


class TestIntentManagerSearchIntents:
    """Tests for IntentManager.search_intents."""

    @pytest.fixture
    def intent_manager(self, temp_dir):
        return IntentManager(state_dir=str(temp_dir))

    def test_search_intents_matches_goal(self, intent_manager):
        """goal でマッチする Intent を返す。"""
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
        """rationale でマッチする Intent を返す。"""
        intent_manager.save_intent({
            "task_id": "task-001",
            "intent": {"rationale": "Improve security"},
        })

        intents = intent_manager.search_intents("security")

        assert len(intents) == 1

    def test_search_intents_case_insensitive(self, intent_manager):
        """検索は大文字小文字を区別しない。"""
        intent_manager.save_intent({
            "task_id": "task-001",
            "intent": {"goal": "Add AUTHENTICATION"},
        })

        intents = intent_manager.search_intents("authentication")

        assert len(intents) == 1

    def test_search_intents_no_match(self, intent_manager):
        """マッチしない場合は空リストを返す。"""
        intent_manager.save_intent({
            "task_id": "task-001",
            "intent": {"goal": "Something else"},
        })

        intents = intent_manager.search_intents("nonexistent")

        assert intents == []
