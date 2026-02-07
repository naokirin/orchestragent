"""Tests for tracking.adr_manager (ADRManager)."""

import pytest

from orchestragent.tracking.adr_manager import ADRManager


class TestADRManagerInit:
    """Tests for ADRManager initialization."""

    def test_init_creates_adr_directory(self, temp_dir):
        """Create ADR directory on init."""
        adr_dir = temp_dir / "docs" / "adr"
        ADRManager(adr_dir=str(adr_dir))

        assert adr_dir.exists()

    def test_init_creates_template_file(self, temp_dir):
        """Create template file on init."""
        adr_dir = temp_dir / "adr"
        ADRManager(adr_dir=str(adr_dir))

        template_path = adr_dir / "template.md"
        assert template_path.exists()

    def test_init_does_not_overwrite_existing_template(self, temp_dir):
        """Do not overwrite existing template."""
        adr_dir = temp_dir / "adr"
        adr_dir.mkdir(parents=True)
        template_path = adr_dir / "template.md"
        template_path.write_text("Custom template content")

        ADRManager(adr_dir=str(adr_dir))

        assert template_path.read_text() == "Custom template content"


class TestADRManagerGetNextNumber:
    """Tests for ADRManager.get_next_number."""

    def test_get_next_number_empty_dir(self, temp_dir):
        """Return 1 when no ADRs."""
        manager = ADRManager(adr_dir=str(temp_dir / "adr"))

        assert manager.get_next_number() == 1

    def test_get_next_number_with_existing_adrs(self, temp_dir):
        """Return max+1 when existing ADRs present."""
        adr_dir = temp_dir / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "0001-first-decision.md").touch()
        (adr_dir / "0003-third-decision.md").touch()

        manager = ADRManager(adr_dir=str(adr_dir))

        assert manager.get_next_number() == 4


class TestADRManagerCreateAdr:
    """Tests for ADRManager.create_adr."""

    @pytest.fixture
    def adr_manager(self, temp_dir):
        return ADRManager(adr_dir=str(temp_dir / "adr"))

    def test_create_adr_returns_number(self, adr_manager):
        """Return ADR number."""
        number = adr_manager.create_adr(title="Use Factory Pattern")

        assert number == "0001"

    def test_create_adr_creates_file(self, adr_manager, temp_dir):
        """Create ADR file."""
        adr_manager.create_adr(title="Use Factory Pattern")

        adr_files = list((temp_dir / "adr").glob("0001-*.md"))
        assert len(adr_files) == 1

    def test_create_adr_with_full_content(self, adr_manager):
        """Create ADR with all sections."""
        number = adr_manager.create_adr(
            title="Use Dependency Injection",
            context="Need flexible testing",
            decision="Use constructor injection",
            rationale="Easy to mock",
            consequences="More verbose constructors",
            related_intents=["task-001", "task-002"],
            status="Accepted",
        )

        adr = adr_manager.get_adr(number)
        assert adr["title"] == "Use Dependency Injection"
        assert adr["status"] == "Accepted"
        assert "Need flexible testing" in adr["context"]
        assert "task-001" in adr["related_intents"]

    def test_create_adr_increments_number(self, adr_manager):
        """Number increments on consecutive creates."""
        num1 = adr_manager.create_adr(title="First")
        num2 = adr_manager.create_adr(title="Second")

        assert num1 == "0001"
        assert num2 == "0002"


class TestADRManagerGetAdr:
    """Tests for ADRManager.get_adr."""

    @pytest.fixture
    def adr_manager(self, temp_dir):
        return ADRManager(adr_dir=str(temp_dir / "adr"))

    def test_get_adr_returns_parsed_content(self, adr_manager):
        """Parse and return ADR content."""
        number = adr_manager.create_adr(
            title="Test Decision",
            context="Test context",
            decision="Test decision",
        )

        adr = adr_manager.get_adr(number)

        assert adr["number"] == "0001"
        assert adr["title"] == "Test Decision"
        assert "Test context" in adr["context"]

    def test_get_adr_nonexistent_returns_none(self, adr_manager):
        """Return None for nonexistent ADR."""
        adr = adr_manager.get_adr("9999")

        assert adr is None

    def test_get_adr_normalizes_number(self, adr_manager):
        """Normalize number with zero-padding."""
        adr_manager.create_adr(title="Test")

        adr = adr_manager.get_adr("1")  # fetch with "1" not "0001"

        assert adr is not None
        assert adr["number"] == "0001"


