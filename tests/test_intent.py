"""Tests for Intent-related data models."""

from datetime import datetime

from orchestragent.models.intent import Commit, IntentData, Intent


class TestCommit:
    """Tests for Commit dataclass."""

    def test_create_commit_basic(self):
        """Test creating a basic commit."""
        commit = Commit(hash="abc123", message="Test commit")
        assert commit.hash == "abc123"
        assert commit.message == "Test commit"
        assert commit.timestamp is not None

    def test_create_commit_with_timestamp(self):
        """Test creating commit with explicit timestamp."""
        ts = "2024-01-15T10:00:00"
        commit = Commit(hash="def456", message="Another commit", timestamp=ts)
        assert commit.timestamp == ts

    def test_post_init_sets_timestamp(self):
        """Test that post_init sets timestamp when None."""
        commit = Commit(hash="abc", message="msg")
        # Timestamp should be set to a valid ISO format datetime
        datetime.fromisoformat(commit.timestamp)

    def test_to_dict(self):
        """Test converting commit to dict."""
        commit = Commit(hash="abc123", message="Test", timestamp="2024-01-01T00:00:00")
        d = commit.to_dict()
        assert d["hash"] == "abc123"
        assert d["message"] == "Test"
        assert d["timestamp"] == "2024-01-01T00:00:00"

    def test_from_dict(self):
        """Test creating commit from dict."""
        data = {
            "hash": "xyz789",
            "message": "From dict",
            "timestamp": "2024-02-01T12:00:00",
        }
        commit = Commit.from_dict(data)
        assert commit.hash == "xyz789"
        assert commit.message == "From dict"
        assert commit.timestamp == "2024-02-01T12:00:00"

    def test_from_dict_defaults(self):
        """Test creating commit from empty dict uses defaults."""
        commit = Commit.from_dict({})
        assert commit.hash == ""
        assert commit.message == ""
        # timestamp will be set by post_init
        assert commit.timestamp is not None

    def test_roundtrip_dict_conversion(self):
        """Test that to_dict -> from_dict preserves data."""
        original = Commit(hash="abc", message="test", timestamp="2024-01-01T00:00:00")
        restored = Commit.from_dict(original.to_dict())
        assert restored.hash == original.hash
        assert restored.message == original.message
        assert restored.timestamp == original.timestamp


class TestIntentData:
    """Tests for IntentData dataclass."""

    def test_default_values(self):
        """Test default values."""
        intent_data = IntentData()
        assert intent_data.goal == ""
        assert intent_data.rationale == ""

    def test_create_with_values(self):
        """Test creating with values."""
        intent_data = IntentData(goal="Add feature", rationale="User requested")
        assert intent_data.goal == "Add feature"
        assert intent_data.rationale == "User requested"

    def test_to_dict(self):
        """Test converting to dict."""
        intent_data = IntentData(goal="Goal", rationale="Rationale")
        d = intent_data.to_dict()
        assert d["goal"] == "Goal"
        assert d["rationale"] == "Rationale"

    def test_from_dict(self):
        """Test creating from dict."""
        data = {"goal": "Test goal", "rationale": "Test rationale"}
        intent_data = IntentData.from_dict(data)
        assert intent_data.goal == "Test goal"
        assert intent_data.rationale == "Test rationale"

    def test_from_dict_defaults(self):
        """Test creating from empty dict uses defaults."""
        intent_data = IntentData.from_dict({})
        assert intent_data.goal == ""
        assert intent_data.rationale == ""

    def test_roundtrip_dict_conversion(self):
        """Test that to_dict -> from_dict preserves data."""
        original = IntentData(goal="Goal", rationale="Rationale")
        restored = IntentData.from_dict(original.to_dict())
        assert restored.goal == original.goal
        assert restored.rationale == original.rationale


