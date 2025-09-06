"""Enhanced Tool Registry with strategy integration and dynamic loading.

This module extends the existing ToolExecutionStrategyManager with advanced features:
- Dynamic tool registration beyond just execution strategies
- Event system for tool registration/unregistration
- Health monitoring for tools and strategies
- Caching layer for better performance
- Integration with existing strategy management
"""

import logging
import asyncio
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from google.adk.agents.invocation_context import InvocationContext

from ..strategies import ToolExecutionStrategyManager, ToolExecutionStrategy
from ..errors import YamlSystemContext, YamlSystemError
from .base import (
    EnhancedRegistryBase,
    RegistryEvent,
    RegistryEventType,
    RegistryHealthStatus,
)
from .config import ToolRegistryConfig

logger = logging.getLogger(__name__)


class ToolHealthStatus(Enum):
    """Tool-specific health status."""
    HEALTHY = "healthy"
    LOADING = "loading"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"


@dataclass
class ToolRegistrationEvent(RegistryEvent):
    """Tool-specific registration event."""
    
    tool_type: Optional[str] = None
    """Type of the tool."""
    
    strategy_name: Optional[str] = None
    """Associated strategy name."""
    
    replaced_tool: Optional[Any] = None
    """Previously registered tool if this was a replacement."""


class ToolInfo:
    """Information about a registered tool."""
    
    def __init__(
        self,
        name: str,
        tool: Any,
        tool_type: str,
        strategy_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.tool = tool
        self.tool_type = tool_type
        self.strategy_name = strategy_name
        self.metadata = metadata or {}
        self.registered_at = self._get_current_timestamp()
        self.last_used = None
        self.usage_count = 0
        self.error_count = 0
    
    def mark_used(self) -> None:
        """Mark tool as used (for statistics)."""
        self.usage_count += 1
        self.last_used = self._get_current_timestamp()
    
    def mark_error(self) -> None:
        """Mark tool as having an error."""
        self.error_count += 1
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'tool_type': self.tool_type,
            'strategy_name': self.strategy_name,
            'metadata': self.metadata.copy(),
            'registered_at': self.registered_at,
            'last_used': self.last_used,
            'usage_count': self.usage_count,
            'error_count': self.error_count,
        }


