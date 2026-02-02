"""Tests for BaseAgent class."""

import pytest
import time
from unittest.mock import MagicMock, patch

from orchestragent.agents.base import BaseAgent
from orchestragent.core.exceptions import AgentError, LLMError


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    def build_prompt(self, state):
        return f"Test prompt with state: {state}"

    def parse_response(self, response):
        return {"parsed": response}

    def update_state(self, result):
        self.state_manager.save_json("test_result.json", result)


class TestBaseAgent:
    """Tests for BaseAgent class."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.call_agent.return_value = "Test response"
        return client

    @pytest.fixture
    def mock_state_manager(self):
        """Create a mock state manager."""
        manager = MagicMock()
        manager.get_plan.return_value = {"goal": "Test goal"}
        manager.get_tasks.return_value = []
        manager.get_status.return_value = {"status": "running"}
        return manager

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def agent(self, mock_llm_client, mock_state_manager, mock_logger):
        """Create a ConcreteAgent instance."""
        return ConcreteAgent(
            name="test_agent",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger,
            config={"mode": "agent", "model": "test-model"}
        )

    def test_init(self, mock_llm_client, mock_state_manager, mock_logger):
        """Test BaseAgent initialization."""
        agent = ConcreteAgent(
            name="test_agent",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )
        assert agent.name == "test_agent"
        assert agent.llm_client is mock_llm_client
        assert agent.state_manager is mock_state_manager
        assert agent.logger is mock_logger
        assert agent.config == {}
        assert agent.mode == "agent"

    def test_init_with_config(self, mock_llm_client, mock_state_manager, mock_logger):
        """Test BaseAgent initialization with config."""
        agent = ConcreteAgent(
            name="test_agent",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger,
            config={"mode": "chat", "model": "gpt-4"}
        )
        assert agent.mode == "chat"
        assert agent.config["model"] == "gpt-4"


class TestLoadState:
    """Tests for load_state method."""

    @pytest.fixture
    def agent(self):
        mock_llm_client = MagicMock()
        mock_state_manager = MagicMock()
        mock_state_manager.get_plan.return_value = {"goal": "Test"}
        mock_state_manager.get_tasks.return_value = [{"id": "t1"}]
        mock_state_manager.get_status.return_value = {"status": "running"}
        mock_logger = MagicMock()
        return ConcreteAgent(
            name="test",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )

    def test_load_state(self, agent):
        """Test load_state returns state dictionary."""
        state = agent.load_state()

        assert "plan" in state
        assert "tasks" in state
        assert "status" in state
        assert state["plan"]["goal"] == "Test"
        assert len(state["tasks"]) == 1


class TestParseResponse:
    """Tests for parse_response method."""

    @pytest.fixture
    def agent(self):
        mock_llm_client = MagicMock()
        mock_state_manager = MagicMock()
        mock_logger = MagicMock()
        return ConcreteAgent(
            name="test",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )

    def test_parse_response_default(self, agent):
        """Test default parse_response returns response in dict."""
        result = agent.parse_response("test response")
        assert result == {"parsed": "test response"}


class TestRun:
    """Tests for run method."""

    @pytest.fixture
    def mock_llm_client(self):
        client = MagicMock()
        client.call_agent.return_value = "Test response"
        return client

    @pytest.fixture
    def mock_state_manager(self):
        manager = MagicMock()
        manager.get_plan.return_value = {}
        manager.get_tasks.return_value = []
        manager.get_status.return_value = {}
        return manager

    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def agent(self, mock_llm_client, mock_state_manager, mock_logger):
        return ConcreteAgent(
            name="test_agent",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )

    def test_run_success(self, agent):
        """Test successful run."""
        result = agent.run(iteration=0)

        assert "parsed" in result
        assert result["parsed"] == "Test response"
        agent.llm_client.call_agent.assert_called_once()
        agent.logger.log_agent_run.assert_called_once()

    def test_run_calls_llm_with_correct_params(self, agent):
        """Test run calls LLM with correct parameters."""
        agent.run(iteration=1)

        call_args = agent.llm_client.call_agent.call_args
        assert "prompt" in call_args.kwargs
        assert call_args.kwargs["mode"] == "agent"
        assert call_args.kwargs["agent_name"] == "test_agent"

    def test_run_logs_agent_run(self, agent):
        """Test run logs the agent run."""
        agent.run(iteration=2)

        log_call = agent.logger.log_agent_run.call_args
        assert log_call.kwargs["agent_name"] == "test_agent"
        assert log_call.kwargs["iteration"] == 2
        assert "duration" in log_call.kwargs


class TestRunRetry:
    """Tests for run retry logic."""

    @pytest.fixture
    def mock_state_manager(self):
        manager = MagicMock()
        manager.get_plan.return_value = {}
        manager.get_tasks.return_value = []
        manager.get_status.return_value = {}
        return manager

    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    def test_run_retries_on_retryable_error(self, mock_state_manager, mock_logger):
        """Test that run retries on retryable LLMError."""
        mock_llm_client = MagicMock()
        # First call raises retryable error, second succeeds
        mock_llm_client.call_agent.side_effect = [
            LLMError("Temporary error", retryable=True),
            "Success response"
        ]

        agent = ConcreteAgent(
            name="test",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )

        with patch("time.sleep"):  # Skip actual sleep
            result = agent.run(iteration=0, max_retries=3)

        assert result["parsed"] == "Success response"
        assert mock_llm_client.call_agent.call_count == 2

    def test_run_fails_on_non_retryable_error(self, mock_state_manager, mock_logger):
        """Test that run fails immediately on non-retryable LLMError."""
        mock_llm_client = MagicMock()
        mock_llm_client.call_agent.side_effect = LLMError("Fatal error", retryable=False)

        agent = ConcreteAgent(
            name="test",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )

        with pytest.raises(LLMError) as exc_info:
            agent.run(iteration=0, max_retries=3)

        assert "Fatal error" in str(exc_info.value)
        # Should only be called once (no retry)
        assert mock_llm_client.call_agent.call_count == 1

    def test_run_fails_after_max_retries(self, mock_state_manager, mock_logger):
        """Test that run fails after max retries exhausted."""
        mock_llm_client = MagicMock()
        mock_llm_client.call_agent.side_effect = LLMError("Persistent error", retryable=True)

        agent = ConcreteAgent(
            name="test",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )

        with patch("time.sleep"):  # Skip actual sleep
            with pytest.raises(LLMError):
                agent.run(iteration=0, max_retries=3)

        assert mock_llm_client.call_agent.call_count == 3

    def test_run_max_retries_zero_raises_exhausted(self, mock_state_manager, mock_logger):
        """異常系: max_retries=0 のときループに入らず AgentError(exhausted) を送出。"""
        mock_llm_client = MagicMock()
        mock_llm_client.call_agent.side_effect = LLMError("Retryable", retryable=True)

        agent = ConcreteAgent(
            name="test",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )

        with pytest.raises(AgentError) as exc_info:
            agent.run(iteration=0, max_retries=0)

        assert "exhausted" in str(exc_info.value).lower()
        assert exc_info.value.retryable is False
        assert mock_llm_client.call_agent.call_count == 0

    def test_run_wraps_unexpected_error(self, mock_state_manager, mock_logger):
        """Test that unexpected errors are wrapped in AgentError."""
        mock_llm_client = MagicMock()
        mock_llm_client.call_agent.side_effect = ValueError("Unexpected")

        agent = ConcreteAgent(
            name="test",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )

        with pytest.raises(AgentError) as exc_info:
            agent.run(iteration=0)

        assert "Unexpected" in str(exc_info.value)
        assert exc_info.value.retryable is False


class TestRunInternal:
    """Tests for _run_internal method."""

    @pytest.fixture
    def mock_llm_client(self):
        client = MagicMock()
        client.call_agent.return_value = "Response"
        return client

    @pytest.fixture
    def mock_state_manager(self):
        manager = MagicMock()
        manager.get_plan.return_value = {}
        manager.get_tasks.return_value = []
        manager.get_status.return_value = {}
        return manager

    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    def test_run_internal_handles_parse_error(self, mock_llm_client, mock_state_manager, mock_logger):
        """Test _run_internal handles parse_response errors."""
        class FailingParseAgent(BaseAgent):
            def build_prompt(self, state):
                return "prompt"

            def parse_response(self, response):
                raise ValueError("Parse failed")

            def update_state(self, result):
                pass

        agent = FailingParseAgent(
            name="test",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )

        result = agent._run_internal(iteration=0, start_time=time.time())

        # Should return fallback result
        assert "response" in result
        assert "error" in result
        mock_logger.error.assert_called()

    def test_run_internal_handles_update_state_error(self, mock_llm_client, mock_state_manager, mock_logger):
        """Test _run_internal raises on update_state errors."""
        class FailingUpdateAgent(BaseAgent):
            def build_prompt(self, state):
                return "prompt"

            def parse_response(self, response):
                return {"data": response}

            def update_state(self, result):
                raise RuntimeError("Update failed")

        agent = FailingUpdateAgent(
            name="test",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )

        with pytest.raises(RuntimeError):
            agent._run_internal(iteration=0, start_time=time.time())

        mock_logger.error.assert_called()

    def test_run_internal_parse_response_returns_non_dict_uses_fallback(self, mock_llm_client, mock_state_manager, mock_logger):
        """異常系: parse_response が dict 以外を返すと ValueError となりフォールバック結果が使われる。"""
        class BadParseAgent(BaseAgent):
            def build_prompt(self, state):
                return "prompt"

            def parse_response(self, response):
                return "not a dict"  # 仕様違反

            def update_state(self, result):
                # フォールバックで {"response": ..., "error": ...} が渡る
                assert "response" in result
                assert "error" in result

        agent = BadParseAgent(
            name="test",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )
        result = agent._run_internal(iteration=0, start_time=time.time())
        assert "response" in result
        assert "error" in result
        mock_logger.error.assert_called()


class TestBuildPromptNotImplemented:
    """Tests for build_prompt NotImplementedError."""

    def test_build_prompt_not_implemented(self):
        """Test that BaseAgent.build_prompt raises NotImplementedError."""
        mock_llm_client = MagicMock()
        mock_state_manager = MagicMock()
        mock_logger = MagicMock()

        # Create BaseAgent directly (not concrete implementation)
        agent = BaseAgent(
            name="test",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )

        with pytest.raises(NotImplementedError):
            agent.build_prompt({})


class TestUpdateStateNotImplemented:
    """Tests for update_state NotImplementedError."""

    def test_update_state_not_implemented(self):
        """Test that BaseAgent.update_state raises NotImplementedError."""
        mock_llm_client = MagicMock()
        mock_state_manager = MagicMock()
        mock_logger = MagicMock()

        agent = BaseAgent(
            name="test",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )

        with pytest.raises(NotImplementedError):
            agent.update_state({})


class TestDefaultParseResponse:
    """Tests for default parse_response behavior."""

    def test_default_parse_response(self):
        """Test BaseAgent's default parse_response returns response in dict."""
        mock_llm_client = MagicMock()
        mock_state_manager = MagicMock()
        mock_logger = MagicMock()

        agent = BaseAgent(
            name="test",
            llm_client=mock_llm_client,
            state_manager=mock_state_manager,
            logger=mock_logger
        )

        result = agent.parse_response("test response")
        assert result == {"response": "test response"}
