"""Enhanced error handling for YAML-driven agent systems.

This module provides rich error handling capabilities that preserve context
about which YAML system, agent, or tool caused an error, making debugging
significantly easier for complex agent compositions.
"""

import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


@dataclass
class YamlSystemContext:
    """Context information for YAML-driven agent systems.
    
    This class captures the current execution context within a YAML system,
    providing valuable debugging information when errors occur.
    
    Attributes:
        system_name: Name of the YAML system being executed
        config_path: Path to the YAML configuration file
        current_agent: Name of the currently executing agent
        current_tool: Name of the currently executing tool (if any)
        invocation_id: Current invocation ID for tracing
        session_id: Current session ID
        user_id: Current user ID
        additional_context: Any additional context information
    
    Examples:
        Basic context:
        ```python
        context = YamlSystemContext(
            system_name="customer-support",
            config_path="/path/to/config.yaml",
            current_agent="main_agent"
        )
        ```
        
        Full context with tool execution:
        ```python
        context = YamlSystemContext(
            system_name="data-pipeline",
            config_path="/path/to/config.yaml", 
            current_agent="processor_agent",
            current_tool="extract_data",
            invocation_id="inv_123",
            session_id="sess_456",
            user_id="user_789"
        )
        ```
    """
    
    system_name: str
    """Name of the YAML system being executed."""
    
    config_path: Optional[Union[str, Path]] = None
    """Path to the YAML configuration file."""
    
    current_agent: Optional[str] = None
    """Name of the currently executing agent."""
    
    current_tool: Optional[str] = None
    """Name of the currently executing tool."""
    
    invocation_id: Optional[str] = None
    """Current invocation ID for tracing."""
    
    session_id: Optional[str] = None
    """Current session ID."""
    
    user_id: Optional[str] = None
    """Current user ID."""
    
    additional_context: Dict[str, Any] = field(default_factory=dict)
    """Additional context information."""
    
    def with_agent(self, agent_name: str) -> 'YamlSystemContext':
        """Create a new context with the specified agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            YamlSystemContext: New context with updated agent
        """
        return YamlSystemContext(
            system_name=self.system_name,
            config_path=self.config_path,
            current_agent=agent_name,
            current_tool=None,  # Reset tool when changing agents
            invocation_id=self.invocation_id,
            session_id=self.session_id,
            user_id=self.user_id,
            additional_context=self.additional_context.copy()
        )
    
    def with_tool(self, tool_name: str) -> 'YamlSystemContext':
        """Create a new context with the specified tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            YamlSystemContext: New context with updated tool
        """
        return YamlSystemContext(
            system_name=self.system_name,
            config_path=self.config_path,
            current_agent=self.current_agent,
            current_tool=tool_name,
            invocation_id=self.invocation_id,
            session_id=self.session_id,
            user_id=self.user_id,
            additional_context=self.additional_context.copy()
        )
    
    def with_invocation(self, invocation_id: str, session_id: str, user_id: str) -> 'YamlSystemContext':
        """Create a new context with invocation details.
        
        Args:
            invocation_id: Invocation ID
            session_id: Session ID  
            user_id: User ID
            
        Returns:
            YamlSystemContext: New context with updated invocation details
        """
        return YamlSystemContext(
            system_name=self.system_name,
            config_path=self.config_path,
            current_agent=self.current_agent,
            current_tool=self.current_tool,
            invocation_id=invocation_id,
            session_id=session_id,
            user_id=user_id,
            additional_context=self.additional_context.copy()
        )
    
    def add_context(self, key: str, value: Any) -> 'YamlSystemContext':
        """Add additional context information.
        
        Args:
            key: Context key
            value: Context value
            
        Returns:
            YamlSystemContext: New context with additional information
        """
        new_context = self.additional_context.copy()
        new_context[key] = value
        
        return YamlSystemContext(
            system_name=self.system_name,
            config_path=self.config_path,
            current_agent=self.current_agent,
            current_tool=self.current_tool,
            invocation_id=self.invocation_id,
            session_id=self.session_id,
            user_id=self.user_id,
            additional_context=new_context
        )
    
    def get_location_string(self) -> str:
        """Get a human-readable location string.
        
        Returns:
            str: Location string for debugging
        """
        parts = [self.system_name]
        
        if self.current_agent:
            parts.append(f"agent:{self.current_agent}")
        
        if self.current_tool:
            parts.append(f"tool:{self.current_tool}")
        
        return " -> ".join(parts)


