"""Enhanced configuration classes for YAML-driven runner behavior.

This module provides configuration models that extend ADK's RunConfig
to support YAML-driven agent systems with advanced features.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from google.adk.agents.run_config import RunConfig, StreamingMode
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class RetryStrategy(str, Enum):
    """Retry strategy options."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"
    LINEAR_BACKOFF = "linear_backoff"
    IMMEDIATE = "immediate"


class CircuitBreakerState(str, Enum):
    """Circuit breaker state options."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry policies."""
    
    max_attempts: int = 3
    """Maximum number of retry attempts."""
    
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    """Retry strategy to use."""
    
    base_delay: float = 1.0
    """Base delay in seconds for retry strategies."""
    
    max_delay: float = 60.0
    """Maximum delay in seconds between retries."""
    
    backoff_multiplier: float = 2.0
    """Multiplier for exponential backoff."""
    
    jitter: bool = True
    """Whether to add random jitter to delays."""


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""
    
    failure_threshold: int = 5
    """Number of failures before opening circuit."""
    
    recovery_timeout: float = 60.0
    """Time to wait before attempting recovery."""
    
    success_threshold: int = 3
    """Number of successes needed to close circuit from half-open."""
    
    timeout: float = 30.0
    """Timeout for individual requests."""


@dataclass
class ToolTimeoutConfig:
    """Configuration for tool-specific timeouts."""
    
    # Tool type timeouts
    mcp_tools: float = 30.0
    """Timeout for MCP toolset operations."""
    
    openapi_tools: float = 60.0
    """Timeout for OpenAPI tool calls."""
    
    function_tools: float = 10.0
    """Timeout for Python function tools."""
    
    # Connection timeouts  
    mcp_connection_timeout: float = 10.0
    """Timeout for MCP server connections."""
    
    openapi_connection_timeout: float = 15.0
    """Timeout for OpenAPI service connections."""
    
    # Per-tool overrides
    tool_specific_timeouts: Dict[str, float] = field(default_factory=dict)
    """Override timeouts for specific tool names."""
    
    def get_timeout_for_tool(self, tool_name: str, tool_type: str = "function") -> float:
        """Get timeout for a specific tool."""
        # Check tool-specific override first
        if tool_name in self.tool_specific_timeouts:
            return self.tool_specific_timeouts[tool_name]
            
        # Use type-based default
        type_timeouts = {
            "mcp": self.mcp_tools,
            "openapi": self.openapi_tools, 
            "function": self.function_tools,
        }
        
        return type_timeouts.get(tool_type, self.function_tools)


@dataclass
class A2AConfig:
    """Configuration for A2A remote agents."""
    
    timeout: float = 30.0
    """Default timeout for A2A agent calls."""
    
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    """Retry configuration for A2A calls."""
    
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    """Circuit breaker configuration for A2A calls."""
    
    connection_pool_size: int = 10
    """Connection pool size for A2A clients."""


@dataclass  
class DebugConfig:
    """Configuration for debugging and development features."""
    
    enabled: bool = False
    """Whether debug mode is enabled."""
    
    trace_agent_flow: bool = False
    """Whether to trace agent selection flow."""
    
    trace_tool_execution: bool = False
    """Whether to trace tool execution."""
    
    performance_profiling: bool = False
    """Whether to enable performance profiling."""
    
    log_level: str = "INFO"
    """Logging level for debug output."""
    
    capture_exceptions: bool = True
    """Whether to capture detailed exception information."""


