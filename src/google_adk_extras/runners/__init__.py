"""Enhanced ADK Runners for YAML-driven agent systems.

This package provides enhanced runners that extend Google ADK's capabilities
to support YAML-driven configuration, better error handling, tool execution
strategies, and integration with agent-compose-kit.

Key Features:
- EnhancedRunner: Drop-in replacement for ADK Runner with advanced features
- EnhancedRunConfig: YAML-driven configuration with tool-specific settings
- YAML System Error Handling: Rich error context for debugging
- Tool Execution Strategies: Configurable execution for different tool types
- Registry Integration: Work with agent and tool registries
- A2A Remote Agent Support: Enhanced timeout and retry for A2A agents

Examples:
    Basic usage as drop-in replacement:
    ```python
    from google_adk_extras.runners import EnhancedRunner, EnhancedRunConfig
    
    config = EnhancedRunConfig.from_yaml_dict({
        'tool_timeouts': {'mcp_tools': 30.0, 'openapi_tools': 60.0},
        'retry_policies': {'default': {'max_attempts': 3}}
    })
    
    runner = EnhancedRunner(
        app_name="yaml-system",
        agent=root_agent, 
        session_service=session_service,
        enhanced_config=config
    )
    ```
    
    Integration with agent-compose-kit:
    ```python
    from google_adk_extras.integration.agent_compose_kit import build_enhanced_runner
    
    runner = build_enhanced_runner(
        app_name=cfg.name,
        agent=root_agent,
        services=services,
        runtime_config=cfg.runtime,  # From YAML
        tool_registry=tool_registry,
        agent_registry=agent_registry,
    )
    ```
"""

from .config import EnhancedRunConfig, ToolTimeoutConfig, RetryConfig, A2AConfig
from .enhanced_runner import EnhancedRunner
from .errors import YamlSystemError, YamlSystemContext, ToolExecutionError
from .strategies import (
    ToolExecutionStrategy, 
    DefaultToolExecutionStrategy,
    McpToolExecutionStrategy,
    OpenApiToolExecutionStrategy,
    FunctionToolExecutionStrategy
)

__all__ = [
    # Core enhanced runner
    'EnhancedRunner',
    'EnhancedRunConfig',
    
    # Configuration models
    'ToolTimeoutConfig', 
    'RetryConfig',
    'A2AConfig',
    
    # Error handling
    'YamlSystemError',
    'YamlSystemContext', 
    'ToolExecutionError',
    
    # Tool execution strategies
    'ToolExecutionStrategy',
    'DefaultToolExecutionStrategy',
    'McpToolExecutionStrategy', 
    'OpenApiToolExecutionStrategy',
    'FunctionToolExecutionStrategy',
]