class YamlSystemError(Exception):
    """Enhanced error with YAML system context.
    
    This exception class provides rich context about errors that occur
    within YAML-driven agent systems, making debugging much easier.
    
    Attributes:
        message: The error message
        context: YAML system context where the error occurred
        original_error: The original exception that was wrapped (if any)
        error_code: Optional error code for categorization
        suggested_fixes: List of suggested fixes for the error
        
    Examples:
        Basic error with context:
        ```python
        raise YamlSystemError(
            "Tool execution failed",
            context=YamlSystemContext(
                system_name="my-system",
                current_agent="processor",
                current_tool="extract_data"
            )
        )
        ```
        
        Wrapping an original error:
        ```python
        try:
            # Some operation that fails
            pass
        except Exception as e:
            raise YamlSystemError(
                "Configuration validation failed",
                context=context,
                original_error=e,
                suggested_fixes=[
                    "Check YAML syntax in config file",
                    "Verify all required fields are present"
                ]
            )
        ```
    """
    
    def __init__(
        self,
        message: str,
        context: YamlSystemContext,
        original_error: Optional[Exception] = None,
        error_code: Optional[str] = None,
        suggested_fixes: Optional[List[str]] = None
    ):
        """Initialize YamlSystemError.
        
        Args:
            message: The error message
            context: YAML system context
            original_error: Original exception that was wrapped
            error_code: Optional error code
            suggested_fixes: List of suggested fixes
        """
        self.context = context
        self.original_error = original_error
        self.error_code = error_code
        self.suggested_fixes = suggested_fixes or []
        
        # Build comprehensive error message
        location = context.get_location_string()
        full_message = f"[{location}] {message}"
        
        # Add original error details if available
        if original_error:
            full_message += f"\n  Caused by: {type(original_error).__name__}: {str(original_error)}"
        
        # Add error code if available
        if error_code:
            full_message += f"\n  Error Code: {error_code}"
        
        # Add suggested fixes
        if suggested_fixes:
            full_message += "\n  Suggested fixes:"
            for i, fix in enumerate(suggested_fixes, 1):
                full_message += f"\n    {i}. {fix}"
        
        super().__init__(full_message)
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get comprehensive debug information.
        
        Returns:
            Dict[str, Any]: Debug information dictionary
        """
        debug_info = {
            'error_type': type(self).__name__,
            'message': str(self),
            'context': {
                'system_name': self.context.system_name,
                'config_path': str(self.context.config_path) if self.context.config_path else None,
                'current_agent': self.context.current_agent,
                'current_tool': self.context.current_tool,
                'invocation_id': self.context.invocation_id,
                'session_id': self.context.session_id,
                'user_id': self.context.user_id,
                'additional_context': self.context.additional_context,
            },
            'error_code': self.error_code,
            'suggested_fixes': self.suggested_fixes,
        }
        
        if self.original_error:
            debug_info['original_error'] = {
                'type': type(self.original_error).__name__,
                'message': str(self.original_error),
                'traceback': traceback.format_exception(
                    type(self.original_error),
                    self.original_error,
                    self.original_error.__traceback__
                )
            }
        
        return debug_info


class ToolExecutionError(YamlSystemError):
    """Specific error for tool execution failures.
    
    This error provides additional context specific to tool execution,
    including tool type, execution time, and tool-specific debugging info.
    
    Examples:
        Tool timeout error:
        ```python
        raise ToolExecutionError(
            "Tool execution timed out",
            context=context.with_tool("extract_data"),
            tool_type="mcp",
            execution_time=30.5,
            timeout=30.0,
            suggested_fixes=[
                "Increase tool timeout in configuration",
                "Check if MCP server is responsive"
            ]
        )
        ```
    """
    
    def __init__(
        self,
        message: str,
        context: YamlSystemContext,
        tool_type: Optional[str] = None,
        execution_time: Optional[float] = None,
        timeout: Optional[float] = None,
        **kwargs
    ):
        """Initialize ToolExecutionError.
        
        Args:
            message: The error message
            context: YAML system context
            tool_type: Type of tool (mcp, openapi, function)
            execution_time: How long the tool ran before failing
            timeout: The configured timeout value
            **kwargs: Additional arguments for YamlSystemError
        """
        self.tool_type = tool_type
        self.execution_time = execution_time
        self.timeout = timeout
        
        # Enhance message with tool-specific info
        enhanced_message = message
        if tool_type:
            enhanced_message += f" (tool_type: {tool_type})"
        if execution_time and timeout:
            enhanced_message += f" (executed for {execution_time:.1f}s, timeout: {timeout:.1f}s)"
        
        super().__init__(enhanced_message, context, **kwargs)


class ConfigurationError(YamlSystemError):
    """Error for YAML configuration issues.
    
    This error is raised when there are problems with YAML configuration
    files, missing required fields, invalid values, etc.
    
    Examples:
        Missing required field:
        ```python
        raise ConfigurationError(
            "Missing required field 'model' in agent configuration",
            context=context.with_agent("main_agent"),
            config_path="/path/to/config.yaml",
            config_section="agents[0]",
            suggested_fixes=[
                "Add 'model' field to agent configuration",
                "Check example configurations for required fields"
            ]
        )
        ```
    """
    
    def __init__(
        self,
        message: str,
        context: YamlSystemContext,
        config_path: Optional[Union[str, Path]] = None,
        config_section: Optional[str] = None,
        **kwargs
    ):
        """Initialize ConfigurationError.
        
        Args:
            message: The error message
            context: YAML system context
            config_path: Path to the problematic config file
            config_section: Specific section of config with the error
            **kwargs: Additional arguments for YamlSystemError
        """
        self.config_path = Path(config_path) if config_path else None
        self.config_section = config_section
        
        # Enhance message with config-specific info
        enhanced_message = message
        if config_section:
            enhanced_message += f" (section: {config_section})"
        if config_path:
            enhanced_message += f" (file: {config_path})"
        
        super().__init__(enhanced_message, context, **kwargs)


class RegistryError(YamlSystemError):
    """Error for agent/tool registry issues.
    
    This error is raised when there are problems with agent or tool
    registries, such as missing agents, circular dependencies, etc.
    
    Examples:
        Missing agent in registry:
        ```python
        raise RegistryError(
            f"Agent '{agent_name}' not found in registry",
            context=context,
            registry_type="agent",
            missing_item=agent_name,
            suggested_fixes=[
                f"Add agent '{agent_name}' to the system configuration",
                "Check agent name spelling and case sensitivity"
            ]
        )
        ```
    """
    
    def __init__(
        self,
        message: str,
        context: YamlSystemContext,
        registry_type: Optional[str] = None,
        missing_item: Optional[str] = None,
        **kwargs
    ):
        """Initialize RegistryError.
        
        Args:
            message: The error message
            context: YAML system context
            registry_type: Type of registry (agent, tool)
            missing_item: Name of the missing item
            **kwargs: Additional arguments for YamlSystemError
        """
        self.registry_type = registry_type
        self.missing_item = missing_item
        
        # Enhance message with registry-specific info
        enhanced_message = message
        if registry_type and missing_item:
            enhanced_message += f" ({registry_type} registry: {missing_item})"
        
        super().__init__(enhanced_message, context, **kwargs)