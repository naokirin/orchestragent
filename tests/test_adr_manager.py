"""Tests for tracking.adr_manager (ADRManager)."""

import pytest
from pathlib import Path

from orchestragent.tracking.adr_manager import ADRManager


class TestADRManagerInit:
    """Tests for ADRManager initialization."""

    def test_init_creates_adr_directory(self, temp_dir):
        """初期化時に ADR ディレクトリを作成する。"""
        adr_dir = temp_dir / "docs" / "adr"
        manager = ADRManager(adr_dir=str(adr_dir))

        assert adr_dir.exists()

    def test_init_creates_template_file(self, temp_dir):
        """初期化時にテンプレートファイルを作成する。"""
        adr_dir = temp_dir / "adr"
        manager = ADRManager(adr_dir=str(adr_dir))

        template_path = adr_dir / "template.md"
        assert template_path.exists()

    def test_init_does_not_overwrite_existing_template(self, temp_dir):
        """既存のテンプレートは上書きしない。"""
        adr_dir = temp_dir / "adr"
        adr_dir.mkdir(parents=True)
        template_path = adr_dir / "template.md"
        template_path.write_text("Custom template content")

        manager = ADRManager(adr_dir=str(adr_dir))

        assert template_path.read_text() == "Custom template content"


class TestADRManagerGetNextNumber:
    """Tests for ADRManager.get_next_number."""

    def test_get_next_number_empty_dir(self, temp_dir):
        """ADR がない場合は 1 を返す。"""
        manager = ADRManager(adr_dir=str(temp_dir / "adr"))

        assert manager.get_next_number() == 1

    def test_get_next_number_with_existing_adrs(self, temp_dir):
        """既存 ADR がある場合は最大 + 1 を返す。"""
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
        """ADR 番号を返す。"""
        number = adr_manager.create_adr(title="Use Factory Pattern")

        assert number == "0001"

    def test_create_adr_creates_file(self, adr_manager, temp_dir):
        """ADR ファイルを作成する。"""
        adr_manager.create_adr(title="Use Factory Pattern")

        adr_files = list((temp_dir / "adr").glob("0001-*.md"))
        assert len(adr_files) == 1

    def test_create_adr_with_full_content(self, adr_manager):
        """全てのセクションを含む ADR を作成する。"""
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
        """連続作成時に番号がインクリメントされる。"""
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
        """ADR の内容をパースして返す。"""
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
        """存在しない ADR は None を返す。"""
        adr = adr_manager.get_adr("9999")

        assert adr is None

    def test_get_adr_normalizes_number(self, adr_manager):
        """番号をゼロ埋めで正規化する。"""
        adr_manager.create_adr(title="Test")

        adr = adr_manager.get_adr("1")  # "0001" ではなく "1" で取得

        assert adr is not None
        assert adr["number"] == "0001"


class TestADRManagerGetAllAdrs:
    """Tests for ADRManager.get_all_adrs."""

    @pytest.fixture
    def adr_manager(self, temp_dir):
        return ADRManager(adr_dir=str(temp_dir / "adr"))

    def test_get_all_adrs_empty(self, adr_manager):
        """ADR がない場合は空リストを返す。"""
        adrs = adr_manager.get_all_adrs()

        assert adrs == []

    def test_get_all_adrs_returns_sorted(self, adr_manager):
        """番号順にソートされた ADR リストを返す。"""
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
        """ステータスを更新できる。"""
        number = adr_manager.create_adr(title="Test", status="Proposed")

        result = adr_manager.update_adr_status(number, "Accepted")

        assert result is True
        adr = adr_manager.get_adr(number)
        assert adr["status"] == "Accepted"

    def test_update_adr_status_nonexistent_returns_false(self, adr_manager):
        """存在しない ADR の更新は False を返す。"""
        result = adr_manager.update_adr_status("9999", "Accepted")

        assert result is False


class TestADRManagerAddRelatedIntent:
    """Tests for ADRManager.add_related_intent."""

    @pytest.fixture
    def adr_manager(self, temp_dir):
        return ADRManager(adr_dir=str(temp_dir / "adr"))

    def test_add_related_intent_success(self, adr_manager):
        """関連 Intent を追加できる。"""
        number = adr_manager.create_adr(title="Test")

        result = adr_manager.add_related_intent(number, "task-001")

        assert result is True
        adr = adr_manager.get_adr(number)
        assert "task-001" in adr["related_intents"]

    def test_add_related_intent_duplicate_returns_true(self, adr_manager):
        """重複追加は True を返し、重複しない。"""
        number = adr_manager.create_adr(
            title="Test",
            related_intents=["task-001"],
        )

        result = adr_manager.add_related_intent(number, "task-001")

        assert result is True
        adr = adr_manager.get_adr(number)
        assert adr["related_intents"].count("task-001") == 1

    def test_add_related_intent_nonexistent_returns_false(self, adr_manager):
        """存在しない ADR への追加は False を返す。"""
        result = adr_manager.add_related_intent("9999", "task-001")

        assert result is False

    def test_add_related_intent_replaces_none(self, adr_manager):
        """「なし」を置き換えて Intent を追加できる。"""
        number = adr_manager.create_adr(title="Test")  # デフォルトは「なし」

        result = adr_manager.add_related_intent(number, "task-001")

        assert result is True
        adr = adr_manager.get_adr(number)
        assert "task-001" in adr["related_intents"]
        assert "なし" not in adr["related_intents"]


class TestADRManagerSlugify:
    """Tests for ADRManager._slugify."""

    def test_slugify_basic(self):
        """基本的なスラグ化。"""
        result = ADRManager._slugify("Use Factory Pattern")

        assert result == "use-factory-pattern"

    def test_slugify_removes_special_chars(self):
        """特殊文字を除去する。"""
        result = ADRManager._slugify("Hello! World? #Test")

        assert result == "hello-world-test"

    def test_slugify_truncates_long_text(self):
        """長いテキストは 50 文字に切り詰める。"""
        long_text = "a" * 100
        result = ADRManager._slugify(long_text)

        assert len(result) <= 50

    def test_slugify_handles_japanese(self):
        """日本語はそのまま（特殊文字除去後）。"""
        result = ADRManager._slugify("ファクトリパターンを使用")

        # 日本語は \w にマッチするため残る
        assert len(result) > 0