class TestIntent:
    """Tests for Intent dataclass."""

    def test_create_basic_intent(self):
        """Test creating a basic intent."""
        intent = Intent(task_id="task-001")
        assert intent.task_id == "task-001"
        assert isinstance(intent.intent, IntentData)
        assert intent.commits == []
        assert intent.related_adr is None
        assert intent.created_at is not None
        assert intent.updated_at is None

    def test_create_intent_with_all_fields(self):
        """Test creating intent with all fields."""
        intent_data = IntentData(goal="Add API", rationale="Needed for integration")
        commits = [Commit(hash="abc", message="Initial")]
        intent = Intent(
            task_id="task-002",
            intent=intent_data,
            commits=commits,
            related_adr="adr-001",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        assert intent.task_id == "task-002"
        assert intent.intent.goal == "Add API"
        assert len(intent.commits) == 1
        assert intent.related_adr == "adr-001"
        assert intent.created_at == "2024-01-01T00:00:00"
        assert intent.updated_at == "2024-01-02T00:00:00"

    def test_post_init_converts_dict_to_intent_data(self):
        """Test that post_init converts dict to IntentData."""
        intent = Intent(
            task_id="task-001",
            intent={"goal": "Test", "rationale": "Testing"}  # type: ignore
        )
        assert isinstance(intent.intent, IntentData)
        assert intent.intent.goal == "Test"
        assert intent.intent.rationale == "Testing"

    def test_post_init_sets_created_at(self):
        """Test that post_init sets created_at when None."""
        intent = Intent(task_id="task-001")
        assert intent.created_at is not None
        datetime.fromisoformat(intent.created_at)

    def test_to_dict(self):
        """Test converting intent to dict."""
        intent_data = IntentData(goal="Goal", rationale="Rationale")
        commit = Commit(hash="abc", message="msg", timestamp="2024-01-01T00:00:00")
        intent = Intent(
            task_id="task-001",
            intent=intent_data,
            commits=[commit],
            related_adr="adr-001",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        d = intent.to_dict()
        assert d["task_id"] == "task-001"
        assert d["intent"]["goal"] == "Goal"
        assert d["intent"]["rationale"] == "Rationale"
        assert len(d["commits"]) == 1
        assert d["commits"][0]["hash"] == "abc"
        assert d["related_adr"] == "adr-001"
        assert d["created_at"] == "2024-01-01T00:00:00"
        assert d["updated_at"] == "2024-01-02T00:00:00"

    def test_to_dict_without_related_adr(self):
        """Test that related_adr is excluded when None."""
        intent = Intent(task_id="task-001")
        d = intent.to_dict()
        assert "related_adr" not in d

    def test_from_dict(self):
        """Test creating intent from dict."""
        data = {
            "task_id": "task-001",
            "intent": {"goal": "Test goal", "rationale": "Test rationale"},
            "commits": [
                {"hash": "abc", "message": "msg", "timestamp": "2024-01-01T00:00:00"}
            ],
            "related_adr": "adr-002",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }
        intent = Intent.from_dict(data)
        assert intent.task_id == "task-001"
        assert intent.intent.goal == "Test goal"
        assert intent.intent.rationale == "Test rationale"
        assert len(intent.commits) == 1
        assert intent.commits[0].hash == "abc"
        assert intent.related_adr == "adr-002"
        assert intent.created_at == "2024-01-01T00:00:00"
        assert intent.updated_at == "2024-01-02T00:00:00"

    def test_from_dict_defaults(self):
        """Test creating intent from empty dict uses defaults."""
        intent = Intent.from_dict({})
        assert intent.task_id == "unknown"
        assert isinstance(intent.intent, IntentData)
        assert intent.commits == []
        assert intent.related_adr is None

    def test_from_dict_with_non_dict_intent(self):
        """Test from_dict handles non-dict intent value."""
        data = {"task_id": "task-001", "intent": "invalid"}
        intent = Intent.from_dict(data)
        assert isinstance(intent.intent, IntentData)
        assert intent.intent.goal == ""

    def test_add_commit_success(self):
        """Test adding a new commit."""
        intent = Intent(task_id="task-001")
        result = intent.add_commit("abc123", "First commit")
        assert result is True
        assert len(intent.commits) == 1
        assert intent.commits[0].hash == "abc123"
        assert intent.commits[0].message == "First commit"
        assert intent.updated_at is not None

    def test_add_commit_duplicate(self):
        """Test that duplicate commits are not added."""
        intent = Intent(task_id="task-001")
        intent.add_commit("abc123", "First commit")
        original_updated_at = intent.updated_at

        result = intent.add_commit("abc123", "Duplicate commit")
        assert result is False
        assert len(intent.commits) == 1
        assert intent.updated_at == original_updated_at

    def test_add_multiple_commits(self):
        """Test adding multiple different commits."""
        intent = Intent(task_id="task-001")
        intent.add_commit("abc", "First")
        intent.add_commit("def", "Second")
        intent.add_commit("ghi", "Third")

        assert len(intent.commits) == 3
        hashes = [c.hash for c in intent.commits]
        assert hashes == ["abc", "def", "ghi"]

    def test_roundtrip_dict_conversion(self):
        """Test that to_dict -> from_dict preserves data."""
        intent_data = IntentData(goal="Goal", rationale="Rationale")
        original = Intent(
            task_id="task-001",
            intent=intent_data,
            commits=[Commit(hash="abc", message="msg", timestamp="2024-01-01T00:00:00")],
            related_adr="adr-001",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        restored = Intent.from_dict(original.to_dict())

        assert restored.task_id == original.task_id
        assert restored.intent.goal == original.intent.goal
        assert restored.intent.rationale == original.intent.rationale
        assert len(restored.commits) == len(original.commits)
        assert restored.commits[0].hash == original.commits[0].hash
        assert restored.related_adr == original.related_adr
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at
