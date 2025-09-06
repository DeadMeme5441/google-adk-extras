"""Registry Configuration System.

This module provides comprehensive configuration for enhanced registries
with validation, hot-reloading capabilities, and integration with existing
EnhancedRunConfig patterns.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict, validator

logger = logging.getLogger(__name__)


@dataclass
class RegistryCacheConfig:
    """Configuration for registry caching."""
    
    enabled: bool = True
    """Whether caching is enabled."""
    
    default_ttl: float = 300.0
    """Default time-to-live in seconds for cached items."""
    
    max_size: Optional[int] = None
    """Maximum number of items to cache (None = unlimited)."""
    
    cleanup_interval: float = 60.0
    """Interval in seconds to clean up expired cache entries."""


@dataclass
class RegistryHealthConfig:
    """Configuration for registry health monitoring."""
    
    enabled: bool = True
    """Whether health monitoring is enabled."""
    
    check_interval: float = 60.0
    """Health check interval in seconds."""
    
    failure_threshold: int = 3
    """Number of consecutive failures before marking as unhealthy."""
    
    recovery_threshold: int = 2
    """Number of consecutive successes needed to mark as healthy again."""
    
    stale_threshold: float = 300.0
    """Time in seconds after which health info is considered stale."""


@dataclass
class RegistryEventConfig:
    """Configuration for registry event system."""
    
    enabled: bool = True
    """Whether event system is enabled."""
    
    max_listeners: int = 100
    """Maximum number of event listeners per registry."""
    
    async_delivery: bool = False
    """Whether to deliver events asynchronously."""


class RegistryConfig(BaseModel):
    """Base configuration for enhanced registries."""
    
    model_config = ConfigDict(extra='forbid', validate_assignment=True)
    
    name: str = Field(description="Registry name")
    
    # Core features
    caching: RegistryCacheConfig = Field(
        default_factory=RegistryCacheConfig,
        description="Caching configuration"
    )
    
    health_monitoring: RegistryHealthConfig = Field(
        default_factory=RegistryHealthConfig,
        description="Health monitoring configuration"
    )
    
    events: RegistryEventConfig = Field(
        default_factory=RegistryEventConfig,
        description="Event system configuration"
    )
    
    # Lifecycle management
    auto_startup: bool = Field(
        default=True,
        description="Whether registry should start automatically"
    )
    
    graceful_shutdown_timeout: float = Field(
        default=30.0,
        description="Timeout for graceful shutdown in seconds"
    )
    
    @validator('name')
    def validate_name(cls, v):
        """Validate registry name."""
        if not v or not v.strip():
            raise ValueError("Registry name cannot be empty")
        return v.strip()
    
    @validator('graceful_shutdown_timeout')
    def validate_shutdown_timeout(cls, v):
        """Validate shutdown timeout."""
        if v <= 0:
            raise ValueError("Shutdown timeout must be positive")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RegistryConfig':
        """Create config from dictionary."""
        return cls.model_validate(data)


class AgentRegistryConfig(RegistryConfig):
    """Configuration for enhanced agent registry."""
    
    # Agent-specific settings
    enable_hot_swapping: bool = Field(
        default=True,
        description="Whether to enable hot-swapping of agents"
    )
    
    validate_agents_on_registration: bool = Field(
        default=True,
        description="Whether to validate agents when registering"
    )
    
    agent_isolation: bool = Field(
        default=True,
        description="Whether to isolate agents from each other"
    )
    
    max_agents: Optional[int] = Field(
        default=None,
        description="Maximum number of agents that can be registered"
    )
    
    allowed_agent_types: Optional[List[str]] = Field(
        default=None,
        description="List of allowed agent type names (None = all allowed)"
    )
    
    # Performance settings
    lazy_loading: bool = Field(
        default=False,
        description="Whether to load agents lazily"
    )
    
    preload_agents: List[str] = Field(
        default_factory=list,
        description="List of agent names to preload on startup"
    )
    
    @validator('max_agents')
    def validate_max_agents(cls, v):
        """Validate max agents setting."""
        if v is not None and v <= 0:
            raise ValueError("max_agents must be positive if specified")
        return v
    
    @validator('allowed_agent_types')
    def validate_allowed_agent_types(cls, v):
        """Validate allowed agent types."""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("allowed_agent_types must be a list")
            if not all(isinstance(t, str) and t.strip() for t in v):
                raise ValueError("All agent types must be non-empty strings")
        return v


class ToolRegistryConfig(RegistryConfig):
    """Configuration for enhanced tool registry."""
    
    # Tool-specific settings
    enable_dynamic_loading: bool = Field(
        default=True,
        description="Whether to enable dynamic tool loading"
    )
    
    validate_tools_on_registration: bool = Field(
        default=True,
        description="Whether to validate tools when registering"
    )
    
    tool_isolation: bool = Field(
        default=True,
        description="Whether to isolate tools from each other"
    )
    
    max_tools: Optional[int] = Field(
        default=None,
        description="Maximum number of tools that can be registered"
    )
    
    allowed_tool_types: Optional[List[str]] = Field(
        default=None,
        description="List of allowed tool types (None = all allowed)"
    )
    
    # Strategy integration
    strategy_inheritance: bool = Field(
        default=True,
        description="Whether tools inherit from strategy configurations"
    )
    
    default_strategy: Optional[str] = Field(
        default=None,
        description="Default strategy name for tools without explicit strategy"
    )
    
    strategy_fallback_chain: List[str] = Field(
        default_factory=lambda: ['default', 'function'],
        description="Strategy fallback chain for tool execution"
    )
    
    # Performance settings
    lazy_strategy_loading: bool = Field(
        default=True,
        description="Whether to load tool strategies lazily"
    )
    
    preload_strategies: List[str] = Field(
        default_factory=list,
        description="List of strategy names to preload on startup"
    )
    
    # Tool execution settings
    default_timeout: float = Field(
        default=30.0,
        description="Default timeout for tool execution in seconds"
    )
    
    max_concurrent_executions: int = Field(
        default=10,
        description="Maximum number of concurrent tool executions"
    )
    
    @validator('max_tools')
    def validate_max_tools(cls, v):
        """Validate max tools setting."""
        if v is not None and v <= 0:
            raise ValueError("max_tools must be positive if specified")
        return v
    
    @validator('allowed_tool_types')
    def validate_allowed_tool_types(cls, v):
        """Validate allowed tool types."""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("allowed_tool_types must be a list")
            if not all(isinstance(t, str) and t.strip() for t in v):
                raise ValueError("All tool types must be non-empty strings")
        return v
    
    @validator('default_timeout')
    def validate_default_timeout(cls, v):
        """Validate default timeout."""
        if v <= 0:
            raise ValueError("Default timeout must be positive")
        return v
    
    @validator('max_concurrent_executions')
    def validate_max_concurrent_executions(cls, v):
        """Validate max concurrent executions."""
        if v <= 0:
            raise ValueError("max_concurrent_executions must be positive")
        return v


def create_default_agent_registry_config(name: str = "default_agent_registry") -> AgentRegistryConfig:
    """Create a default agent registry configuration.
    
    Args:
        name: Registry name
        
    Returns:
        AgentRegistryConfig: Default configuration
    """
    return AgentRegistryConfig(name=name)


def create_default_tool_registry_config(name: str = "default_tool_registry") -> ToolRegistryConfig:
    """Create a default tool registry configuration.
    
    Args:
        name: Registry name
        
    Returns:
        ToolRegistryConfig: Default configuration
    """
    return ToolRegistryConfig(name=name)


def create_production_registry_config(
    name: str,
    registry_type: str = "agent",
    enable_caching: bool = True,
    enable_health_monitoring: bool = True,
    enable_events: bool = True
) -> RegistryConfig:
    """Create a production-ready registry configuration.
    
    Args:
        name: Registry name
        registry_type: Type of registry ("agent" or "tool")
        enable_caching: Whether to enable caching
        enable_health_monitoring: Whether to enable health monitoring
        enable_events: Whether to enable event system
        
    Returns:
        RegistryConfig: Production configuration
    """
    if registry_type == "agent":
        config = AgentRegistryConfig(name=name)
    elif registry_type == "tool":
        config = ToolRegistryConfig(name=name)
    else:
        config = RegistryConfig(name=name)
    
    # Configure for production
    config.caching.enabled = enable_caching
    config.caching.default_ttl = 600.0  # 10 minutes
    config.caching.cleanup_interval = 120.0  # 2 minutes
    
    config.health_monitoring.enabled = enable_health_monitoring
    config.health_monitoring.check_interval = 30.0  # 30 seconds
    config.health_monitoring.failure_threshold = 5
    config.health_monitoring.recovery_threshold = 3
    
    config.events.enabled = enable_events
    config.events.max_listeners = 50
    config.events.async_delivery = True
    
    config.graceful_shutdown_timeout = 60.0  # 1 minute
    
    return config


def validate_registry_config(config: Dict[str, Any], registry_type: str = "base") -> RegistryConfig:
    """Validate and create registry configuration from dictionary.
    
    Args:
        config: Configuration dictionary
        registry_type: Type of registry ("base", "agent", or "tool")
        
    Returns:
        RegistryConfig: Validated configuration
        
    Raises:
        ValueError: If configuration is invalid
    """
    try:
        if registry_type == "agent":
            return AgentRegistryConfig.from_dict(config)
        elif registry_type == "tool":
            return ToolRegistryConfig.from_dict(config)
        else:
            return RegistryConfig.from_dict(config)
    except Exception as e:
        raise ValueError(f"Invalid {registry_type} registry configuration: {e}")


def merge_registry_configs(base: RegistryConfig, override: Dict[str, Any]) -> RegistryConfig:
    """Merge registry configuration with overrides.
    
    Args:
        base: Base configuration
        override: Configuration overrides
        
    Returns:
        RegistryConfig: Merged configuration
    """
    # Convert base to dict
    merged_dict = base.to_dict()
    
    # Apply overrides recursively
    def deep_update(base_dict: Dict[str, Any], override_dict: Dict[str, Any]) -> None:
        for key, value in override_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    deep_update(merged_dict, override)
    
    # Return new config of same type as base
    return type(base).from_dict(merged_dict)