class EnhancedRunConfig(BaseModel):
    """Enhanced runtime configuration that extends ADK's RunConfig.
    
    This configuration class provides YAML-driven control over runner behavior
    beyond what ADK's basic RunConfig supports. It's designed to integrate
    seamlessly with agent-compose-kit's runtime configuration.
    
    Examples:
        From YAML runtime section:
        ```python
        yaml_config = {
            'streaming_mode': 'NONE',
            'max_llm_calls': 200,
            'tool_timeouts': {
                'mcp_tools': 30.0,
                'openapi_tools': 60.0
            },
            'retry_policies': {
                'default': {'max_attempts': 3}
            }
        }
        
        config = EnhancedRunConfig.from_yaml_dict(yaml_config)
        ```
        
        Direct creation:
        ```python
        config = EnhancedRunConfig(
            base_config=RunConfig(max_llm_calls=200),
            tool_timeouts=ToolTimeoutConfig(mcp_tools=45.0),
            enable_circuit_breaker=True
        )
        ```
    """
    
    model_config = ConfigDict(
        extra='allow',  # Allow extra fields for flexibility
        validate_assignment=True,
    )
    
    # Base ADK configuration
    base_config: RunConfig = Field(default_factory=RunConfig)
    """Underlying ADK RunConfig that this enhances."""
    
    # Enhanced tool configuration
    tool_timeouts: ToolTimeoutConfig = Field(default_factory=ToolTimeoutConfig)
    """Timeout configuration for different tool types."""
    
    retry_policies: Dict[str, RetryConfig] = Field(default_factory=lambda: {
        'default': RetryConfig(),
        'mcp_tools': RetryConfig(max_attempts=2, base_delay=0.5),
        'openapi_tools': RetryConfig(max_attempts=3, base_delay=1.0),
    })
    """Retry policies for different operation types."""
    
    # A2A configuration
    a2a_config: A2AConfig = Field(default_factory=A2AConfig)
    """Configuration for A2A remote agents."""
    
    # Error handling configuration
    enable_circuit_breaker: bool = False
    """Whether to enable circuit breaker pattern for external services."""
    
    circuit_breaker_config: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    """Circuit breaker configuration."""
    
    # Registry integration
    enable_tool_registry: bool = True
    """Whether to enable tool registry integration."""
    
    enable_agent_registry: bool = True
    """Whether to enable agent registry integration."""
    
    # Performance configuration
    max_concurrent_tools: int = 5
    """Maximum number of concurrent tool executions."""
    
    tool_execution_queue_size: int = 100
    """Size of the tool execution queue."""
    
    # Development and debugging
    debug_config: DebugConfig = Field(default_factory=DebugConfig)
    """Debug and development configuration."""
    
    # Compatibility and validation
    validate_tool_configs: bool = True
    """Whether to validate tool configurations at startup."""
    
    strict_mode: bool = False
    """Whether to operate in strict mode (fail fast on configuration errors)."""
    
    @classmethod
    def from_yaml_dict(cls, yaml_config: Dict[str, Any]) -> 'EnhancedRunConfig':
        """Create EnhancedRunConfig from YAML runtime configuration.
        
        This method processes agent-compose-kit's runtime YAML sections
        and creates an appropriate enhanced configuration.
        
        Args:
            yaml_config: Dictionary from YAML runtime section
            
        Returns:
            EnhancedRunConfig: Configured instance
            
        Examples:
            ```python
            yaml_runtime = {
                'streaming_mode': 'NONE',
                'max_llm_calls': 200,
                'tool_timeouts': {
                    'mcp_tools': 30.0,
                    'function_tools': 5.0
                },
                'retry_policies': {
                    'default': {'max_attempts': 3, 'base_delay': 1.0}
                },
                'debug': {'enabled': True, 'trace_agent_flow': True}
            }
            
            config = EnhancedRunConfig.from_yaml_dict(yaml_runtime)
            ```
        """
        logger.debug(f"Creating EnhancedRunConfig from YAML: {yaml_config}")
        
        # Extract base ADK RunConfig fields
        base_config_fields = {
            'speech_config', 'response_modalities', 'save_input_blobs_as_artifacts',
            'support_cfc', 'streaming_mode', 'output_audio_transcription',
            'input_audio_transcription', 'realtime_input_config', 
            'enable_affective_dialog', 'proactivity', 'session_resumption', 'max_llm_calls'
        }
        
        base_config_data = {k: v for k, v in yaml_config.items() if k in base_config_fields}
        
        # Handle streaming_mode enum conversion
        if 'streaming_mode' in base_config_data:
            streaming_value = base_config_data['streaming_mode']
            if isinstance(streaming_value, str):
                base_config_data['streaming_mode'] = StreamingMode[streaming_value]
        
        # Create base config
        base_config = RunConfig(**base_config_data)
        
        # Extract enhanced configuration
        enhanced_data = {}
        
        # Tool timeouts
        if 'tool_timeouts' in yaml_config:
            timeout_data = yaml_config['tool_timeouts']
            enhanced_data['tool_timeouts'] = ToolTimeoutConfig(**timeout_data)
        
        # Retry policies
        if 'retry_policies' in yaml_config:
            retry_data = yaml_config['retry_policies']
            retry_configs = {}
            for name, config in retry_data.items():
                if isinstance(config, dict):
                    # Convert strategy string to enum if present
                    if 'strategy' in config:
                        config['strategy'] = RetryStrategy(config['strategy'])
                    retry_configs[name] = RetryConfig(**config)
                else:
                    retry_configs[name] = config
            enhanced_data['retry_policies'] = retry_configs
        
        # A2A configuration
        if 'a2a_config' in yaml_config:
            a2a_data = yaml_config['a2a_config']
            if 'retry_config' in a2a_data and isinstance(a2a_data['retry_config'], dict):
                retry_config = RetryConfig(**a2a_data['retry_config'])
                a2a_data['retry_config'] = retry_config
            enhanced_data['a2a_config'] = A2AConfig(**a2a_data)
        
        # Debug configuration
        if 'debug' in yaml_config:
            debug_data = yaml_config['debug']
            enhanced_data['debug_config'] = DebugConfig(**debug_data)
        
        # Other enhanced fields
        enhanced_fields = {
            'enable_circuit_breaker', 'enable_tool_registry', 'enable_agent_registry',
            'max_concurrent_tools', 'tool_execution_queue_size', 'validate_tool_configs',
            'strict_mode'
        }
        
        for field in enhanced_fields:
            if field in yaml_config:
                enhanced_data[field] = yaml_config[field]
        
        # Create enhanced config
        enhanced_data['base_config'] = base_config
        return cls(**enhanced_data)
    
    def to_base_run_config(self) -> RunConfig:
        """Extract the base ADK RunConfig for compatibility.
        
        Returns:
            RunConfig: The underlying ADK RunConfig
        """
        return self.base_config
    
    def get_tool_timeout(self, tool_name: str, tool_type: str = "function") -> float:
        """Get timeout for a specific tool.
        
        Args:
            tool_name: Name of the tool
            tool_type: Type of tool (mcp, openapi, function)
            
        Returns:
            float: Timeout in seconds
        """
        return self.tool_timeouts.get_timeout_for_tool(tool_name, tool_type)
    
    def get_retry_config(self, operation_type: str = "default") -> RetryConfig:
        """Get retry configuration for an operation type.
        
        Args:
            operation_type: Type of operation (default, mcp_tools, openapi_tools, etc.)
            
        Returns:
            RetryConfig: Retry configuration
        """
        return self.retry_policies.get(operation_type, self.retry_policies['default'])
    
    def merge_with_yaml(self, yaml_config: Dict[str, Any]) -> 'EnhancedRunConfig':
        """Merge this configuration with additional YAML configuration.
        
        Args:
            yaml_config: Additional YAML configuration to merge
            
        Returns:
            EnhancedRunConfig: New merged configuration
        """
        # Convert current config to dict
        current_dict = self.model_dump()
        
        # Merge base_config fields
        if any(k in yaml_config for k in ['streaming_mode', 'max_llm_calls', 'support_cfc']):
            base_dict = current_dict['base_config']
            base_dict.update({k: v for k, v in yaml_config.items() 
                            if k in base_dict})
            yaml_config['base_config'] = base_dict
        
        # Deep merge the configurations
        merged_dict = self._deep_merge(current_dict, yaml_config)
        
        return self.from_yaml_dict(merged_dict)
    
    @staticmethod
    def _deep_merge(base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = EnhancedRunConfig._deep_merge(result[key], value)
            else:
                result[key] = value
        return result