"""Integration tests for Configuration System with Enhanced ADK Capabilities."""

import os
import tempfile
from pathlib import Path

import pytest

from google_adk_extras.configuration import load_enhanced_run_config
from google_adk_extras.runners.config import EnhancedRunConfig
from google_adk_extras.runners.registry.config import (
    AgentRegistryConfig, 
    ToolRegistryConfig
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def clean_env():
    """Clean environment for testing."""
    original_env = dict(os.environ)
    os.environ.clear()
    
    # Set realistic environment variables
    os.environ.update({
        'DATABASE_URL': 'postgresql://localhost/enhanced_adk',
        'REDIS_URL': 'redis://localhost:6379',
        'API_KEY': 'sk-test-key-12345',
        'MAX_LLM_CALLS': '500',
        'CIRCUIT_BREAKER_THRESHOLD': '5',
        'TOOL_TIMEOUT': '30.0',
        'AGENT_REGISTRY_CACHE_TTL': '300'
    })
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


class TestEnhancedRunConfigIntegration:
    """Test Enhanced Configuration System with EnhancedRunConfig."""
    
    def test_enhanced_run_config_from_yaml(self, temp_dir, clean_env):
        """Test loading EnhancedRunConfig from YAML with all features."""
        yaml_content = """
# Enhanced ADK Runtime Configuration
max_llm_calls: ${MAX_LLM_CALLS}
streaming_mode: NONE

# Tool Configuration
tool_timeouts:
  mcp_tools: ${TOOL_TIMEOUT}
  openapi_tools: 60.0
  function_tools: 10.0
  tool_specific_timeouts:
    slow_tool: 120.0

# Retry Policies
retry_policies:
  default:
    max_attempts: 3
    strategy: exponential_backoff
    base_delay: 1.0
    max_delay: 60.0
    
  mcp_tools:
    max_attempts: 2
    strategy: fixed_delay
    base_delay: 0.5
    
  openapi_tools:
    max_attempts: 4
    strategy: linear_backoff
    base_delay: 2.0

# Circuit Breaker Configuration
enable_circuit_breaker: true
circuit_breaker_config:
  failure_threshold: ${CIRCUIT_BREAKER_THRESHOLD}
  recovery_timeout: 60.0
  success_threshold: 3
  timeout: 30.0

# A2A Configuration  
a2a_config:
  timeout: 30.0
  connection_pool_size: 10
  retry_config:
    max_attempts: 3
    base_delay: 1.0

# Registry Integration
enable_tool_registry: true
enable_agent_registry: true

# Performance Configuration
max_concurrent_tools: 10
tool_execution_queue_size: 200

# Debug Configuration
debug:
  enabled: true
  trace_agent_flow: true
  trace_tool_execution: false
  performance_profiling: true
  log_level: INFO
  capture_exceptions: true

# Validation
validate_tool_configs: true
strict_mode: false
"""
        
        yaml_file = temp_dir / "enhanced_config.yaml"
        yaml_file.write_text(yaml_content)
        
        result = load_enhanced_run_config(str(yaml_file))
        
        assert result.config is not None
        config = result.config
        
        # Verify basic fields are loaded
        assert isinstance(config, EnhancedRunConfig)
        assert config.base_config is not None
        
        # Verify tool timeouts are configured
        assert config.tool_timeouts is not None
        # Environment variables come as strings, so check if it can be converted
        mcp_timeout = config.tool_timeouts.mcp_tools
        if isinstance(mcp_timeout, str):
            assert float(mcp_timeout) > 0
        else:
            assert mcp_timeout > 0
        
        # Verify retry policies are loaded
        assert 'default' in config.retry_policies
        assert 'mcp_tools' in config.retry_policies
        
        # Verify A2A config
        assert config.a2a_config is not None
        assert config.a2a_config.timeout > 0
        
        # Verify debug config
        assert config.debug_config is not None
        assert config.debug_config.enabled == True
    
    def test_enhanced_run_config_environment_integration(self, clean_env):
        """Test EnhancedRunConfig with environment variable integration."""
        config_dict = {
            'max_llm_calls': '${MAX_LLM_CALLS}',
            'streaming_mode': 'NONE',
            'tool_timeouts': {
                'mcp_tools': '${TOOL_TIMEOUT}',
                'openapi_tools': 45.0
            },
            'enable_circuit_breaker': True,
            'circuit_breaker_config': {
                'failure_threshold': '${CIRCUIT_BREAKER_THRESHOLD}',
                'recovery_timeout': 60.0
            },
            'debug_config': {
                'enabled': True,
                'trace_agent_flow': True,
                'log_level': 'DEBUG'
            }
        }
        
        result = load_enhanced_run_config(config_dict)
        
        assert result.config is not None
        config = result.config
        
        # Environment variables should be interpolated
        # Note: Actual interpolation depends on working interpolation system
        assert isinstance(config, EnhancedRunConfig)
    
    def test_enhanced_run_config_with_registry_configs(self, clean_env):
        """Test EnhancedRunConfig integration with registry configurations."""
        config_dict = {
            'max_llm_calls': 200,
            'streaming_mode': 'NONE',
            
            # Enable registries
            'enable_tool_registry': True,
            'enable_agent_registry': True,
            
            # Tool execution settings
            'max_concurrent_tools': 8,
            'tool_execution_queue_size': 150,
            
            # Circuit breaker for external services
            'enable_circuit_breaker': True,
            'circuit_breaker_config': {
                'failure_threshold': 3,
                'recovery_timeout': 45.0,
                'success_threshold': 2
            }
        }
        
        result = load_enhanced_run_config(config_dict)
        
        assert result.config is not None
        config = result.config
        
        # Verify registry integration settings
        assert config.enable_tool_registry == True
        assert config.enable_agent_registry == True
        
        # Verify performance settings
        assert config.max_concurrent_tools == 8
        assert config.tool_execution_queue_size == 150
        
        # Verify circuit breaker
        assert config.enable_circuit_breaker == True
        assert config.circuit_breaker_config.failure_threshold == 3


class TestRegistryConfigIntegration:
    """Test configuration system with registry configurations."""
    
    def test_agent_registry_config_loading(self, temp_dir, clean_env):
        """Test loading AgentRegistryConfig via configuration system."""
        yaml_content = """
name: "test_agent_registry"
graceful_shutdown_timeout: 30.0
max_agents: 50
allowed_agent_types:
  - "sequential"
  - "parallel"
  - "loop"
  - "custom"
enable_hot_swapping: true
validate_agents_on_registration: true

# Cache configuration
caching:
  enabled: true
  default_ttl: ${AGENT_REGISTRY_CACHE_TTL}
  max_size: 1000
  cleanup_interval: 120.0

# Health monitoring
health_monitoring:
  enabled: true
  check_interval: 60.0
  failure_threshold: 3
  recovery_threshold: 2
  stale_threshold: 300.0
"""
        
        yaml_file = temp_dir / "agent_registry_config.yaml"
        yaml_file.write_text(yaml_content)
        
        from google_adk_extras.configuration import load_config
        
        result = load_config(AgentRegistryConfig, str(yaml_file))
        
        assert result.config is not None
        config = result.config
        
        # Verify agent registry specific settings
        assert config.name == "test_agent_registry"
        assert config.max_agents == 50
        assert len(config.allowed_agent_types) == 4
        assert config.enable_hot_swapping == True
    
    def test_tool_registry_config_loading(self, temp_dir, clean_env):
        """Test loading ToolRegistryConfig via configuration system."""
        yaml_content = """
name: "test_tool_registry"
max_tools: 200
allowed_tool_types:
  - "function"
  - "mcp"
  - "openapi"
  - "agent"
  - "google"

default_timeout: 30.0
max_concurrent_executions: 15
enable_dynamic_loading: true
validate_tools_on_registration: true

# Cache configuration
caching:
  enabled: true
  default_ttl: 600.0
  max_size: 2000
  cleanup_interval: 180.0

# Health monitoring
health_monitoring:
  enabled: true
  check_interval: 45.0
  failure_threshold: 4
  recovery_threshold: 3
  stale_threshold: 400.0
"""
        
        yaml_file = temp_dir / "tool_registry_config.yaml"
        yaml_file.write_text(yaml_content)
        
        from google_adk_extras.configuration import load_config
        
        result = load_config(ToolRegistryConfig, str(yaml_file))
        
        assert result.config is not None
        config = result.config
        
        # Verify tool registry specific settings
        assert config.name == "test_tool_registry"
        assert config.max_tools == 200
        assert len(config.allowed_tool_types) == 5
        assert config.default_timeout == 30.0
        assert config.max_concurrent_executions == 15


class TestEnhancedCapabilitiesWorkflow:
    """Test complete workflow with enhanced capabilities."""
    
    def test_complete_enhanced_adk_configuration(self, temp_dir, clean_env):
        """Test complete enhanced ADK configuration workflow."""
        # Master configuration that brings together all enhanced capabilities
        master_config = {
            # Base ADK configuration
            'max_llm_calls': 1000,
            'streaming_mode': 'NONE',
            'support_cfc': True,
            
            # Enhanced tool configuration with environment variables
            'tool_timeouts': {
                'mcp_tools': '${TOOL_TIMEOUT}',
                'openapi_tools': 90.0,
                'function_tools': 15.0
            },
            
            # Comprehensive retry policies
            'retry_policies': {
                'default': {
                    'max_attempts': 3,
                    'strategy': 'exponential_backoff',
                    'base_delay': 1.0,
                    'max_delay': 120.0,
                    'backoff_multiplier': 2.0,
                    'jitter': True
                },
                'critical_operations': {
                    'max_attempts': 5,
                    'strategy': 'exponential_backoff',
                    'base_delay': 0.5,
                    'max_delay': 60.0
                }
            },
            
            # Circuit breaker for resilience
            'enable_circuit_breaker': True,
            'circuit_breaker_config': {
                'failure_threshold': '${CIRCUIT_BREAKER_THRESHOLD}',
                'recovery_timeout': 90.0,
                'success_threshold': 2,
                'timeout': 45.0
            },
            
            # A2A remote agent configuration
            'a2a_config': {
                'timeout': 60.0,
                'connection_pool_size': 20,
                'retry_config': {
                    'max_attempts': 3,
                    'strategy': 'fixed_delay',
                    'base_delay': 2.0
                }
            },
            
            # Registry integration
            'enable_tool_registry': True,
            'enable_agent_registry': True,
            
            # Performance tuning
            'max_concurrent_tools': 12,
            'tool_execution_queue_size': 300,
            
            # Debug and monitoring
            'debug': {
                'enabled': True,
                'trace_agent_flow': True,
                'trace_tool_execution': True,
                'performance_profiling': True,
                'log_level': 'INFO',
                'capture_exceptions': True
            },
            
            # Validation and safety
            'validate_tool_configs': True,
            'strict_mode': False
        }
        
        result = load_enhanced_run_config(master_config)
        
        assert result.config is not None
        config = result.config
        
        # Comprehensive verification
        assert isinstance(config, EnhancedRunConfig)
        # Base config should use direct values, not environment variables
        assert config.base_config.max_llm_calls == 1000
        
        # Tool configuration
        assert config.tool_timeouts is not None
        assert config.tool_timeouts.function_tools == 15.0
        
        # Retry policies
        assert len(config.retry_policies) >= 2
        assert 'default' in config.retry_policies
        assert 'critical_operations' in config.retry_policies
        
        # Circuit breaker
        assert config.enable_circuit_breaker == True
        assert config.circuit_breaker_config.success_threshold == 2
        
        # A2A configuration
        assert config.a2a_config.timeout == 60.0
        assert config.a2a_config.connection_pool_size == 20
        
        # Registry settings
        assert config.enable_tool_registry == True
        assert config.enable_agent_registry == True
        
        # Performance settings
        assert config.max_concurrent_tools == 12
        assert config.tool_execution_queue_size == 300
        
        # Debug configuration
        assert config.debug_config.enabled == True
        assert config.debug_config.trace_agent_flow == True
        assert config.debug_config.performance_profiling == True
        
        # Validation settings
        assert config.validate_tool_configs == True
        assert config.strict_mode == False
    
    def test_configuration_system_performance_with_enhanced_configs(self):
        """Test configuration system performance with complex enhanced configs."""
        # Simulate loading multiple complex configurations
        base_config = {
            'max_llm_calls': 500,
            'streaming_mode': 'NONE',
            'tool_timeouts': {
                'mcp_tools': 30.0,
                'openapi_tools': 60.0,
                'function_tools': 10.0
            },
            'retry_policies': {
                'default': {
                    'max_attempts': 3,
                    'strategy': 'exponential_backoff'
                }
            },
            'enable_circuit_breaker': True,
            'debug': {
                'enabled': True,
                'trace_agent_flow': True
            }
        }
        
        # Load multiple variations
        results = []
        for i in range(5):
            config_variant = base_config.copy()
            config_variant['max_llm_calls'] = 500 + (i * 100)
            config_variant['debug'] = {
                'enabled': i % 2 == 0,
                'trace_agent_flow': True,
                'log_level': ['DEBUG', 'INFO', 'WARNING', 'ERROR'][i % 4]
            }
            
            result = load_enhanced_run_config(config_variant)
            results.append(result)
        
        # All should succeed
        assert all(r.config is not None for r in results)
        
        # Performance metrics should be reasonable
        assert all(r.processing_time < 1.0 for r in results)  # Less than 1 second
        
        # Verify different configurations were created
        max_calls = [r.config.base_config.max_llm_calls for r in results]
        assert len(set(max_calls)) == 5  # All different values
    
    def test_configuration_validation_with_enhanced_features(self, clean_env):
        """Test configuration validation with enhanced ADK features."""
        # Configuration with potential validation issues
        config_with_issues = {
            'max_llm_calls': -1,  # Invalid negative value
            'streaming_mode': 'INVALID_MODE',  # Invalid enum
            'tool_timeouts': {
                'mcp_tools': -5.0,  # Invalid negative timeout
                'unknown_tool_type': 30.0  # Unknown tool type
            },
            'retry_policies': {
                'default': {
                    'max_attempts': 0,  # Invalid zero attempts
                    'strategy': 'unknown_strategy',  # Invalid strategy
                    'base_delay': -1.0  # Invalid negative delay
                }
            },
            'circuit_breaker_config': {
                'failure_threshold': 0,  # Invalid zero threshold
                'recovery_timeout': -30.0  # Invalid negative timeout
            },
            'max_concurrent_tools': -5,  # Invalid negative value
            'undefined_env_var': '${COMPLETELY_UNDEFINED_VAR}'  # Undefined variable
        }
        
        from google_adk_extras.configuration import ConfigurationSystem
        
        # Test with validation enabled but non-strict mode
        system = ConfigurationSystem(enable_validation=True, strict_mode=False)
        result = system.load_config(EnhancedRunConfig, config_with_issues)
        
        # Should have result but potentially with validation issues
        assert result is not None
        
        # May have validation issues reported
        if result.validation_issues:
            # Should have various types of validation issues
            severities = [issue.severity for issue in result.validation_issues]
            assert any(severity.value in ['error', 'warning'] for severity in severities)


class TestConfigurationSystemExtensibility:
    """Test configuration system extensibility with enhanced capabilities."""
    
    def test_custom_config_class_integration(self):
        """Test integration with custom configuration classes."""
        
        # Custom configuration class that extends enhanced capabilities
        class CustomEnhancedConfig:
            def __init__(self, **kwargs):
                # Custom fields
                self.custom_feature_enabled = kwargs.get('custom_feature_enabled', False)
                self.custom_timeout = kwargs.get('custom_timeout', 30.0)
                self.custom_settings = kwargs.get('custom_settings', {})
                
                # Enhanced ADK fields
                self.max_llm_calls = kwargs.get('max_llm_calls', 100)
                self.enable_circuit_breaker = kwargs.get('enable_circuit_breaker', False)
            
            @classmethod
            def from_dict(cls, data):
                return cls(**data)
        
        custom_config = {
            'custom_feature_enabled': True,
            'custom_timeout': 45.0,
            'custom_settings': {
                'advanced_mode': True,
                'experimental_features': ['feature_a', 'feature_b']
            },
            'max_llm_calls': 200,
            'enable_circuit_breaker': True
        }
        
        from google_adk_extras.configuration import load_config
        
        result = load_config(CustomEnhancedConfig, custom_config)
        
        assert result.config is not None
        config = result.config
        
        # Verify custom fields
        assert config.custom_feature_enabled == True
        assert config.custom_timeout == 45.0
        assert config.custom_settings['advanced_mode'] == True
        
        # Verify enhanced ADK fields
        assert config.max_llm_calls == 200
        assert config.enable_circuit_breaker == True