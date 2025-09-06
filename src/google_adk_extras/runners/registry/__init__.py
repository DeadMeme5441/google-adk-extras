"""Enhanced Registry Infrastructure for Google ADK Extras.

This module provides enhanced registry infrastructure that extends the existing
CustomAgentLoader and ToolExecutionStrategyManager with advanced features:
- Event system for registry changes
- Health monitoring for registered items
- Caching layer for performance optimization
- Lifecycle management with startup/shutdown hooks

Key Components:
- EnhancedRegistryBase: Abstract base class for all enhanced registries
- EnhancedAgentRegistry: Enhanced agent registry with monitoring and events
- EnhancedToolRegistry: Enhanced tool registry with dynamic loading
- Registry configuration and event system
"""

from .base import (
    EnhancedRegistryBase,
    RegistryEvent, 
    RegistryEventType,
    RegistryHealth,
    RegistryHealthStatus,
)
from .agent_registry import (
    EnhancedAgentRegistry,
    AgentRegistrationEvent,
    AgentHealthStatus,
)
from .tool_registry import (
    EnhancedToolRegistry,
    ToolRegistrationEvent,
    ToolHealthStatus,
)
from .config import (
    RegistryConfig,
    AgentRegistryConfig,
    ToolRegistryConfig,
    RegistryCacheConfig,
    RegistryHealthConfig,
)

__all__ = [
    # Base registry infrastructure
    'EnhancedRegistryBase',
    'RegistryEvent',
    'RegistryEventType', 
    'RegistryHealth',
    'RegistryHealthStatus',
    
    # Agent registry
    'EnhancedAgentRegistry',
    'AgentRegistrationEvent',
    'AgentHealthStatus',
    
    # Tool registry
    'EnhancedToolRegistry',
    'ToolRegistrationEvent', 
    'ToolHealthStatus',
    
    # Configuration
    'RegistryConfig',
    'AgentRegistryConfig',
    'ToolRegistryConfig',
    'RegistryCacheConfig',
    'RegistryHealthConfig',
]