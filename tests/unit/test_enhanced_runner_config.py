"""Unit tests for enhanced runner configuration."""

import pytest
from dataclasses import asdict
from unittest.mock import Mock

from google.adk.agents.run_config import RunConfig, StreamingMode

from google_adk_extras.runners.config import (
    A2AConfig,
    CircuitBreakerConfig,
    DebugConfig,
    EnhancedRunConfig,
    RetryConfig,
    RetryStrategy,
    ToolTimeoutConfig,
)


class TestRetryConfig:
    """Test cases for RetryConfig."""
    
    def test_default_values(self):
        """Test default retry configuration values."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_multiplier == 2.0
        assert config.jitter is True
    
    def test_custom_values(self):
        """Test custom retry configuration values."""
        config = RetryConfig(
            max_attempts=5,
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=2.0,
            max_delay=30.0,
            backoff_multiplier=1.5,
            jitter=False
        )
        
        assert config.max_attempts == 5
        assert config.strategy == RetryStrategy.FIXED_DELAY
        assert config.base_delay == 2.0
        assert config.max_delay == 30.0
        assert config.backoff_multiplier == 1.5
        assert config.jitter is False


class TestCircuitBreakerConfig:
    """Test cases for CircuitBreakerConfig."""
    
    def test_default_values(self):
        """Test default circuit breaker configuration values."""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.success_threshold == 3
        assert config.timeout == 30.0
    
    def test_custom_values(self):
        """Test custom circuit breaker configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            success_threshold=2,
            timeout=15.0
        )
        
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.success_threshold == 2
        assert config.timeout == 15.0


class TestToolTimeoutConfig:
    """Test cases for ToolTimeoutConfig."""
    
    def test_default_values(self):
        """Test default tool timeout configuration values."""
        config = ToolTimeoutConfig()
        
        assert config.mcp_tools == 30.0
        assert config.openapi_tools == 60.0
        assert config.function_tools == 10.0
        assert config.mcp_connection_timeout == 10.0
        assert config.openapi_connection_timeout == 15.0
        assert config.tool_specific_timeouts == {}
    
    def test_get_timeout_for_tool_default(self):
        """Test getting timeout for tool with default values."""
        config = ToolTimeoutConfig()
        
        # Test type-based defaults
        assert config.get_timeout_for_tool("test_tool", "mcp") == 30.0
        assert config.get_timeout_for_tool("test_tool", "openapi") == 60.0
        assert config.get_timeout_for_tool("test_tool", "function") == 10.0
        assert config.get_timeout_for_tool("test_tool", "unknown") == 10.0
        assert config.get_timeout_for_tool("test_tool") == 10.0  # default type
    
    def test_get_timeout_for_tool_specific_override(self):
        """Test getting timeout with tool-specific override."""
        config = ToolTimeoutConfig(
            tool_specific_timeouts={"special_tool": 45.0}
        )
        
        # Should use specific override
        assert config.get_timeout_for_tool("special_tool", "mcp") == 45.0
        assert config.get_timeout_for_tool("special_tool", "function") == 45.0
        
        # Should use type default for other tools
        assert config.get_timeout_for_tool("other_tool", "mcp") == 30.0


class TestA2AConfig:
    """Test cases for A2AConfig."""
    
    def test_default_values(self):
        """Test default A2A configuration values."""
        config = A2AConfig()
        
        assert config.timeout == 30.0
        assert isinstance(config.retry_config, RetryConfig)
        assert isinstance(config.circuit_breaker, CircuitBreakerConfig)
        assert config.connection_pool_size == 10


class TestDebugConfig:
    """Test cases for DebugConfig."""
    
    def test_default_values(self):
        """Test default debug configuration values."""
        config = DebugConfig()
        
        assert config.enabled is False
        assert config.trace_agent_flow is False
        assert config.trace_tool_execution is False
        assert config.performance_profiling is False
        assert config.log_level == "INFO"
        assert config.capture_exceptions is True
    
    def test_custom_values(self):
        """Test custom debug configuration values."""
        config = DebugConfig(
            enabled=True,
            trace_agent_flow=True,
            trace_tool_execution=True,
            performance_profiling=True,
            log_level="DEBUG",
            capture_exceptions=False
        )
        
        assert config.enabled is True
        assert config.trace_agent_flow is True
        assert config.trace_tool_execution is True
        assert config.performance_profiling is True
        assert config.log_level == "DEBUG"
        assert config.capture_exceptions is False


