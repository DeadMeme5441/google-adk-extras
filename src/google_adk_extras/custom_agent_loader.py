"""CustomAgentLoader - Enhanced agent loader for programmatic agent management.

This module provides CustomAgentLoader which extends Google ADK's agent loading
capabilities to support programmatically registered agent instances with
thread-safe registry management.
"""

import logging
import threading
from typing import Dict, List, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.cli.utils.base_agent_loader import BaseAgentLoader

logger = logging.getLogger(__name__)


class CustomAgentLoader(BaseAgentLoader):
    """Enhanced agent loader for programmatic agent management.
    
    This loader allows you to:
    1. Register agent instances directly for programmatic control
    2. Dynamically add/remove agents at runtime
    3. Thread-safe access to agent registry
    
    Examples:
        # Register and use agents
        loader = CustomAgentLoader()
        loader.register_agent("my_agent", my_agent_instance)
        agent = loader.load_agent("my_agent")
        
        # List all registered agents
        agents = loader.list_agents()  # ['my_agent']
    """
    
    def __init__(self):
        """Initialize CustomAgentLoader."""
        self._registered_agents: Dict[str, BaseAgent] = {}
        self._lock = threading.RLock()  # Thread-safe access to registry
        
        logger.debug("CustomAgentLoader initialized")
    
    def register_agent(self, name: str, agent: BaseAgent) -> None:
        """Register an agent instance by name.
        
        Args:
            name: Agent name for discovery and loading.
            agent: BaseAgent instance to register.
            
        Raises:
            ValueError: If name is empty or agent is not a BaseAgent instance.
        """
        if not name or not name.strip():
            raise ValueError("Agent name cannot be empty")
            
        if not isinstance(agent, BaseAgent):
            raise ValueError(f"Agent must be BaseAgent instance, got {type(agent)}")
        
        with self._lock:
            if name in self._registered_agents:
                logger.info("Replacing existing registered agent: %s", name)
            else:
                logger.info("Registering new agent instance: %s", name)
            
            self._registered_agents[name] = agent
    
    def unregister_agent(self, name: str) -> bool:
        """Unregister an agent instance by name.
        
        Args:
            name: Name of agent to unregister.
            
        Returns:
            bool: True if agent was found and removed, False otherwise.
        """
        with self._lock:
            if name in self._registered_agents:
                del self._registered_agents[name]
                logger.info("Unregistered agent instance: %s", name)
                return True
            else:
                logger.debug("Agent not found in registry: %s", name)
                return False
    
    def is_registered(self, name: str) -> bool:
        """Check if an agent is registered by name.
        
        Args:
            name: Agent name to check.
            
        Returns:
            bool: True if agent is registered, False otherwise.
        """
        with self._lock:
            return name in self._registered_agents
    
    def get_registered_agents(self) -> Dict[str, BaseAgent]:
        """Get a copy of all registered agents.
        
        Returns:
            Dict[str, BaseAgent]: Copy of registered agents mapping.
        """
        with self._lock:
            return self._registered_agents.copy()
    
    def clear_registry(self) -> None:
        """Clear all registered agents from the registry."""
        with self._lock:
            count = len(self._registered_agents)
            self._registered_agents.clear()
            logger.info("Cleared %d registered agents", count)
    
    def load_agent(self, name: str) -> BaseAgent:
        """Load an agent by name.
        
        Args:
            name: Name of agent to load.
            
        Returns:
            BaseAgent: The loaded agent instance.
            
        Raises:
            ValueError: If agent is not found in registry.
        """
        with self._lock:
            if name in self._registered_agents:
                logger.debug("Loading registered agent: %s", name)
                return self._registered_agents[name]
        
        # Agent not found
        available_agents = self.list_agents()
        raise ValueError(
            f"Agent '{name}' not found. "
            f"Available agents: {available_agents if available_agents else 'None'}"
        )
    
    def list_agents(self) -> List[str]:
        """List all available agents from registry.
        
        Returns:
            List[str]: Sorted list of all registered agent names.
        """
        with self._lock:
            agent_names = list(self._registered_agents.keys())
        
        sorted_agents = sorted(agent_names)
        logger.debug("Total registered agents: %d", len(sorted_agents))
        return sorted_agents
    
    
    def __repr__(self) -> str:
        """String representation of the loader."""
        with self._lock:
            registered_count = len(self._registered_agents)
        
        return f"CustomAgentLoader(registered={registered_count})"