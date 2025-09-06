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
import inspect
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from google.adk.agents.invocation_context import InvocationContext

# ADK Tool imports for enhanced support
try:
    from google.adk.tools.base_tool import BaseTool
    from google.adk.tools.function_tool import FunctionTool
    from google.adk.tools.agent_tool import AgentTool
    from google.adk.tools.mcp_tool.mcp_tool import McpTool
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
    from google.adk.tools.openapi_tool.openapi_spec_parser.rest_api_tool import RestApiTool
    from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import OpenAPIToolset
    from google.adk.tools.google_tool import GoogleTool
    from google.adk.tools.google_api_tool.google_api_tool import GoogleApiTool
    from google.adk.tools.google_api_tool.google_api_toolset import GoogleApiToolset
    from google.adk.tools.base_toolset import BaseToolset
except ImportError as e:
    logger.warning(f"Some ADK tool types not available: {e}")
    # Fallback for development/testing
    BaseTool = Any
    FunctionTool = Any
    AgentTool = Any
    McpTool = Any
    McpToolset = Any
    RestApiTool = Any
    OpenAPIToolset = Any
    GoogleTool = Any
    GoogleApiTool = Any
    GoogleApiToolset = Any
    BaseToolset = Any

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


class ToolType(Enum):
    """Supported ADK tool types."""
    FUNCTION = "function"
    MCP = "mcp"
    OPENAPI = "openapi"
    AGENT = "agent"
    GOOGLE = "google"
    GOOGLE_API = "google_api"
    TOOLSET = "toolset"
    UNKNOWN = "unknown"


class ToolHealthStatus(Enum):
    """Tool-specific health status."""
    HEALTHY = "healthy"
    INITIALIZING = "initializing"
    LOADING = "loading"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    CONNECTION_ERROR = "connection_error"  # For MCP/API tools
    AUTH_ERROR = "auth_error"  # For authenticated tools


