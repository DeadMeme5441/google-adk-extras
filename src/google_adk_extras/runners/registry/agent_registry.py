"""Enhanced Agent Registry with hot-swapping and dynamic loading.

This module extends the existing CustomAgentLoader with advanced features:
- Event system for agent registration/unregistration
- Health monitoring for registered agents  
- Caching layer for better performance
- Hot-swapping capabilities with validation
- Integration with enhanced agent composition engine
"""

import logging
import inspect
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Type, Callable

from google.adk.agents.base_agent import BaseAgent

from ...custom_agent_loader import CustomAgentLoader
from ..errors import YamlSystemContext, YamlSystemError
from .base import (
    EnhancedRegistryBase,
    RegistryEvent,
    RegistryEventType,
    RegistryHealthStatus,
)
from .config import AgentRegistryConfig

logger = logging.getLogger(__name__)


class AgentHealthStatus(Enum):
    """Agent-specific health status."""
    HEALTHY = "healthy"
    INITIALIZING = "initializing"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    UNAVAILABLE = "unavailable"


@dataclass
class AgentRegistrationEvent(RegistryEvent):
    """Agent-specific registration event."""
    
    agent_type: Optional[str] = None
    """Type of the agent."""
    
    agent_version: Optional[str] = None
    """Version of the agent if available."""
    
    replaced_agent: Optional[BaseAgent] = None
    """Previously registered agent if this was a replacement."""