class TestADRManagerGetAllAdrs:
    """Tests for ADRManager.get_all_adrs."""

    @pytest.fixture
    def adr_manager(self, temp_dir):
        return ADRManager(adr_dir=str(temp_dir / "adr"))

    def test_get_all_adrs_empty(self, adr_manager):
        """Return empty list when no ADRs."""
        adrs = adr_manager.get_all_adrs()

        assert adrs == []

    def test_get_all_adrs_returns_sorted(self, adr_manager):
        """Return ADR list sorted by number."""
        adr_manager.create_adr(title="Third")
        adr_manager.create_adr(title="First")

        adrs = adr_manager.get_all_adrs()

        assert len(adrs) == 2
        assert adrs[0]["number"] == "0001"
        assert adrs[1]["number"] == "0002"


class TestADRManagerUpdateStatus:
    """Tests for ADRManager.update_adr_status."""

    @pytest.fixture
    def adr_manager(self, temp_dir):
        return ADRManager(adr_dir=str(temp_dir / "adr"))

    def test_update_adr_status_success(self, adr_manager):
        """Can update status."""
        number = adr_manager.create_adr(title="Test", status="Proposed")

        result = adr_manager.update_adr_status(number, "Accepted")

        assert result is True
        adr = adr_manager.get_adr(number)
        assert adr["status"] == "Accepted"

    def test_update_adr_status_nonexistent_returns_false(self, adr_manager):
        """Return False when updating nonexistent ADR."""
        result = adr_manager.update_adr_status("9999", "Accepted")

        assert result is False


class TestADRManagerAddRelatedIntent:
    """Tests for ADRManager.add_related_intent."""

    @pytest.fixture
    def adr_manager(self, temp_dir):
        return ADRManager(adr_dir=str(temp_dir / "adr"))

    def test_add_related_intent_success(self, adr_manager):
        """Can add related Intent."""
        number = adr_manager.create_adr(title="Test")

        result = adr_manager.add_related_intent(number, "task-001")

        assert result is True
        adr = adr_manager.get_adr(number)
        assert "task-001" in adr["related_intents"]

    def test_add_related_intent_duplicate_returns_true(self, adr_manager):
        """Duplicate add returns True and does not duplicate."""
        number = adr_manager.create_adr(
            title="Test",
            related_intents=["task-001"],
        )

        result = adr_manager.add_related_intent(number, "task-001")

        assert result is True
        adr = adr_manager.get_adr(number)
        assert adr["related_intents"].count("task-001") == 1

    def test_add_related_intent_nonexistent_returns_false(self, adr_manager):
        """Return False when adding to nonexistent ADR."""
        result = adr_manager.add_related_intent("9999", "task-001")

        assert result is False

    def test_add_related_intent_replaces_none(self, adr_manager):
        """Can add Intent replacing 'None'."""
        number = adr_manager.create_adr(title="Test")  # default is 'None'

        result = adr_manager.add_related_intent(number, "task-001")

        assert result is True
        adr = adr_manager.get_adr(number)
        assert "task-001" in adr["related_intents"]
        assert "なし" not in adr["related_intents"]


class TestADRManagerSlugify:
    """Tests for ADRManager._slugify."""

    def test_slugify_basic(self):
        """Basic slugify."""
        result = ADRManager._slugify("Use Factory Pattern")

        assert result == "use-factory-pattern"

    def test_slugify_removes_special_chars(self):
        """Remove special characters."""
        result = ADRManager._slugify("Hello! World? #Test")

        assert result == "hello-world-test"

    def test_slugify_truncates_long_text(self):
        """Truncate long text to 50 chars."""
        long_text = "a" * 100
        result = ADRManager._slugify(long_text)

        assert len(result) <= 50

    def test_slugify_handles_japanese(self):
        """Japanese remains (after special char removal)."""
        result = ADRManager._slugify("ファクトリパターンを使用")

        # Japanese matches \w so it remains
        assert len(result) > 0
