"""Base agent class."""

import time
from typing import Dict, Any, Optional
from utils.llm_client import LLMClient
from utils.state_manager import StateManager
from utils.logger import AgentLogger
from utils.exceptions import AgentError, LLMError


class BaseAgent:
    """Base class for all agents."""
    
    def __init__(
        self,
        name: str,
        llm_client: LLMClient,
        state_manager: StateManager,
        logger: AgentLogger,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize base agent.
        
        Args:
            name: Agent name
            llm_client: LLM client instance
            state_manager: State manager instance
            logger: Logger instance
            config: Configuration dictionary
        """
        self.name = name
        self.llm_client = llm_client
        self.state_manager = state_manager
        self.logger = logger
        self.config = config or {}
        self.mode = self.config.get("mode", "agent")
    
    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        Build prompt from current state.
        
        Args:
            state: Current state dictionary
        
        Returns:
            Prompt string
        """
        raise NotImplementedError("Subclasses must implement build_prompt")
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse agent response.
        
        Args:
            response: Agent response string
        
        Returns:
            Parsed result dictionary
        """
        # Default implementation: return response as-is
        return {"response": response}
    
    def update_state(self, result: Dict[str, Any]) -> None:
        """
        Update state with result.
        
        Args:
            result: Parsed result dictionary
        """
        raise NotImplementedError("Subclasses must implement update_state")
    
    def run(self, iteration: int = 0, max_retries: int = 3) -> Dict[str, Any]:
        """
        Run agent with retry logic.
        
        Args:
            iteration: Current iteration number
            max_retries: Maximum number of retries for retryable errors
        
        Returns:
            Result dictionary
        
        Raises:
            AgentError: If agent execution fails after all retries
        """
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                return self._run_internal(iteration, start_time)
            except LLMError as e:
                if e.retryable and attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s, ...
                    self.logger.warning(
                        f"[{self.name}] LLM error (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time} seconds: {e}"
                    )
                    time.sleep(wait_time)
                    continue
                # Not retryable or max retries reached
                self.logger.log_error_with_traceback(
                    self.name,
                    e,
                    context={
                        "iteration": iteration,
                        "attempt": attempt + 1,
                        "max_retries": max_retries
                    }
                )
                raise
            except AgentError as e:
                # Other agent errors are not retryable
                self.logger.log_error_with_traceback(
                    self.name,
                    e,
                    context={"iteration": iteration}
                )
                raise
            except Exception as e:
                # Unexpected errors
                self.logger.log_error_with_traceback(
                    self.name,
                    e,
                    context={"iteration": iteration}
                )
                # Wrap in AgentError
                raise AgentError(f"Unexpected error: {e}", retryable=False, original_error=e)
    
    def _run_internal(self, iteration: int, start_time: float) -> Dict[str, Any]:
        """
        Internal run method (without retry logic).
        
        Args:
            iteration: Current iteration number
            start_time: Start time for duration calculation
        
        Returns:
            Result dictionary
        """
        # 1. Load state
        state = self.load_state()
        
        # 2. Build prompt
        prompt = self.build_prompt(state)
        
        # 3. Call LLM
        # Log which model/mode this agent will use for this run
        current_model = self.config.get("model") or "default"
        self.logger.info(
            f"[{self.name}] Starting run "
            f"(mode={self.mode}, model={current_model}, iteration={iteration})"
        )
        response = self.llm_client.call_agent(
            prompt=prompt,
            mode=self.mode,
            model=self.config.get("model"),
            agent_name=self.name,
            logger=self.logger
        )
        
        # 4. Parse response
        try:
            result = self.parse_response(response)
            # Ensure result is a dictionary
            if not isinstance(result, dict):
                raise ValueError(f"parse_response() must return a dict, got {type(result)}")
        except Exception as e:
            self.logger.error(f"[{self.name}] Error parsing response: {e}")
            # Create a fallback result
            result = {
                "response": response,
                "error": str(e)
            }
        
        # 5. Update state
        try:
            self.update_state(result)
        except Exception as e:
            self.logger.error(f"[{self.name}] Error updating state: {e}")
            raise
        
        # 6. Log
        duration = time.time() - start_time
        self.logger.log_agent_run(
            agent_name=self.name,
            iteration=iteration,
            prompt=prompt,
            response=response,
            duration=duration,
            mode=self.mode,
            model=self.config.get("model")
        )
        
        return result
    
    def load_state(self) -> Dict[str, Any]:
        """
        Load current state.
        
        Returns:
            State dictionary
        """
        return {
            "plan": self.state_manager.get_plan(),
            "tasks": self.state_manager.get_tasks(),
            "status": self.state_manager.get_status()
        }
