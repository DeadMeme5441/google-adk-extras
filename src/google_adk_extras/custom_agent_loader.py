"""CustomAgentLoader - Enhanced agent loader supporting both instances and directories.

This module provides CustomAgentLoader which extends Google ADK's agent loading
capabilities to support both programmatically registered agent instances and
traditional directory-based agent discovery.
"""

import logging
import threading
from typing import Dict, List, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.cli.utils.base_agent_loader import BaseAgentLoader

logger = logging.getLogger(__name__)


class CustomAgentLoader(BaseAgentLoader):
    """Enhanced agent loader supporting both agent instances and directory fallback.
    
    This loader allows you to:
    1. Register agent instances directly for programmatic control
    2. Fall back to directory-based loading for traditional workflows  
    3. Mix both approaches in a single application
    4. Dynamically add/remove agents at runtime
    
    The loader checks registered instances first, then falls back to the
    optional directory-based loader for discovery and loading.
    
    Examples:
        # Instance-only mode
        loader = CustomAgentLoader()
        loader.register_agent("my_agent", my_agent_instance)
        
        # Hybrid mode with directory fallback
        directory_loader = AgentLoader("./agents")
        loader = CustomAgentLoader(fallback_loader=directory_loader)
        loader.register_agent("dynamic_agent", dynamic_instance)
        
        # Both registered and directory agents are available
        agents = loader.list_agents()  # ['dynamic_agent', 'dir_agent1', 'dir_agent2']
    """
    
    def __init__(self, fallback_loader: Optional[BaseAgentLoader] = None):
        """Initialize CustomAgentLoader.
        
        Args:
            fallback_loader: Optional BaseAgentLoader to fall back to when
                agents are not found in the registry. Typically an AgentLoader
                configured with a directory path.
        """
        self._registered_agents: Dict[str, BaseAgent] = {}
        self._fallback_loader = fallback_loader
        self._lock = threading.RLock()  # Thread-safe access to registry
        
        logger.debug(
            "CustomAgentLoader initialized with fallback: %s", 
            type(fallback_loader).__name__ if fallback_loader else "None"
        )
    
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
        
        Checks registered agents first, then falls back to directory loader
        if configured. This provides a hybrid loading approach.
        
        Args:
            name: Name of agent to load.
            
        Returns:
            BaseAgent: The loaded agent instance.
            
        Raises:
            ValueError: If agent is not found in registry or fallback loader.
        """
        # Check registered agents first
        with self._lock:
            if name in self._registered_agents:
                logger.debug("Loading registered agent: %s", name)
                return self._registered_agents[name]
        
        # Fall back to directory loader if configured
        if self._fallback_loader:
            try:
                logger.debug("Loading agent from fallback loader: %s", name)
                return self._fallback_loader.load_agent(name)
            except Exception as e:
                logger.debug("Fallback loader failed for %s: %s", name, e)
                # Continue to raise our own error below
        
        # Agent not found anywhere
        available_agents = self.list_agents()
        raise ValueError(
            f"Agent '{name}' not found. "
            f"Available agents: {available_agents if available_agents else 'None'}"
        )
    
    def list_agents(self) -> List[str]:
        """List all available agents from both registry and fallback loader.
        
        Returns:
            List[str]: Sorted list of all available agent names.
        """
        agent_names = set()
        
        # Add registered agents
        with self._lock:
            agent_names.update(self._registered_agents.keys())
        
        # Add fallback loader agents if available
        if self._fallback_loader:
            try:
                fallback_agents = self._fallback_loader.list_agents()
                agent_names.update(fallback_agents)
                logger.debug(
                    "Found %d fallback agents: %s", 
                    len(fallback_agents), fallback_agents
                )
            except Exception as e:
                logger.warning("Failed to list agents from fallback loader: %s", e)
        
        sorted_agents = sorted(list(agent_names))
        logger.debug("Total available agents: %d", len(sorted_agents))
        return sorted_agents
    
    def has_fallback_loader(self) -> bool:
        """Check if a fallback loader is configured.
        
        Returns:
            bool: True if fallback loader is configured, False otherwise.
        """
        return self._fallback_loader is not None
    
    def get_agent_source(self, name: str) -> str:
        """Get the source of an agent (registry or fallback).
        
        Args:
            name: Agent name to check.
            
        Returns:
            str: "registry", "fallback", or "not_found".
        """
        with self._lock:
            if name in self._registered_agents:
                return "registry"
        
        if self._fallback_loader:
            try:
                fallback_agents = self._fallback_loader.list_agents()
                if name in fallback_agents:
                    return "fallback"
            except Exception:
                pass
        
        return "not_found"
    
    def __repr__(self) -> str:
        """String representation of the loader."""
        with self._lock:
            registered_count = len(self._registered_agents)
        
        fallback_info = (
            f", fallback={type(self._fallback_loader).__name__}" 
            if self._fallback_loader else ""
        )
        
        return f"CustomAgentLoader(registered={registered_count}{fallback_info})"