class EnhancedAgentRegistry(CustomAgentLoader, EnhancedRegistryBase[BaseAgent]):
    """Enhanced agent registry with advanced features.
    
    This registry extends CustomAgentLoader with:
    - Event system for registration/unregistration notifications
    - Health monitoring for agents
    - Caching for improved performance
    - Hot-swapping with validation
    - Integration with YAML system context for error reporting
    """
    
    def __init__(
        self,
        config: Optional[AgentRegistryConfig] = None,
        yaml_context: Optional[YamlSystemContext] = None
    ):
        """Initialize enhanced agent registry.
        
        Args:
            config: Agent registry configuration
            yaml_context: YAML system context for error reporting
        """
        config = config or AgentRegistryConfig(name="enhanced_agent_registry")
        
        # Initialize CustomAgentLoader (provides thread-safe agent management)
        CustomAgentLoader.__init__(self)
        
        # Initialize EnhancedRegistryBase (provides events, health, caching)
        EnhancedRegistryBase.__init__(
            self,
            name=config.name,
            cache_ttl=config.caching.default_ttl,
            health_check_interval=config.health_monitoring.check_interval,
            enable_events=config.events.enabled,
            enable_caching=config.caching.enabled,
            enable_health_monitoring=config.health_monitoring.enabled
        )
        
        self.config = config
        self.yaml_context = yaml_context or YamlSystemContext(system_name="EnhancedAgentRegistry")
        
        # Agent validation and management
        self._agent_validators: List[Callable[[str, BaseAgent], bool]] = []
        self._agent_metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Initialized EnhancedAgentRegistry '{config.name}' with hot-swapping={config.enable_hot_swapping}")
    
    def register_agent(self, name: str, agent: BaseAgent, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Register an agent with enhanced features.
        
        Args:
            name: Agent name
            agent: BaseAgent instance
            metadata: Optional metadata about the agent
            
        Raises:
            YamlSystemError: If registration fails validation
        """
        if not name or not name.strip():
            raise YamlSystemError(
                "Agent name cannot be empty",
                context=self.yaml_context.with_agent(name),
                suggested_fixes=["Provide a non-empty agent name"]
            )
        
        if not isinstance(agent, BaseAgent):
            raise YamlSystemError(
                f"Agent must be BaseAgent instance, got {type(agent)}",
                context=self.yaml_context.with_agent(name),
                suggested_fixes=[
                    "Ensure agent inherits from google.adk.agents.base_agent.BaseAgent",
                    "Check agent class implementation"
                ]
            )
        
        # Check maximum agents limit
        if self.config.max_agents is not None:
            current_count = len(self.list_agents())
            if current_count >= self.config.max_agents and not self.is_registered(name):
                raise YamlSystemError(
                    f"Maximum agents limit ({self.config.max_agents}) reached",
                    context=self.yaml_context.with_agent(name),
                    suggested_fixes=[
                        f"Unregister unused agents or increase max_agents limit",
                        "Consider agent lifecycle management"
                    ]
                )
        
        # Validate agent type if restrictions are configured
        if self.config.allowed_agent_types is not None:
            agent_type = type(agent).__name__
            if agent_type not in self.config.allowed_agent_types:
                raise YamlSystemError(
                    f"Agent type '{agent_type}' not in allowed types: {self.config.allowed_agent_types}",
                    context=self.yaml_context.with_agent(name),
                    suggested_fixes=[
                        f"Use one of the allowed agent types: {self.config.allowed_agent_types}",
                        "Update allowed_agent_types configuration"
                    ]
                )
        
        # Run custom validators
        if self.config.validate_agents_on_registration:
            for validator in self._agent_validators:
                try:
                    if not validator(name, agent):
                        raise YamlSystemError(
                            f"Agent validation failed for '{name}'",
                            context=self.yaml_context.with_agent(name),
                            suggested_fixes=[
                                "Check agent implementation meets validation requirements",
                                "Review custom agent validators"
                            ]
                        )
                except Exception as e:
                    raise YamlSystemError(
                        f"Agent validation error for '{name}': {str(e)}",
                        context=self.yaml_context.with_agent(name),
                        original_error=e,
                        suggested_fixes=["Fix agent validation issues"]
                    )
        
        # Check if agent is being replaced (hot-swapping)
        was_registered = self.is_registered(name)
        replaced_agent = None
        
        if was_registered:
            if not self.config.enable_hot_swapping:
                raise YamlSystemError(
                    f"Agent '{name}' is already registered and hot-swapping is disabled",
                    context=self.yaml_context.with_agent(name),
                    suggested_fixes=[
                        "Enable hot-swapping in configuration",
                        "Unregister the existing agent first"
                    ]
                )
            
            # Get the existing agent before replacement
            replaced_agent = self._registered_agents.get(name)
        
        # Register with parent CustomAgentLoader
        CustomAgentLoader.register_agent(self, name, agent)
        
        # Store metadata
        if metadata:
            self._agent_metadata[name] = metadata.copy()
        else:
            self._agent_metadata[name] = {}
        
        # Add agent type and other introspected metadata
        agent_metadata = self._agent_metadata[name]
        agent_metadata.update({
            'agent_type': type(agent).__name__,
            'agent_class': f"{type(agent).__module__}.{type(agent).__qualname__}",
            'registered_at': self._get_current_timestamp(),
            'hot_swapped': was_registered,
        })
        
        # Add version if available
        if hasattr(agent, '__version__'):
            agent_metadata['agent_version'] = agent.__version__
        elif hasattr(agent, 'version'):
            agent_metadata['agent_version'] = agent.version
        
        # Update health status
        self.update_health_status(name, RegistryHealthStatus.HEALTHY)
        
        # Cache the agent if caching is enabled
        if self._enable_caching:
            self._put_in_cache(name, agent)
        
        # Emit registration event
        if self._enable_events:
            event = AgentRegistrationEvent(
                event_type=RegistryEventType.REGISTERED if not was_registered else RegistryEventType.UPDATED,
                registry_name=self.name,
                item_name=name,
                item=agent,
                agent_type=agent_metadata['agent_type'],
                agent_version=agent_metadata.get('agent_version'),
                replaced_agent=replaced_agent,
                metadata=agent_metadata.copy()
            )
            self._emit_event(event)
        
        operation = "Updated" if was_registered else "Registered"
        logger.info(f"{operation} agent '{name}' (type: {agent_metadata['agent_type']})")
    
    def unregister_agent(self, name: str) -> bool:
        """Unregister an agent with cleanup.
        
        Args:
            name: Name of agent to unregister
            
        Returns:
            bool: True if agent was found and removed
        """
        # Get agent before removal for event
        agent = self._registered_agents.get(name) if hasattr(self, '_registered_agents') else None
        
        # Unregister with parent CustomAgentLoader
        was_removed = CustomAgentLoader.unregister_agent(self, name)
        
        if was_removed:
            # Clean up metadata
            if name in self._agent_metadata:
                del self._agent_metadata[name]
            
            # Clean up health info
            self._remove_health_info(name)
            
            # Remove from cache
            if self._enable_caching:
                self._remove_from_cache(name)
            
            # Emit unregistration event
            if self._enable_events and agent:
                event = AgentRegistrationEvent(
                    event_type=RegistryEventType.UNREGISTERED,
                    registry_name=self.name,
                    item_name=name,
                    item=agent,
                    agent_type=type(agent).__name__
                )
                self._emit_event(event)
            
            logger.info(f"Unregistered agent '{name}'")
        
        return was_removed
    
    def load_agent(self, name: str) -> BaseAgent:
        """Load agent with caching support.
        
        Args:
            name: Agent name to load
            
        Returns:
            BaseAgent: The loaded agent
            
        Raises:
            YamlSystemError: If agent not found
        """
        # Try cache first if enabled
        if self._enable_caching:
            cached_agent = self._get_from_cache(name)
            if cached_agent is not None:
                logger.debug(f"Loaded agent '{name}' from cache")
                return cached_agent
        
        try:
            # Load from parent CustomAgentLoader
            agent = CustomAgentLoader.load_agent(self, name)
            
            # Cache if caching enabled
            if self._enable_caching:
                self._put_in_cache(name, agent)
            
            return agent
        
        except ValueError as e:
            # Wrap in YamlSystemError for better error reporting
            available_agents = self.list_agents()
            raise YamlSystemError(
                f"Agent '{name}' not found in registry",
                context=self.yaml_context.with_agent(name),
                original_error=e,
                suggested_fixes=[
                    f"Register the agent using register_agent()",
                    f"Available agents: {available_agents}" if available_agents else "No agents currently registered"
                ]
            )
    
    def get_agent_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a registered agent.
        
        Args:
            name: Agent name
            
        Returns:
            Dict[str, Any]: Agent metadata or None if not found
        """
        return self._agent_metadata.get(name)
    
    def get_all_agent_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata for all registered agents.
        
        Returns:
            Dict[str, Dict[str, Any]]: Mapping of agent names to metadata
        """
        return self._agent_metadata.copy()
    
    def add_agent_validator(self, validator: Callable[[str, BaseAgent], bool]) -> None:
        """Add custom agent validator.
        
        Args:
            validator: Function that takes (name, agent) and returns bool
        """
        self._agent_validators.append(validator)
        logger.debug(f"Added agent validator: {validator.__name__}")
    
    def remove_agent_validator(self, validator: Callable[[str, BaseAgent], bool]) -> bool:
        """Remove custom agent validator.
        
        Args:
            validator: Validator function to remove
            
        Returns:
            bool: True if validator was found and removed
        """
        if validator in self._agent_validators:
            self._agent_validators.remove(validator)
            logger.debug(f"Removed agent validator: {validator.__name__}")
            return True
        return False
    
    def find_agents_by_type(self, agent_type: str) -> List[str]:
        """Find agents by their type.
        
        Args:
            agent_type: Agent type name to search for
            
        Returns:
            List[str]: Names of agents with matching type
        """
        matching_agents = []
        
        for name, metadata in self._agent_metadata.items():
            if metadata.get('agent_type') == agent_type:
                matching_agents.append(name)
        
        return sorted(matching_agents)
    
    def find_agents_by_metadata(self, **metadata_filters) -> List[str]:
        """Find agents by metadata filters.
        
        Args:
            **metadata_filters: Key-value pairs to match in agent metadata
            
        Returns:
            List[str]: Names of agents matching all filters
        """
        matching_agents = []
        
        for name, metadata in self._agent_metadata.items():
            matches_all = True
            for key, value in metadata_filters.items():
                if metadata.get(key) != value:
                    matches_all = False
                    break
            
            if matches_all:
                matching_agents.append(name)
        
        return sorted(matching_agents)
    
    def validate_all_agents(self) -> Dict[str, bool]:
        """Validate all registered agents.
        
        Returns:
            Dict[str, bool]: Mapping of agent names to validation results
        """
        results = {}
        
        for name in self.list_agents():
            try:
                agent = CustomAgentLoader.load_agent(self, name)
                is_valid = True
                
                # Run all validators
                for validator in self._agent_validators:
                    if not validator(name, agent):
                        is_valid = False
                        break
                
                results[name] = is_valid
            except Exception as e:
                logger.warning(f"Validation error for agent '{name}': {e}")
                results[name] = False
        
        return results
    
    def _get_items_for_health_check(self) -> Dict[str, BaseAgent]:
        """Get all registered agents for health checking.
        
        Returns:
            Dict[str, BaseAgent]: Mapping of agent names to agents
        """
        items = {}
        
        for name in self.list_agents():
            try:
                # Load agent (may come from cache)
                agent = CustomAgentLoader.load_agent(self, name)
                items[name] = agent
            except Exception as e:
                logger.warning(f"Failed to load agent '{name}' for health check: {e}")
        
        return items
    
    async def _check_item_health(self, item_name: str, item: BaseAgent) -> RegistryHealthStatus:
        """Check health of a specific agent.
        
        Args:
            item_name: Agent name
            item: The agent instance
            
        Returns:
            RegistryHealthStatus: Health status of the agent
        """
        try:
            # Basic health checks
            if not isinstance(item, BaseAgent):
                return RegistryHealthStatus.UNHEALTHY
            
            # Check if agent has required methods
            required_methods = ['_run_async_impl', '_run_live_impl']
            for method_name in required_methods:
                if not hasattr(item, method_name):
                    return RegistryHealthStatus.DEGRADED
            
            # Check if agent can be called (basic validation)
            if hasattr(item, 'name') and not item.name:
                return RegistryHealthStatus.DEGRADED
            
            # Run custom validators for health check
            for validator in self._agent_validators:
                try:
                    if not validator(item_name, item):
                        return RegistryHealthStatus.DEGRADED
                except Exception:
                    return RegistryHealthStatus.DEGRADED
            
            return RegistryHealthStatus.HEALTHY
        
        except Exception as e:
            logger.debug(f"Health check failed for agent '{item_name}': {e}")
            return RegistryHealthStatus.UNHEALTHY
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get enhanced agent registry statistics.
        
        Returns:
            Dict[str, Any]: Registry statistics
        """
        stats = super().get_registry_stats()
        
        # Add agent-specific stats
        stats['total_agents'] = len(self.list_agents())
        stats['hot_swapping_enabled'] = self.config.enable_hot_swapping
        stats['validation_enabled'] = self.config.validate_agents_on_registration
        stats['max_agents'] = self.config.max_agents
        stats['allowed_agent_types'] = self.config.allowed_agent_types
        
        # Agent type distribution
        type_distribution = {}
        for metadata in self._agent_metadata.values():
            agent_type = metadata.get('agent_type', 'unknown')
            type_distribution[agent_type] = type_distribution.get(agent_type, 0) + 1
        
        stats['agent_type_distribution'] = type_distribution
        
        # Validation stats
        if self._agent_validators:
            stats['custom_validators'] = len(self._agent_validators)
        
        return stats
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def __repr__(self) -> str:
        """String representation of the registry."""
        agent_count = len(self.list_agents()) if hasattr(self, '_registered_agents') else 0
        return f"EnhancedAgentRegistry(name='{self.name}', agents={agent_count}, started={self._is_started})"