class TestEnhancedRunConfig:
    """Test cases for EnhancedRunConfig."""
    
    def test_default_initialization(self):
        """Test default EnhancedRunConfig initialization."""
        config = EnhancedRunConfig()
        
        # Check base config
        assert isinstance(config.base_config, RunConfig)
        
        # Check enhanced fields
        assert isinstance(config.tool_timeouts, ToolTimeoutConfig)
        assert isinstance(config.retry_policies, dict)
        assert 'default' in config.retry_policies
        assert 'mcp_tools' in config.retry_policies
        assert 'openapi_tools' in config.retry_policies
        
        assert isinstance(config.a2a_config, A2AConfig)
        assert isinstance(config.debug_config, DebugConfig)
        
        # Check defaults
        assert config.enable_circuit_breaker is False
        assert config.enable_tool_registry is True
        assert config.enable_agent_registry is True
        assert config.max_concurrent_tools == 5
        assert config.tool_execution_queue_size == 100
        assert config.validate_tool_configs is True
        assert config.strict_mode is False
    
    def test_custom_initialization(self):
        """Test EnhancedRunConfig with custom values."""
        base_config = RunConfig(max_llm_calls=100)
        tool_timeouts = ToolTimeoutConfig(mcp_tools=45.0)
        debug_config = DebugConfig(enabled=True)
        
        config = EnhancedRunConfig(
            base_config=base_config,
            tool_timeouts=tool_timeouts,
            debug_config=debug_config,
            enable_circuit_breaker=True,
            max_concurrent_tools=10
        )
        
        assert config.base_config is base_config
        assert config.tool_timeouts is tool_timeouts
        assert config.debug_config is debug_config
        assert config.enable_circuit_breaker is True
        assert config.max_concurrent_tools == 10
    
    def test_from_yaml_dict_basic(self):
        """Test creating config from basic YAML dict."""
        yaml_config = {
            'max_llm_calls': 200,
            'streaming_mode': 'NONE',
            'tool_timeouts': {
                'mcp_tools': 45.0,
                'function_tools': 5.0
            },
            'enable_circuit_breaker': True,
            'debug': {
                'enabled': True,
                'trace_agent_flow': True
            }
        }
        
        config = EnhancedRunConfig.from_yaml_dict(yaml_config)
        
        # Check base config extraction
        assert config.base_config.max_llm_calls == 200
        assert config.base_config.streaming_mode == StreamingMode.NONE
        
        # Check enhanced config
        assert config.tool_timeouts.mcp_tools == 45.0
        assert config.tool_timeouts.function_tools == 5.0
        assert config.enable_circuit_breaker is True
        assert config.debug_config.enabled is True
        assert config.debug_config.trace_agent_flow is True
    
    def test_from_yaml_dict_retry_policies(self):
        """Test creating config with retry policies from YAML."""
        yaml_config = {
            'retry_policies': {
                'default': {
                    'max_attempts': 5,
                    'strategy': 'fixed_delay',
                    'base_delay': 2.0
                },
                'custom': {
                    'max_attempts': 2,
                    'strategy': 'immediate'
                }
            }
        }
        
        config = EnhancedRunConfig.from_yaml_dict(yaml_config)
        
        # Check retry policies
        assert 'default' in config.retry_policies
        assert 'custom' in config.retry_policies
        
        default_policy = config.retry_policies['default']
        assert default_policy.max_attempts == 5
        assert default_policy.strategy == RetryStrategy.FIXED_DELAY
        assert default_policy.base_delay == 2.0
        
        custom_policy = config.retry_policies['custom']
        assert custom_policy.max_attempts == 2
        assert custom_policy.strategy == RetryStrategy.IMMEDIATE
    
    def test_from_yaml_dict_a2a_config(self):
        """Test creating config with A2A configuration from YAML."""
        yaml_config = {
            'a2a_config': {
                'timeout': 45.0,
                'connection_pool_size': 20,
                'retry_config': {
                    'max_attempts': 4,
                    'base_delay': 1.5
                }
            }
        }
        
        config = EnhancedRunConfig.from_yaml_dict(yaml_config)
        
        # Check A2A config
        assert config.a2a_config.timeout == 45.0
        assert config.a2a_config.connection_pool_size == 20
        assert config.a2a_config.retry_config.max_attempts == 4
        assert config.a2a_config.retry_config.base_delay == 1.5
    
    def test_to_base_run_config(self):
        """Test extracting base RunConfig."""
        base_config = RunConfig(max_llm_calls=150)
        enhanced_config = EnhancedRunConfig(base_config=base_config)
        
        extracted = enhanced_config.to_base_run_config()
        
        assert extracted is base_config
        assert extracted.max_llm_calls == 150
    
    def test_get_tool_timeout(self):
        """Test getting tool timeout."""
        config = EnhancedRunConfig(
            tool_timeouts=ToolTimeoutConfig(
                mcp_tools=45.0,
                tool_specific_timeouts={'special_tool': 90.0}
            )
        )
        
        assert config.get_tool_timeout('test_tool', 'mcp') == 45.0
        assert config.get_tool_timeout('special_tool', 'mcp') == 90.0
        assert config.get_tool_timeout('other_tool', 'function') == 10.0  # default
    
    def test_get_retry_config(self):
        """Test getting retry configuration."""
        custom_retry = RetryConfig(max_attempts=5)
        config = EnhancedRunConfig(
            retry_policies={'custom': custom_retry}
        )
        
        # Should return specific config
        assert config.get_retry_config('custom') is custom_retry
        
        # Should return default for unknown type
        default_config = config.get_retry_config('unknown')
        assert isinstance(default_config, RetryConfig)
        assert default_config.max_attempts == 3  # Default RetryConfig value
    
    def test_merge_with_yaml(self):
        """Test merging configuration with additional YAML."""
        original_config = EnhancedRunConfig(
            tool_timeouts=ToolTimeoutConfig(mcp_tools=30.0),
            enable_circuit_breaker=False
        )
        
        additional_yaml = {
            'tool_timeouts': {
                'mcp_tools': 60.0,  # Should override
                'openapi_tools': 90.0  # Should be added
            },
            'enable_circuit_breaker': True,  # Should override
            'max_concurrent_tools': 15  # Should be added
        }
        
        merged_config = original_config.merge_with_yaml(additional_yaml)
        
        # Check merged values
        assert merged_config.tool_timeouts.mcp_tools == 60.0
        assert merged_config.tool_timeouts.openapi_tools == 90.0
        assert merged_config.enable_circuit_breaker is True
        assert merged_config.max_concurrent_tools == 15
    
    def test_deep_merge_nested_dicts(self):
        """Test deep merge of nested dictionaries."""
        base = {
            'level1': {
                'level2': {
                    'existing': 'value1',
                    'override_me': 'old'
                }
            },
            'top_level': 'original'
        }
        
        update = {
            'level1': {
                'level2': {
                    'override_me': 'new',
                    'added': 'value2'
                }
            },
            'new_top': 'added'
        }
        
        result = EnhancedRunConfig._deep_merge(base, update)
        
        assert result['level1']['level2']['existing'] == 'value1'
        assert result['level1']['level2']['override_me'] == 'new'
        assert result['level1']['level2']['added'] == 'value2'
        assert result['top_level'] == 'original'
        assert result['new_top'] == 'added'
    
    def test_yaml_streaming_mode_enum_conversion(self):
        """Test streaming mode enum conversion from YAML."""
        yaml_configs = [
            ({'streaming_mode': 'NONE'}, StreamingMode.NONE),
            ({'streaming_mode': 'SSE'}, StreamingMode.SSE),
            ({'streaming_mode': 'BIDI'}, StreamingMode.BIDI),
        ]
        
        for yaml_config, expected_mode in yaml_configs:
            config = EnhancedRunConfig.from_yaml_dict(yaml_config)
            assert config.base_config.streaming_mode == expected_mode
    
    def test_empty_yaml_dict(self):
        """Test creating config from empty YAML dict."""
        config = EnhancedRunConfig.from_yaml_dict({})
        
        # Should have all defaults
        assert isinstance(config.base_config, RunConfig)
        assert isinstance(config.tool_timeouts, ToolTimeoutConfig)
        assert isinstance(config.debug_config, DebugConfig)
        assert config.enable_circuit_breaker is False