@dataclass
class ToolRegistrationEvent(RegistryEvent):
    """Tool-specific registration event."""
    
    tool_type: Optional[ToolType] = None
    """Type of the tool."""
    
    tool_version: Optional[str] = None
    """Version of the tool if available."""
    
    toolset_name: Optional[str] = None
    """Name of parent toolset if applicable."""
    
    has_auth: bool = False
    """Whether tool requires authentication."""
    
    connection_info: Optional[Dict[str, Any]] = None
    """Connection information for remote tools."""
    
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
        tool_type: Union[str, ToolType],
        strategy_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.tool = tool
        
        # Ensure tool_type is ToolType enum
        if isinstance(tool_type, str):
            try:
                self.tool_type = ToolType(tool_type.lower())
            except ValueError:
                self.tool_type = ToolType.UNKNOWN
        else:
            self.tool_type = tool_type
        
        self.strategy_name = strategy_name
        self.metadata = metadata or {}
        self.registered_at = self._get_current_timestamp()
        self.last_used = None
        self.usage_count = 0
        self.error_count = 0
        self.health_status = ToolHealthStatus.INITIALIZING
        self.has_auth = self._check_has_auth(tool)
    
    def mark_used(self) -> None:
        """Mark tool as used (for statistics)."""
        self.usage_count += 1
        self.last_used = self._get_current_timestamp()
    
    def mark_error(self) -> None:
        """Mark tool as having an error."""
        self.error_count += 1
    
    def _check_has_auth(self, tool: Any) -> bool:
        """Check if tool requires authentication."""
        # Check for common auth indicators
        auth_indicators = [
            'auth_scheme', 'auth_credential', '_credentials_manager', 
            '_auth_config', 'credentials_config', '_mcp_session_manager'
        ]
        
        return any(hasattr(tool, attr) and getattr(tool, attr) is not None for attr in auth_indicators)
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'tool_type': self.tool_type.value if isinstance(self.tool_type, ToolType) else str(self.tool_type),
            'strategy_name': self.strategy_name,
            'metadata': self.metadata.copy(),
            'registered_at': self.registered_at,
            'last_used': self.last_used,
            'usage_count': self.usage_count,
            'error_count': self.error_count,
            'health_status': self.health_status.value if isinstance(self.health_status, ToolHealthStatus) else str(self.health_status),
            'has_auth': self.has_auth,
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
        
        # Enhanced features for ADK tool support
        self._toolsets: Dict[str, BaseToolset] = {}
        self._tool_type_counters: Dict[ToolType, int] = {t: 0 for t in ToolType}
        
        logger.info(f"Initialized EnhancedToolRegistry '{config.name}' with dynamic_loading={config.enable_dynamic_loading}")
    
    def detect_tool_type(self, tool: Any) -> ToolType:
        """Detect tool type from tool object.
        
        Args:
            tool: Tool object to analyze
            
        Returns:
            Detected tool type
        """
        # Check instance types in order of specificity
        if isinstance(tool, GoogleApiTool):
            return ToolType.GOOGLE_API
        elif isinstance(tool, GoogleTool):
            return ToolType.GOOGLE
        elif isinstance(tool, AgentTool):
            return ToolType.AGENT
        elif isinstance(tool, McpTool):
            return ToolType.MCP
        elif isinstance(tool, RestApiTool):
            return ToolType.OPENAPI
        elif isinstance(tool, FunctionTool):
            return ToolType.FUNCTION
        elif isinstance(tool, BaseToolset):
            return ToolType.TOOLSET
        else:
            # Check for tool_type attribute or class name patterns
            if hasattr(tool, 'tool_type') and isinstance(getattr(tool, 'tool_type', None), str):
                try:
                    return ToolType(tool.tool_type.lower())
                except ValueError:
                    pass
            
            # Fallback to class name analysis
            class_name = tool.__class__.__name__.lower()
            if 'function' in class_name:
                return ToolType.FUNCTION
            elif 'mcp' in class_name:
                return ToolType.MCP
            elif 'openapi' in class_name or 'rest' in class_name:
                return ToolType.OPENAPI
            elif 'agent' in class_name:
                return ToolType.AGENT
            elif 'googleapi' in class_name or ('google' in class_name and 'api' in class_name):
                return ToolType.GOOGLE_API
            elif 'google' in class_name:
                return ToolType.GOOGLE
            elif 'toolset' in class_name:
                return ToolType.TOOLSET
            
            logger.warning(f"Could not detect tool type for {tool.__class__.__name__}, using UNKNOWN")
            return ToolType.UNKNOWN

    async def register_toolset(
        self,
        name: str,
        toolset: BaseToolset,
        auto_register_tools: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register a toolset and optionally its tools.
        
        Args:
            name: Toolset name
            toolset: Toolset instance
            auto_register_tools: Whether to auto-register all tools in the toolset
            metadata: Additional metadata
            
        Returns:
            True if registration successful
        """
        if name in self._toolsets:
            logger.warning(f"Toolset '{name}' already registered")
            return False
        
        self._toolsets[name] = toolset
        
        if auto_register_tools:
            try:
                tools = await toolset.get_tools()
                for tool in tools:
                    tool_name = f"{name}.{tool.name}"
                    tool_type = self.detect_tool_type(tool)
                    tool_metadata = (metadata or {}).copy()
                    tool_metadata['parent_toolset'] = name
                    
                    self.register_tool(tool_name, tool, tool_type.value, metadata=tool_metadata)
            
            except Exception as e:
                logger.error(f"Error auto-registering tools from toolset '{name}': {e}")
                # Cleanup partially registered tools
                for tool_name in list(self._registered_tools.keys()):
                    if tool_name.startswith(f"{name}."):
                        self.unregister_tool(tool_name)
                del self._toolsets[name]
                return False
        
        logger.info(f"Successfully registered toolset '{name}' with {len(await toolset.get_tools()) if auto_register_tools else 0} tools")
        return True

    def register_tool(
        self,
        name: str,
        tool: Any,
        tool_type: Optional[Union[str, ToolType]] = None,
        strategy_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a tool with enhanced features.
        
        Args:
            name: Tool name
            tool: Tool instance or callable
            tool_type: Type of tool (auto-detected if None)
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
        
        # Auto-detect tool type if not provided
        if tool_type is None:
            detected_tool_type = self.detect_tool_type(tool)
            logger.debug(f"Auto-detected tool type '{detected_tool_type.value}' for tool '{name}'")
        else:
            # Convert string to ToolType if needed
            if isinstance(tool_type, str):
                try:
                    detected_tool_type = ToolType(tool_type.lower())
                except ValueError:
                    detected_tool_type = ToolType.UNKNOWN
            else:
                detected_tool_type = tool_type
        
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
            if detected_tool_type.value not in self.config.allowed_tool_types:
                raise YamlSystemError(
                    f"Tool type '{detected_tool_type.value}' not in allowed types: {self.config.allowed_tool_types}",
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
        else:
            # Update tool type counter for new tools
            self._tool_type_counters[detected_tool_type] += 1
        
        # Create tool info
        tool_info = ToolInfo(
            name=name,
            tool=tool,
            tool_type=detected_tool_type,
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
                tool_type=detected_tool_type,
                has_auth=tool_info.has_auth,
                strategy_name=strategy_name,
                replaced_tool=replaced_tool,
                metadata=metadata
            )
            self._emit_event(event)
        
        operation = "Updated" if was_registered else "Registered"
        logger.info(f"{operation} tool '{name}' (type: {detected_tool_type.value}, strategy: {strategy_name})")
    
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
        
        # Update tool type counter
        self._tool_type_counters[tool_info.tool_type] = max(0, self._tool_type_counters[tool_info.tool_type] - 1)
        
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
    
    # Enhanced ADK tool type introspection methods
    def get_tool_types(self) -> Dict[ToolType, int]:
        """Get count of tools by type."""
        return self._tool_type_counters.copy()

    def get_tools_by_type(self, tool_type: ToolType) -> List[str]:
        """Get list of tool names by type."""
        return [name for name, tool_info in self._registered_tools.items() if tool_info.tool_type == tool_type]

    def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific tool."""
        tool_info = self._registered_tools.get(tool_name)
        return tool_info.metadata if tool_info else None

    def get_tool_health(self, tool_name: str) -> Optional[ToolHealthStatus]:
        """Get health status for a specific tool."""
        tool_info = self._registered_tools.get(tool_name)
        return tool_info.health_status if tool_info else None

    def get_registered_toolsets(self) -> List[str]:
        """Get list of registered toolset names."""
        return list(self._toolsets.keys())

    def get_toolset_tools(self, toolset_name: str) -> List[str]:
        """Get list of tools from a specific toolset."""
        if toolset_name not in self._toolsets:
            return []
        
        return [name for name, tool_info in self._registered_tools.items() 
                if tool_info.metadata.get('parent_toolset') == toolset_name]

    def get_authenticated_tools(self) -> List[str]:
        """Get list of tools that require authentication."""
        return [name for name, tool_info in self._registered_tools.items() if tool_info.has_auth]

    def get_tool_usage_stats(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get usage statistics for a specific tool."""
        tool_info = self._registered_tools.get(tool_name)
        if not tool_info:
            return None
        
        return {
            'usage_count': tool_info.usage_count,
            'error_count': tool_info.error_count,
            'error_rate': tool_info.error_count / max(tool_info.usage_count, 1),
            'last_used': tool_info.last_used,
            'registered_at': tool_info.registered_at
        }

    # Tool-Specific Registry Wrappers
    
    async def register_function_tool(
        self,
        name: str,
        function: Callable,
        metadata: Optional[Dict[str, Any]] = None,
        validate_signature: bool = True,
        validate_docstring: bool = True
    ) -> bool:
        """Register a FunctionTool with enhanced validation.
        
        Args:
            name: Tool name
            function: Python function to wrap
            metadata: Additional metadata
            validate_signature: Whether to validate function signature
            validate_docstring: Whether to validate docstring presence
            
        Returns:
            True if registration successful
        """
        try:
            # Validate function if enabled
            if validate_signature:
                if not callable(function):
                    raise YamlSystemError(
                        f"Function '{name}' is not callable",
                        context=self.yaml_context.with_tool(name),
                        suggested_fixes=["Provide a callable function"]
                    )
                
                # Check function signature
                try:
                    signature = inspect.signature(function)
                    params = signature.parameters
                    
                    # Function should have at least some parameters (excluding tool_context)
                    non_context_params = [p for p in params.values() 
                                        if p.name not in ['tool_context', 'input_stream']]
                    
                    if not non_context_params and not getattr(function, '__doc__', None):
                        logger.warning(f"Function '{name}' has no parameters and no docstring - may not be useful as a tool")
                
                except Exception as e:
                    raise YamlSystemError(
                        f"Cannot inspect function signature for '{name}': {e}",
                        context=self.yaml_context.with_tool(name),
                        original_error=e,
                        suggested_fixes=["Ensure function has proper signature"]
                    )
            
            if validate_docstring:
                if not getattr(function, '__doc__', None) or not function.__doc__.strip():
                    logger.warning(f"Function '{name}' has no docstring - tool description will be empty")
            
            # Create FunctionTool
            function_tool = FunctionTool(function)
            
            # Extract metadata
            extracted_metadata = await self._extract_function_tool_metadata(function_tool, function)
            if metadata:
                extracted_metadata.update(metadata)
            
            # Register tool
            self.register_tool(name, function_tool, ToolType.FUNCTION, metadata=extracted_metadata)
            
            logger.info(f"Successfully registered FunctionTool '{name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register FunctionTool '{name}': {e}")
            return False
    
    async def register_mcp_tool(
        self,
        name: str,
        mcp_tool: 'McpTool',
        metadata: Optional[Dict[str, Any]] = None,
        test_connection: bool = True
    ) -> bool:
        """Register an MCP tool with connection validation.
        
        Args:
            name: Tool name
            mcp_tool: MCP tool instance
            metadata: Additional metadata
            test_connection: Whether to test MCP connection
            
        Returns:
            True if registration successful
        """
        try:
            # Test MCP connection if enabled
            if test_connection and hasattr(mcp_tool, '_mcp_session_manager'):
                session_manager = mcp_tool._mcp_session_manager
                try:
                    # Try to create a session to test connectivity
                    session = await session_manager.create_session()
                    if not session:
                        raise YamlSystemError(
                            f"Cannot establish MCP session for tool '{name}'",
                            context=self.yaml_context.with_tool(name),
                            suggested_fixes=[
                                "Check MCP server is running",
                                "Verify connection parameters",
                                "Check authentication credentials"
                            ]
                        )
                except Exception as e:
                    logger.warning(f"MCP connection test failed for '{name}': {e}")
                    # Don't fail registration, but mark as connection error
                    if name in self._registered_tools:
                        self._registered_tools[name].health_status = ToolHealthStatus.CONNECTION_ERROR
            
            # Extract metadata
            extracted_metadata = await self._extract_mcp_tool_metadata(mcp_tool)
            if metadata:
                extracted_metadata.update(metadata)
            
            # Register tool
            self.register_tool(name, mcp_tool, ToolType.MCP, metadata=extracted_metadata)
            
            logger.info(f"Successfully registered MCP tool '{name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register MCP tool '{name}': {e}")
            return False
    
    async def register_openapi_tool(
        self,
        name: str,
        rest_api_tool: 'RestApiTool',
        metadata: Optional[Dict[str, Any]] = None,
        validate_schema: bool = True,
        test_endpoint: bool = False
    ) -> bool:
        """Register an OpenAPI/REST tool with schema validation.
        
        Args:
            name: Tool name
            rest_api_tool: REST API tool instance
            metadata: Additional metadata
            validate_schema: Whether to validate OpenAPI schema
            test_endpoint: Whether to test endpoint connectivity
            
        Returns:
            True if registration successful
        """
        try:
            # Validate schema if enabled
            if validate_schema:
                try:
                    declaration = rest_api_tool._get_declaration()
                    if not declaration:
                        logger.warning(f"OpenAPI tool '{name}' has no function declaration")
                    elif not declaration.parameters:
                        logger.warning(f"OpenAPI tool '{name}' has no parameters defined")
                
                except Exception as e:
                    logger.warning(f"Schema validation failed for OpenAPI tool '{name}': {e}")
            
            # Test endpoint connectivity if enabled
            if test_endpoint and hasattr(rest_api_tool, 'endpoint'):
                # Basic endpoint validation - don't make actual HTTP calls in registration
                endpoint = rest_api_tool.endpoint
                if endpoint and hasattr(endpoint, 'url'):
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(str(endpoint.url))
                        if not parsed.netloc:
                            logger.warning(f"OpenAPI tool '{name}' has invalid endpoint URL: {endpoint.url}")
                    except Exception as e:
                        logger.warning(f"Endpoint validation failed for '{name}': {e}")
            
            # Extract metadata
            extracted_metadata = await self._extract_openapi_tool_metadata(rest_api_tool)
            if metadata:
                extracted_metadata.update(metadata)
            
            # Register tool
            self.register_tool(name, rest_api_tool, ToolType.OPENAPI, metadata=extracted_metadata)
            
            logger.info(f"Successfully registered OpenAPI tool '{name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register OpenAPI tool '{name}': {e}")
            return False
    
    async def register_agent_tool(
        self,
        name: str,
        agent_tool: 'AgentTool',
        metadata: Optional[Dict[str, Any]] = None,
        validate_agent: bool = True
    ) -> bool:
        """Register an AgentTool with agent validation.
        
        Args:
            name: Tool name
            agent_tool: Agent tool instance
            metadata: Additional metadata
            validate_agent: Whether to validate wrapped agent
            
        Returns:
            True if registration successful
        """
        try:
            # Validate wrapped agent if enabled
            if validate_agent and hasattr(agent_tool, 'agent'):
                agent = agent_tool.agent
                
                # Check agent has required attributes
                if not hasattr(agent, 'name') or not agent.name:
                    logger.warning(f"AgentTool '{name}' wraps agent with no name")
                
                if not hasattr(agent, 'description') or not agent.description:
                    logger.warning(f"AgentTool '{name}' wraps agent with no description")
                
                # Check for circular references
                if hasattr(agent, 'name') and agent.name == name:
                    logger.warning(f"Potential circular reference: AgentTool '{name}' wraps agent with same name")
            
            # Extract metadata
            extracted_metadata = await self._extract_agent_tool_metadata(agent_tool)
            if metadata:
                extracted_metadata.update(metadata)
            
            # Register tool
            self.register_tool(name, agent_tool, ToolType.AGENT, metadata=extracted_metadata)
            
            logger.info(f"Successfully registered AgentTool '{name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register AgentTool '{name}': {e}")
            return False
    
    async def register_google_tool(
        self,
        name: str,
        google_tool: Union['GoogleTool', 'GoogleApiTool'],
        metadata: Optional[Dict[str, Any]] = None,
        validate_credentials: bool = True
    ) -> bool:
        """Register a Google tool with credential validation.
        
        Args:
            name: Tool name
            google_tool: Google tool instance
            metadata: Additional metadata
            validate_credentials: Whether to validate Google credentials
            
        Returns:
            True if registration successful
        """
        try:
            # Try isinstance check first, fallback to detection logic
            if isinstance(google_tool, GoogleApiTool):
                tool_type = ToolType.GOOGLE_API
            elif isinstance(google_tool, GoogleTool):
                tool_type = ToolType.GOOGLE
            else:
                # Fallback to detection logic for tests/mocks
                tool_type = self.detect_tool_type(google_tool)
            
            # Validate credentials if enabled
            if validate_credentials:
                has_credentials = False
                
                if isinstance(google_tool, GoogleTool) and hasattr(google_tool, '_credentials_manager'):
                    has_credentials = google_tool._credentials_manager is not None
                elif isinstance(google_tool, GoogleApiTool):
                    # Check for auth configuration in wrapped REST tool
                    if hasattr(google_tool, '_rest_api_tool'):
                        rest_tool = google_tool._rest_api_tool
                        has_credentials = (
                            hasattr(rest_tool, 'auth_credential') and rest_tool.auth_credential is not None
                        ) or (
                            hasattr(rest_tool, 'auth_scheme') and rest_tool.auth_scheme is not None
                        )
                
                if not has_credentials:
                    logger.warning(f"Google tool '{name}' has no credentials configured - may fail at runtime")
            
            # Extract metadata
            extracted_metadata = await self._extract_google_tool_metadata(google_tool)
            if metadata:
                extracted_metadata.update(metadata)
            
            # Register tool
            self.register_tool(name, google_tool, tool_type, metadata=extracted_metadata)
            
            logger.info(f"Successfully registered {tool_type.value} tool '{name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register Google tool '{name}': {e}")
            return False
    
    # Enhanced Metadata Extraction Methods
    
    async def _extract_function_tool_metadata(self, function_tool: FunctionTool, original_function: Callable) -> Dict[str, Any]:
        """Extract comprehensive metadata from FunctionTool."""
        metadata = {
            'tool_type': 'function',
            'function_name': getattr(original_function, '__name__', 'unknown'),
            'module': getattr(original_function, '__module__', 'unknown'),
            'is_coroutine': inspect.iscoroutinefunction(original_function),
            'docstring': getattr(original_function, '__doc__', '').strip() if getattr(original_function, '__doc__', None) else None
        }
        
        try:
            # Extract signature information
            signature = inspect.signature(original_function)
            metadata.update({
                'signature': str(signature),
                'parameters': {
                    name: {
                        'kind': str(param.kind),
                        'default': str(param.default) if param.default != inspect.Parameter.empty else None,
                        'annotation': str(param.annotation) if param.annotation != inspect.Parameter.empty else None
                    }
                    for name, param in signature.parameters.items()
                },
                'mandatory_args': function_tool._get_mandatory_args() if hasattr(function_tool, '_get_mandatory_args') else [],
                'ignore_params': getattr(function_tool, '_ignore_params', [])
            })
        except Exception as e:
            logger.debug(f"Could not extract signature metadata: {e}")
            metadata['signature_error'] = str(e)
        
        # Extract function declaration
        try:
            declaration = function_tool._get_declaration()
            if declaration:
                metadata['function_declaration'] = {
                    'name': declaration.name,
                    'description': declaration.description,
                    'has_parameters': declaration.parameters is not None
                }
        except Exception as e:
            logger.debug(f"Could not extract function declaration: {e}")
        
        return metadata
    
    async def _extract_mcp_tool_metadata(self, mcp_tool: 'McpTool') -> Dict[str, Any]:
        """Extract comprehensive metadata from MCP tool."""
        metadata = {
            'tool_type': 'mcp',
            'has_session_manager': hasattr(mcp_tool, '_mcp_session_manager')
        }
        
        # Extract MCP-specific information
        if hasattr(mcp_tool, '_mcp_tool'):
            mcp_base_tool = mcp_tool._mcp_tool
            metadata.update({
                'mcp_name': getattr(mcp_base_tool, 'name', None),
                'mcp_description': getattr(mcp_base_tool, 'description', None),
                'input_schema': getattr(mcp_base_tool, 'inputSchema', None)
            })
        
        # Extract session manager information
        if hasattr(mcp_tool, '_mcp_session_manager'):
            session_manager = mcp_tool._mcp_session_manager
            metadata.update({
                'session_manager_type': session_manager.__class__.__name__,
                'connection_params_type': getattr(session_manager, '_connection_params', {}).get('type', 'unknown') if hasattr(session_manager, '_connection_params') else 'unknown'
            })
        
        # Check authentication configuration
        auth_info = {}
        if hasattr(mcp_tool, '_credentials_manager') and mcp_tool._credentials_manager:
            auth_info['has_credentials_manager'] = True
        if hasattr(mcp_tool, '_auth_config') and mcp_tool._auth_config:
            auth_info['has_auth_config'] = True
        metadata['auth_info'] = auth_info
        
        return metadata
    
    async def _extract_openapi_tool_metadata(self, rest_api_tool: 'RestApiTool') -> Dict[str, Any]:
        """Extract comprehensive metadata from OpenAPI/REST tool."""
        metadata = {
            'tool_type': 'openapi'
        }
        
        # Extract endpoint information
        if hasattr(rest_api_tool, 'endpoint'):
            endpoint = rest_api_tool.endpoint
            if endpoint:
                metadata.update({
                    'endpoint': str(endpoint),
                    'has_endpoint': True
                })
                
                # Try to extract URL and method
                if hasattr(endpoint, 'url'):
                    metadata['endpoint_url'] = str(endpoint.url)
                if hasattr(endpoint, 'method'):
                    metadata['http_method'] = str(endpoint.method)
        
        # Extract operation information
        if hasattr(rest_api_tool, 'operation'):
            operation = rest_api_tool.operation
            if operation:
                metadata.update({
                    'has_operation': True,
                    'operation_id': getattr(operation, 'operationId', None),
                    'http_method': getattr(operation, 'method', None) if hasattr(operation, 'method') else None
                })
        
        # Extract authentication information
        auth_info = {}
        if hasattr(rest_api_tool, 'auth_scheme') and rest_api_tool.auth_scheme:
            auth_info['has_auth_scheme'] = True
            auth_info['auth_scheme_type'] = rest_api_tool.auth_scheme.__class__.__name__
        if hasattr(rest_api_tool, 'auth_credential') and rest_api_tool.auth_credential:
            auth_info['has_auth_credential'] = True
        metadata['auth_info'] = auth_info
        
        # Extract function declaration
        try:
            declaration = rest_api_tool._get_declaration()
            if declaration:
                metadata['function_declaration'] = {
                    'name': declaration.name,
                    'description': declaration.description,
                    'has_parameters': declaration.parameters is not None
                }
        except Exception as e:
            logger.debug(f"Could not extract function declaration from REST tool: {e}")
        
        return metadata
    
    async def _extract_agent_tool_metadata(self, agent_tool: 'AgentTool') -> Dict[str, Any]:
        """Extract comprehensive metadata from AgentTool."""
        metadata = {
            'tool_type': 'agent',
            'skip_summarization': getattr(agent_tool, 'skip_summarization', False)
        }
        
        # Extract wrapped agent information
        if hasattr(agent_tool, 'agent'):
            agent = agent_tool.agent
            metadata.update({
                'agent_name': getattr(agent, 'name', None),
                'agent_description': getattr(agent, 'description', None),
                'agent_class': agent.__class__.__name__,
                'agent_module': agent.__class__.__module__
            })
            
            # Check for schemas
            schema_info = {}
            if hasattr(agent, 'input_schema'):
                schema_info['has_input_schema'] = agent.input_schema is not None
                if agent.input_schema:
                    schema_info['input_schema_type'] = agent.input_schema.__class__.__name__
            
            if hasattr(agent, 'output_schema'):
                schema_info['has_output_schema'] = agent.output_schema is not None  
                if agent.output_schema:
                    schema_info['output_schema_type'] = agent.output_schema.__class__.__name__
            
            metadata['schema_info'] = schema_info
        
        # Extract function declaration
        try:
            declaration = agent_tool._get_declaration()
            if declaration:
                metadata['function_declaration'] = {
                    'name': declaration.name,
                    'description': declaration.description,
                    'has_parameters': declaration.parameters is not None,
                    'has_response_schema': hasattr(declaration, 'response') and declaration.response is not None
                }
        except Exception as e:
            logger.debug(f"Could not extract function declaration from AgentTool: {e}")
        
        return metadata
    
    async def _extract_google_tool_metadata(self, google_tool: Union['GoogleTool', 'GoogleApiTool']) -> Dict[str, Any]:
        """Extract comprehensive metadata from Google tools."""
        if isinstance(google_tool, GoogleApiTool):
            metadata = await self._extract_google_api_tool_metadata(google_tool)
        elif isinstance(google_tool, GoogleTool):
            metadata = await self._extract_google_base_tool_metadata(google_tool)
        else:
            metadata = {'tool_type': 'google', 'subtype': 'unknown'}
        
        return metadata
    
    async def _extract_google_api_tool_metadata(self, google_api_tool: 'GoogleApiTool') -> Dict[str, Any]:
        """Extract metadata from GoogleApiTool."""
        metadata = {
            'tool_type': 'google_api',
            'is_wrapper': True
        }
        
        # Extract wrapped REST API tool information
        if hasattr(google_api_tool, '_rest_api_tool'):
            rest_tool = google_api_tool._rest_api_tool
            metadata.update({
                'wraps_rest_tool': True,
                'rest_tool_name': getattr(rest_tool, 'name', None),
                'rest_tool_description': getattr(rest_tool, 'description', None),
                'rest_tool_class': rest_tool.__class__.__name__
            })
            
            # Get OpenAPI metadata from wrapped tool
            rest_metadata = await self._extract_openapi_tool_metadata(rest_tool)
            metadata['rest_tool_metadata'] = rest_metadata
        
        # Extract Google-specific auth information
        auth_info = {}
        if hasattr(google_api_tool, '_client_id'):
            auth_info['has_client_id'] = getattr(google_api_tool, '_client_id') is not None
        if hasattr(google_api_tool, '_client_secret'):
            auth_info['has_client_secret'] = getattr(google_api_tool, '_client_secret') is not None
        if hasattr(google_api_tool, '_service_account'):
            auth_info['has_service_account'] = getattr(google_api_tool, '_service_account') is not None
        metadata['google_auth_info'] = auth_info
        
        return metadata
    
    async def _extract_google_base_tool_metadata(self, google_tool: 'GoogleTool') -> Dict[str, Any]:
        """Extract metadata from GoogleTool."""
        metadata = {
            'tool_type': 'google',
            'is_function_tool_subclass': True
        }
        
        # Extract credentials manager information
        if hasattr(google_tool, '_credentials_manager'):
            creds_manager = google_tool._credentials_manager
            metadata.update({
                'has_credentials_manager': creds_manager is not None,
                'credentials_manager_type': creds_manager.__class__.__name__ if creds_manager else None
            })
        
        # Extract tool settings information
        if hasattr(google_tool, '_tool_settings'):
            settings = google_tool._tool_settings
            metadata.update({
                'has_tool_settings': settings is not None,
                'tool_settings_type': settings.__class__.__name__ if settings else None
            })
        
        # Extract function information (since GoogleTool extends FunctionTool)
        if hasattr(google_tool, 'func'):
            func_metadata = await self._extract_function_tool_metadata(google_tool, google_tool.func)
            metadata['function_metadata'] = func_metadata
        
        return metadata

    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def __repr__(self) -> str:
        """String representation of the registry."""
        tool_count = len(self._registered_tools)
        strategy_count = len(self.strategies)
        return f"EnhancedToolRegistry(name='{self.name}', tools={tool_count}, strategies={strategy_count}, started={self._is_started})"