class EnhancedToolRegistry(ToolExecutionStrategyManager, EnhancedRegistryBase[Any]):
    """Enhanced tool registry with advanced features.
    
    This registry extends ToolExecutionStrategyManager with:
    - Dynamic tool registration beyond just strategies
    - Event system for tool registration/unregistration
    - Health monitoring for tools and strategies
    - Caching for improved performance
    - Strategy integration and fallback chains
    """
    
    def __init__(
        self,
        config: Optional[ToolRegistryConfig] = None,
        yaml_context: Optional[YamlSystemContext] = None
    ):
        """Initialize enhanced tool registry.
        
        Args:
            config: Tool registry configuration
            yaml_context: YAML system context for error reporting
        """
        config = config or ToolRegistryConfig(name="enhanced_tool_registry")
        
        # Initialize ToolExecutionStrategyManager (provides strategy management)
        ToolExecutionStrategyManager.__init__(self)
        
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
        self.yaml_context = yaml_context or YamlSystemContext(system_name="EnhancedToolRegistry")
        
        # Tool registration and management
        self._registered_tools: Dict[str, ToolInfo] = {}
        self._tool_validators: List[Callable[[str, Any], bool]] = []
        self._execution_semaphore = asyncio.Semaphore(config.max_concurrent_executions)
        
        logger.info(f"Initialized EnhancedToolRegistry '{config.name}' with dynamic_loading={config.enable_dynamic_loading}")
    
    def register_tool(
        self,
        name: str,
        tool: Any,
        tool_type: str,
        strategy_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a tool with enhanced features.
        
        Args:
            name: Tool name
            tool: Tool instance or callable
            tool_type: Type of tool (e.g., 'mcp', 'openapi', 'function')
            strategy_name: Associated strategy name
            metadata: Optional metadata about the tool
            
        Raises:
            YamlSystemError: If registration fails validation
        """
        if not name or not name.strip():
            raise YamlSystemError(
                "Tool name cannot be empty",
                context=self.yaml_context.with_tool(name),
                suggested_fixes=["Provide a non-empty tool name"]
            )
        
        if not tool_type or not tool_type.strip():
            raise YamlSystemError(
                "Tool type cannot be empty",
                context=self.yaml_context.with_tool(name),
                suggested_fixes=["Provide a valid tool type (e.g., 'mcp', 'openapi', 'function')"]
            )
        
        # Check maximum tools limit
        if self.config.max_tools is not None:
            current_count = len(self._registered_tools)
            if current_count >= self.config.max_tools and name not in self._registered_tools:
                raise YamlSystemError(
                    f"Maximum tools limit ({self.config.max_tools}) reached",
                    context=self.yaml_context.with_tool(name),
                    suggested_fixes=[
                        "Unregister unused tools or increase max_tools limit",
                        "Consider tool lifecycle management"
                    ]
                )
        
        # Validate tool type if restrictions are configured
        if self.config.allowed_tool_types is not None:
            if tool_type not in self.config.allowed_tool_types:
                raise YamlSystemError(
                    f"Tool type '{tool_type}' not in allowed types: {self.config.allowed_tool_types}",
                    context=self.yaml_context.with_tool(name),
                    suggested_fixes=[
                        f"Use one of the allowed tool types: {self.config.allowed_tool_types}",
                        "Update allowed_tool_types configuration"
                    ]
                )
        
        # Run custom validators
        if self.config.validate_tools_on_registration:
            for validator in self._tool_validators:
                try:
                    if not validator(name, tool):
                        raise YamlSystemError(
                            f"Tool validation failed for '{name}'",
                            context=self.yaml_context.with_tool(name),
                            suggested_fixes=[
                                "Check tool implementation meets validation requirements",
                                "Review custom tool validators"
                            ]
                        )
                except Exception as e:
                    raise YamlSystemError(
                        f"Tool validation error for '{name}': {str(e)}",
                        context=self.yaml_context.with_tool(name),
                        original_error=e,
                        suggested_fixes=["Fix tool validation issues"]
                    )
        
        # Check if tool is being replaced
        was_registered = name in self._registered_tools
        replaced_tool = None
        
        if was_registered:
            replaced_tool = self._registered_tools[name].tool
        
        # Create tool info
        tool_info = ToolInfo(
            name=name,
            tool=tool,
            tool_type=tool_type,
            strategy_name=strategy_name,
            metadata=metadata
        )
        
        # Register tool
        self._registered_tools[name] = tool_info
        
        # Update health status
        self.update_health_status(name, RegistryHealthStatus.HEALTHY)
        
        # Cache the tool if caching is enabled
        if self._enable_caching:
            self._put_in_cache(name, tool)
        
        # Emit registration event
        if self._enable_events:
            event = ToolRegistrationEvent(
                event_type=RegistryEventType.REGISTERED if not was_registered else RegistryEventType.UPDATED,
                registry_name=self.name,
                item_name=name,
                item=tool,
                tool_type=tool_type,
                strategy_name=strategy_name,
                replaced_tool=replaced_tool,
                metadata=metadata
            )
            self._emit_event(event)
        
        operation = "Updated" if was_registered else "Registered"
        logger.info(f"{operation} tool '{name}' (type: {tool_type}, strategy: {strategy_name})")
    
    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool with cleanup.
        
        Args:
            name: Name of tool to unregister
            
        Returns:
            bool: True if tool was found and removed
        """
        if name not in self._registered_tools:
            return False
        
        # Get tool info before removal for event
        tool_info = self._registered_tools[name]
        
        # Remove tool
        del self._registered_tools[name]
        
        # Clean up health info
        self._remove_health_info(name)
        
        # Remove from cache
        if self._enable_caching:
            self._remove_from_cache(name)
        
        # Emit unregistration event
        if self._enable_events:
            event = ToolRegistrationEvent(
                event_type=RegistryEventType.UNREGISTERED,
                registry_name=self.name,
                item_name=name,
                item=tool_info.tool,
                tool_type=tool_info.tool_type,
                strategy_name=tool_info.strategy_name
            )
            self._emit_event(event)
        
        logger.info(f"Unregistered tool '{name}'")
        return True
    
    def get_tool(self, name: str) -> Any:
        """Get a registered tool.
        
        Args:
            name: Tool name
            
        Returns:
            Any: The tool instance
            
        Raises:
            YamlSystemError: If tool not found
        """
        # Try cache first if enabled
        if self._enable_caching:
            cached_tool = self._get_from_cache(name)
            if cached_tool is not None:
                logger.debug(f"Loaded tool '{name}' from cache")
                # Mark as used
                if name in self._registered_tools:
                    self._registered_tools[name].mark_used()
                return cached_tool
        
        if name not in self._registered_tools:
            available_tools = self.list_tools()
            raise YamlSystemError(
                f"Tool '{name}' not found in registry",
                context=self.yaml_context.with_tool(name),
                suggested_fixes=[
                    "Register the tool using register_tool()",
                    f"Available tools: {available_tools}" if available_tools else "No tools currently registered"
                ]
            )
        
        tool_info = self._registered_tools[name]
        tool_info.mark_used()
        
        # Cache if caching enabled
        if self._enable_caching:
            self._put_in_cache(name, tool_info.tool)
        
        return tool_info.tool
    
    def list_tools(self) -> List[str]:
        """List all registered tool names.
        
        Returns:
            List[str]: Sorted list of tool names
        """
        return sorted(self._registered_tools.keys())
    
    def get_tool_info(self, name: str) -> Optional[ToolInfo]:
        """Get information about a registered tool.
        
        Args:
            name: Tool name
            
        Returns:
            ToolInfo: Tool information or None if not found
        """
        return self._registered_tools.get(name)
    
    def get_all_tool_info(self) -> Dict[str, ToolInfo]:
        """Get information about all registered tools.
        
        Returns:
            Dict[str, ToolInfo]: Mapping of tool names to tool info
        """
        return self._registered_tools.copy()
    
    def find_tools_by_type(self, tool_type: str) -> List[str]:
        """Find tools by their type.
        
        Args:
            tool_type: Tool type to search for
            
        Returns:
            List[str]: Names of tools with matching type
        """
        matching_tools = []
        
        for name, tool_info in self._registered_tools.items():
            if tool_info.tool_type == tool_type:
                matching_tools.append(name)
        
        return sorted(matching_tools)
    
    def find_tools_by_strategy(self, strategy_name: str) -> List[str]:
        """Find tools by their associated strategy.
        
        Args:
            strategy_name: Strategy name to search for
            
        Returns:
            List[str]: Names of tools with matching strategy
        """
        matching_tools = []
        
        for name, tool_info in self._registered_tools.items():
            if tool_info.strategy_name == strategy_name:
                matching_tools.append(name)
        
        return sorted(matching_tools)
    
    def get_strategy_for_tool(self, tool_name: str) -> Optional[ToolExecutionStrategy]:
        """Get execution strategy for a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            ToolExecutionStrategy: Strategy for the tool or None
        """
        if tool_name not in self._registered_tools:
            return None
        
        tool_info = self._registered_tools[tool_name]
        
        # First try tool's specific strategy
        if tool_info.strategy_name:
            strategy = self.strategies.get(tool_info.strategy_name)
            if strategy:
                return strategy
        
        # Then try strategy based on tool type
        strategy = self.strategies.get(tool_info.tool_type)
        if strategy:
            return strategy
        
        # Finally try fallback chain
        for fallback_strategy in self.config.strategy_fallback_chain:
            strategy = self.strategies.get(fallback_strategy)
            if strategy:
                return strategy
        
        # Use default strategy as last resort
        return self.default_strategy
    
    async def execute_tool(
        self,
        tool_name: str,
        context: InvocationContext,
        tool_context: YamlSystemContext,
        tool_config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a tool with enhanced monitoring and error handling.
        
        Args:
            tool_name: Name of tool to execute
            context: Invocation context
            tool_context: YAML system context for error reporting
            tool_config: Tool-specific configuration
            
        Returns:
            Any: Tool execution result
            
        Raises:
            YamlSystemError: If tool execution fails
        """
        # Rate limiting with semaphore
        async with self._execution_semaphore:
            try:
                # Get tool
                tool = self.get_tool(tool_name)
                tool_info = self._registered_tools[tool_name]
                
                # Get appropriate strategy
                strategy = self.get_strategy_for_tool(tool_name)
                
                if not strategy:
                    raise YamlSystemError(
                        f"No execution strategy available for tool '{tool_name}'",
                        context=tool_context,
                        suggested_fixes=[
                            "Register an appropriate execution strategy",
                            "Configure strategy fallback chain"
                        ]
                    )
                
                # Execute with strategy
                start_time = self._get_current_timestamp()
                
                try:
                    result = await strategy.execute(tool, context, tool_context, tool_config)
                    
                    # Update health status on success
                    self.update_health_status(tool_name, RegistryHealthStatus.HEALTHY)
                    
                    return result
                
                except Exception as e:
                    # Mark error and update health
                    tool_info.mark_error()
                    self.update_health_status(
                        tool_name, 
                        RegistryHealthStatus.UNHEALTHY,
                        {'error': str(e), 'error_count': tool_info.error_count}
                    )
                    
                    # Re-raise as YamlSystemError if not already
                    if not isinstance(e, YamlSystemError):
                        raise YamlSystemError(
                            f"Tool '{tool_name}' execution failed: {str(e)}",
                            context=tool_context,
                            original_error=e,
                            suggested_fixes=[
                                "Check tool implementation and configuration",
                                "Review tool execution logs"
                            ]
                        )
                    else:
                        raise
            
            except YamlSystemError:
                # Re-raise YamlSystemError as-is
                raise
            except Exception as e:
                # Wrap unexpected errors
                raise YamlSystemError(
                    f"Unexpected error executing tool '{tool_name}': {str(e)}",
                    context=tool_context,
                    original_error=e,
                    suggested_fixes=["Check tool registry and configuration"]
                )
    
    def add_tool_validator(self, validator: Callable[[str, Any], bool]) -> None:
        """Add custom tool validator.
        
        Args:
            validator: Function that takes (name, tool) and returns bool
        """
        self._tool_validators.append(validator)
        logger.debug(f"Added tool validator: {validator.__name__}")
    
    def remove_tool_validator(self, validator: Callable[[str, Any], bool]) -> bool:
        """Remove custom tool validator.
        
        Args:
            validator: Validator function to remove
            
        Returns:
            bool: True if validator was found and removed
        """
        if validator in self._tool_validators:
            self._tool_validators.remove(validator)
            logger.debug(f"Removed tool validator: {validator.__name__}")
            return True
        return False
    
    def _get_items_for_health_check(self) -> Dict[str, Any]:
        """Get all registered tools for health checking.
        
        Returns:
            Dict[str, Any]: Mapping of tool names to tools
        """
        items = {}
        
        for name, tool_info in self._registered_tools.items():
            items[name] = tool_info.tool
        
        return items
    
    async def _check_item_health(self, item_name: str, item: Any) -> RegistryHealthStatus:
        """Check health of a specific tool.
        
        Args:
            item_name: Tool name
            item: The tool instance
            
        Returns:
            RegistryHealthStatus: Health status of the tool
        """
        try:
            tool_info = self._registered_tools.get(item_name)
            if not tool_info:
                return RegistryHealthStatus.UNHEALTHY
            
            # Check error rate
            if tool_info.error_count > 0 and tool_info.usage_count > 0:
                error_rate = tool_info.error_count / tool_info.usage_count
                if error_rate > 0.5:  # More than 50% errors
                    return RegistryHealthStatus.UNHEALTHY
                elif error_rate > 0.2:  # More than 20% errors
                    return RegistryHealthStatus.DEGRADED
            
            # Check if tool is callable
            if callable(item):
                # Basic health check - tool exists and is callable
                return RegistryHealthStatus.HEALTHY
            
            # Check if tool has required methods/attributes
            # This would be tool-type specific in a full implementation
            return RegistryHealthStatus.HEALTHY
        
        except Exception as e:
            logger.debug(f"Health check failed for tool '{item_name}': {e}")
            return RegistryHealthStatus.UNHEALTHY
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get enhanced tool registry statistics.
        
        Returns:
            Dict[str, Any]: Registry statistics
        """
        stats = super().get_registry_stats()
        
        # Add tool-specific stats
        stats['total_tools'] = len(self._registered_tools)
        stats['total_strategies'] = len(self.strategies)
        stats['dynamic_loading_enabled'] = self.config.enable_dynamic_loading
        stats['validation_enabled'] = self.config.validate_tools_on_registration
        stats['max_tools'] = self.config.max_tools
        stats['allowed_tool_types'] = self.config.allowed_tool_types
        stats['max_concurrent_executions'] = self.config.max_concurrent_executions
        
        # Tool type distribution
        type_distribution = {}
        total_usage = 0
        total_errors = 0
        
        for tool_info in self._registered_tools.values():
            tool_type = tool_info.tool_type
            type_distribution[tool_type] = type_distribution.get(tool_type, 0) + 1
            total_usage += tool_info.usage_count
            total_errors += tool_info.error_count
        
        stats['tool_type_distribution'] = type_distribution
        stats['total_tool_usage'] = total_usage
        stats['total_tool_errors'] = total_errors
        stats['overall_error_rate'] = total_errors / max(total_usage, 1)
        
        # Strategy stats
        strategy_usage = {}
        for tool_info in self._registered_tools.values():
            strategy = tool_info.strategy_name or 'default'
            strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
        
        stats['strategy_usage'] = strategy_usage
        
        return stats
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def __repr__(self) -> str:
        """String representation of the registry."""
        tool_count = len(self._registered_tools)
        strategy_count = len(self.strategies)
        return f"EnhancedToolRegistry(name='{self.name}', tools={tool_count}, strategies={strategy_count}, started={self._is_started})"