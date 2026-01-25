"""Base agent class."""

import time
from typing import Dict, Any, Optional
from utils.llm_client import LLMClient
from utils.state_manager import StateManager
from utils.logger import AgentLogger


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
    
    def run(self, iteration: int = 0) -> Dict[str, Any]:
        """
        Run agent.
        
        Args:
            iteration: Current iteration number
        
        Returns:
            Result dictionary
        """
        start_time = time.time()
        
        try:
            # 1. Load state
            state = self.load_state()
            
            # 2. Build prompt
            prompt = self.build_prompt(state)
            
            # 3. Call LLM
            self.logger.info(f"[{self.name}] Calling LLM...")
            response = self.llm_client.call_agent(
                prompt=prompt,
                mode=self.mode,
                model=self.config.get("model")
            )
            
            # 4. Parse response
            result = self.parse_response(response)
            
            # 5. Update state
            self.update_state(result)
            
            # 6. Log
            duration = time.time() - start_time
            self.logger.log_agent_run(
                agent_name=self.name,
                iteration=iteration,
                prompt=prompt,
                response=response,
                duration=duration
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"[{self.name}] Error: {e}")
            raise
    
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
