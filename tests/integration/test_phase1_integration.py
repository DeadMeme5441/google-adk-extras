"""Integration tests for Phase 1: Enhanced Runner Foundation.

These tests verify that all Phase 1 components work together correctly
in realistic scenarios, testing the integration between:
- EnhancedRunner and EnhancedRunConfig
- YAML configuration loading and parsing
- Tool execution strategies and strategy manager
- Error handling across component boundaries
- Performance metrics collection
"""

import asyncio
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from typing import Any, AsyncGenerator, Dict, List

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.events.event import Event
from google.adk.sessions.base_session_service import BaseSessionService
from google.genai import types

from google_adk_extras.runners.config import (
    CircuitBreakerConfig,
    EnhancedRunConfig,
    RetryConfig,
    RetryStrategy,
    ToolTimeoutConfig,
)
from google_adk_extras.runners.enhanced_runner import EnhancedRunner
from google_adk_extras.runners.errors import (
    ConfigurationError,
    ToolExecutionError,
    YamlSystemContext,
    YamlSystemError,
)
from google_adk_extras.runners.strategies import (
    DefaultToolExecutionStrategy,
    McpToolExecutionStrategy,
    OpenApiToolExecutionStrategy,
    ToolExecutionStrategyManager,
)


class MockEvent:
    """Mock event for testing."""
    
    def __init__(self, author: str = None, content: str = None):
        self.author = author
        self.content = content


class MockAgent(BaseAgent):
    """Mock agent for integration testing."""
    
    def __init__(self, name: str = "test_agent"):
        # Properly initialize Pydantic BaseModel with required fields
        super().__init__(name=name)
        self._invocation_count = 0
    
    async def run(self, context, **kwargs):
        """Mock run method."""
        self._invocation_count += 1
        yield MockEvent(author=self.name, content=f"Response {self._invocation_count}")


class MockSessionService(BaseSessionService):
    """Mock session service for integration testing."""
    
    def __init__(self):
        self._sessions = {}
    
    async def create_session(self, user_id: str, session_id: str, **kwargs):
        """Mock create session."""
        self._sessions[session_id] = {"user_id": user_id}
        return {"session_id": session_id}
    
    async def get_session(self, session_id: str, **kwargs):
        """Mock get session."""
        return self._sessions.get(session_id)
    
    async def delete_session(self, session_id: str, **kwargs):
        """Mock delete session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    async def list_sessions(self, user_id: str = None, **kwargs):
        """Mock list sessions."""
        if user_id:
            return [s for s in self._sessions.values() if s.get("user_id") == user_id]
        return list(self._sessions.values())


class TestEnhancedRunConfigYamlIntegration:
    """Test EnhancedRunConfig YAML integration end-to-end."""
    
    def create_yaml_config_file(self, config_dict: Dict[str, Any]) -> Path:
        """Create a temporary YAML config file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(config_dict, temp_file)
        temp_file.close()
        return Path(temp_file.name)
    
    def test_complete_yaml_config_loading(self):
        """Test complete YAML configuration loading and parsing."""
        yaml_config = {
            'streaming_mode': 'NONE',
            'max_llm_calls': 150,
            'tool_timeouts': {
                'mcp_tools': 45.0,
                'openapi_tools': 90.0,
                'function_tools': 15.0,
                'mcp_connection_timeout': 12.0,
                'tool_specific_timeouts': {
                    'slow_mcp_tool': 120.0,
                    'fast_function': 5.0
                }
            },
            'retry_policies': {
                'default': {
                    'max_attempts': 4,
                    'strategy': 'exponential_backoff',
                    'base_delay': 1.5,
                    'max_delay': 30.0,
                    'jitter': True
                },
                'mcp_tools': {
                    'max_attempts': 2,
                    'strategy': 'fixed_delay',
                    'base_delay': 0.8
                },
                'critical_operations': {
                    'max_attempts': 6,
                    'strategy': 'linear_backoff',
                    'base_delay': 2.0
                }
            },
            'a2a_config': {
                'timeout': 60.0,
                'connection_pool_size': 15,
                'retry_config': {
                    'max_attempts': 3,
                    'strategy': 'exponential_backoff',
                    'base_delay': 2.0
                }
            },
            'debug': {
                'enabled': True,
                'trace_agent_flow': True,
                'trace_tool_execution': False,
                'performance_profiling': True,
                'log_level': 'DEBUG',
                'capture_exceptions': True
            },
            'enable_circuit_breaker': True,
            'enable_tool_registry': True,
            'enable_agent_registry': False,
            'max_concurrent_tools': 12,
            'tool_execution_queue_size': 200,
            'validate_tool_configs': True,
            'strict_mode': True
        }
        
        # Test loading from dict
        config = EnhancedRunConfig.from_yaml_dict(yaml_config)
        
        # Verify base config
        assert config.base_config.streaming_mode == StreamingMode.NONE
        assert config.base_config.max_llm_calls == 150
        
        # Verify tool timeouts
        assert config.tool_timeouts.mcp_tools == 45.0
        assert config.tool_timeouts.openapi_tools == 90.0
        assert config.tool_timeouts.function_tools == 15.0
        assert config.tool_timeouts.mcp_connection_timeout == 12.0
        assert config.tool_timeouts.tool_specific_timeouts['slow_mcp_tool'] == 120.0
        assert config.tool_timeouts.tool_specific_timeouts['fast_function'] == 5.0
        
        # Verify retry policies
        assert len(config.retry_policies) == 3
        
        default_retry = config.retry_policies['default']
        assert default_retry.max_attempts == 4
        assert default_retry.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert default_retry.base_delay == 1.5
        assert default_retry.max_delay == 30.0
        assert default_retry.jitter is True
        
        mcp_retry = config.retry_policies['mcp_tools']
        assert mcp_retry.max_attempts == 2
        assert mcp_retry.strategy == RetryStrategy.FIXED_DELAY
        assert mcp_retry.base_delay == 0.8
        
        critical_retry = config.retry_policies['critical_operations']
        assert critical_retry.max_attempts == 6
        assert critical_retry.strategy == RetryStrategy.LINEAR_BACKOFF
        assert critical_retry.base_delay == 2.0
        
        # Verify A2A config
        assert config.a2a_config.timeout == 60.0
        assert config.a2a_config.connection_pool_size == 15
        assert config.a2a_config.retry_config.max_attempts == 3
        assert config.a2a_config.retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        
        # Verify debug config
        assert config.debug_config.enabled is True
        assert config.debug_config.trace_agent_flow is True
        assert config.debug_config.trace_tool_execution is False
        assert config.debug_config.performance_profiling is True
        assert config.debug_config.log_level == 'DEBUG'
        assert config.debug_config.capture_exceptions is True
        
        # Verify other settings
        assert config.enable_circuit_breaker is True
        assert config.enable_tool_registry is True
        assert config.enable_agent_registry is False
        assert config.max_concurrent_tools == 12
        assert config.tool_execution_queue_size == 200
        assert config.validate_tool_configs is True
        assert config.strict_mode is True
    
    def test_yaml_config_merging_integration(self):
        """Test configuration merging with multiple YAML sources."""
        # Base configuration
        base_yaml = {
            'max_llm_calls': 100,
            'tool_timeouts': {
                'mcp_tools': 30.0,
                'function_tools': 10.0
            },
            'debug': {
                'enabled': False,
                'log_level': 'INFO'
            }
        }
        
        # Override configuration
        override_yaml = {
            'max_llm_calls': 200,  # Override
            'tool_timeouts': {
                'mcp_tools': 45.0,  # Override
                'openapi_tools': 60.0  # Add new
            },
            'debug': {
                'enabled': True,  # Override
                'trace_agent_flow': True  # Add new
            },
            'enable_circuit_breaker': True  # Add new top-level
        }
        
        # Create base config and merge
        base_config = EnhancedRunConfig.from_yaml_dict(base_yaml)
        merged_config = base_config.merge_with_yaml(override_yaml)
        
        # Verify merging
        assert merged_config.base_config.max_llm_calls == 200  # Overridden
        
        # Tool timeouts should be merged
        assert merged_config.tool_timeouts.mcp_tools == 45.0  # Overridden
        assert merged_config.tool_timeouts.function_tools == 10.0  # Preserved
        assert merged_config.tool_timeouts.openapi_tools == 60.0  # Added
        
        # Debug config should be merged
        assert merged_config.debug_config.enabled is True  # Overridden
        assert merged_config.debug_config.log_level == 'INFO'  # Preserved
        assert merged_config.debug_config.trace_agent_flow is True  # Added
        
        # New top-level field should be added
        assert merged_config.enable_circuit_breaker is True


class TestEnhancedRunnerIntegration:
    """Test complete EnhancedRunner integration scenarios."""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        agent = MockAgent("integration_test_agent")
        session_service = MockSessionService()
        return agent, session_service
    
    def test_enhanced_runner_initialization_integration(self, mock_services):
        """Test complete EnhancedRunner initialization with all components."""
        agent, session_service = mock_services
        
        # Create comprehensive configuration
        yaml_config = {
            'streaming_mode': 'NONE',
            'max_llm_calls': 100,
            'tool_timeouts': {
                'mcp_tools': 30.0,
                'openapi_tools': 60.0,
                'function_tools': 15.0
            },
            'retry_policies': {
                'default': {'max_attempts': 3, 'strategy': 'exponential_backoff'},
                'mcp_tools': {'max_attempts': 2, 'strategy': 'immediate'}
            },
            'debug': {'enabled': True, 'trace_agent_flow': True},
            'enable_circuit_breaker': True,
            'max_concurrent_tools': 8
        }
        
        enhanced_config = EnhancedRunConfig.from_yaml_dict(yaml_config)
        yaml_context = YamlSystemContext(
            system_name="integration-system",
            config_path="/test/config.yaml"
        )
        
        # Initialize runner
        runner = EnhancedRunner(
            app_name="integration-test-app",
            agent=agent,
            session_service=session_service,
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Verify complete initialization
        assert runner.app_name == "integration-test-app"
        assert runner.agent is agent
        assert runner.enhanced_config is enhanced_config
        assert runner.yaml_context is yaml_context
        
        # Verify strategy manager was created with config
        strategy_manager = runner.tool_strategy_manager
        assert 'mcp' in strategy_manager.strategies
        assert 'openapi' in strategy_manager.strategies
        assert 'function' in strategy_manager.strategies
        
        # Verify strategies use enhanced config values
        mcp_strategy = strategy_manager.strategies['mcp']
        assert mcp_strategy.timeout == 30.0  # From config
        
        openapi_strategy = strategy_manager.strategies['openapi']
        assert openapi_strategy.timeout == 60.0  # From config
        
        # Verify performance metrics initialized
        metrics = runner.get_performance_metrics()
        assert metrics['total_invocations'] == 0
        assert metrics['error_count'] == 0
    
    @pytest.mark.asyncio
    async def test_enhanced_runner_execution_flow_integration(self, mock_services):
        """Test complete execution flow with all components working together."""
        agent, session_service = mock_services
        
        # Setup enhanced configuration
        enhanced_config = EnhancedRunConfig(
            base_config=RunConfig(max_llm_calls=50),
            debug_config={'enabled': True, 'trace_agent_flow': True}
        )
        
        yaml_context = YamlSystemContext(
            system_name="execution-test",
            config_path="/test/execution.yaml"
        )
        
        runner = EnhancedRunner(
            app_name="execution-test-app",
            agent=agent,
            session_service=session_service,
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Mock the parent Runner's run_async method
        mock_events = [
            MockEvent(author="execution_agent", content="Processing request"),
            MockEvent(author="execution_agent", content="Calling tool"),
            MockEvent(author="execution_agent", content="Response generated")
        ]
        
        with patch.object(runner.__class__.__bases__[0], 'run_async') as mock_parent_run:
            async def mock_event_generator():
                for event in mock_events:
                    yield event
            
            mock_parent_run.return_value = mock_event_generator()
            
            # Execute the complete flow
            collected_events = []
            async for event in runner.run_async(
                user_id="integration_user",
                session_id="integration_session",
                new_message=types.Content(parts=[types.Part(text="Integration test message")])
            ):
                collected_events.append(event)
        
        # Verify complete execution flow
        assert len(collected_events) == 3
        assert collected_events == mock_events
        
        # Verify performance metrics were updated
        metrics = runner.get_performance_metrics()
        assert metrics['total_invocations'] == 1
        assert metrics['avg_invocation_time'] > 0
        assert metrics['error_count'] == 0
        assert metrics['success_rate'] == 1.0
        
        # Verify parent runner was called with enhanced config
        mock_parent_run.assert_called_once()
        call_kwargs = mock_parent_run.call_args[1]
        assert call_kwargs['user_id'] == "integration_user"
        assert call_kwargs['session_id'] == "integration_session"
        assert isinstance(call_kwargs['run_config'], RunConfig)
    
    @pytest.mark.asyncio
    async def test_enhanced_runner_error_handling_integration(self, mock_services):
        """Test error handling integration across all components."""
        agent, session_service = mock_services
        
        runner = EnhancedRunner(
            app_name="error-test-app",
            agent=agent,
            session_service=session_service,
            yaml_context=YamlSystemContext(
                system_name="error-test-system",
                config_path="/test/error.yaml",
                current_agent="error_agent"
            )
        )
        
        # Mock parent runner to raise different types of errors
        test_cases = [
            RuntimeError("Generic runtime error"),
            ConnectionError("Connection failed"),
            ValueError("Invalid value provided")
        ]
        
        for original_error in test_cases:
            with patch.object(runner.__class__.__bases__[0], 'run_async') as mock_parent_run:
                mock_parent_run.side_effect = original_error
                
                # Should wrap in YamlSystemError with context
                with pytest.raises(YamlSystemError) as exc_info:
                    async for _ in runner.run_async(
                        user_id="error_user",
                        session_id="error_session",
                        new_message=types.Content(parts=[types.Part(text="Error test")])
                    ):
                        pass
                
                # Verify error wrapping
                yaml_error = exc_info.value
                assert "Enhanced runner execution failed" in str(yaml_error)
                assert yaml_error.original_error is original_error
                assert yaml_error.context.system_name == "error-test-system"
                assert yaml_error.context.current_agent == "error_agent"
                assert len(yaml_error.suggested_fixes) > 0
        
        # Verify error metrics
        metrics = runner.get_performance_metrics()
        assert metrics['error_count'] == len(test_cases)
        assert metrics['total_invocations'] == len(test_cases)
        assert metrics['success_rate'] == 0.0


class TestToolExecutionStrategyIntegration:
    """Test tool execution strategy integration scenarios."""
    
    def test_strategy_manager_complete_workflow(self):
        """Test strategy manager with complete configuration workflow."""
        # Create comprehensive enhanced config
        yaml_config = {
            'tool_timeouts': {
                'mcp_tools': 35.0,
                'openapi_tools': 75.0,
                'function_tools': 12.0,
                'mcp_connection_timeout': 8.0,
                'openapi_connection_timeout': 20.0,
                'tool_specific_timeouts': {
                    'slow_mcp_tool': 120.0,
                    'fast_api_call': 5.0
                }
            },
            'retry_policies': {
                'default': {
                    'max_attempts': 3,
                    'strategy': 'exponential_backoff',
                    'base_delay': 1.0
                },
                'mcp_tools': {
                    'max_attempts': 2,
                    'strategy': 'immediate'
                },
                'openapi_tools': {
                    'max_attempts': 4,
                    'strategy': 'fixed_delay',
                    'base_delay': 2.0
                }
            }
        }
        
        enhanced_config = EnhancedRunConfig.from_yaml_dict(yaml_config)
        
        # Create runner with this configuration
        agent = MockAgent()
        session_service = MockSessionService()
        
        runner = EnhancedRunner(
            app_name="strategy-integration-app",
            agent=agent,
            session_service=session_service,
            enhanced_config=enhanced_config
        )
        
        strategy_manager = runner.tool_strategy_manager
        
        # Verify strategies were configured correctly
        mcp_strategy = strategy_manager.strategies['mcp']
        assert isinstance(mcp_strategy, McpToolExecutionStrategy)
        assert mcp_strategy.timeout == 35.0
        assert mcp_strategy.connection_timeout == 8.0
        assert mcp_strategy.retry_config.max_attempts == 2
        
        openapi_strategy = strategy_manager.strategies['openapi']
        assert isinstance(openapi_strategy, OpenApiToolExecutionStrategy)
        assert openapi_strategy.timeout == 75.0
        assert openapi_strategy.connection_timeout == 20.0
        
        function_strategy = strategy_manager.strategies['function']
        assert function_strategy.timeout == 12.0
        
        default_strategy = strategy_manager.default_strategy
        assert isinstance(default_strategy, DefaultToolExecutionStrategy)
        assert default_strategy.timeout == 12.0  # Uses function_tools timeout
        
        # Test tool timeout resolution
        assert enhanced_config.get_tool_timeout('regular_tool', 'mcp') == 35.0
        assert enhanced_config.get_tool_timeout('slow_mcp_tool', 'mcp') == 120.0  # Override
        assert enhanced_config.get_tool_timeout('fast_api_call', 'openapi') == 5.0  # Override
        assert enhanced_config.get_tool_timeout('unknown_tool', 'unknown_type') == 12.0  # Default
    
    @pytest.mark.asyncio
    async def test_tool_execution_strategies_end_to_end(self):
        """Test tool execution strategies working end-to-end."""
        # Setup configuration for different strategies
        enhanced_config = EnhancedRunConfig.from_yaml_dict({
            'tool_timeouts': {
                'mcp_tools': 30.0,
                'openapi_tools': 60.0,
                'function_tools': 15.0
            },
            'retry_policies': {
                'mcp_tools': {'max_attempts': 2, 'strategy': 'immediate'},
                'openapi_tools': {'max_attempts': 3, 'strategy': 'fixed_delay', 'base_delay': 1.0}
            }
        })
        
        # Create runner
        runner = EnhancedRunner(
            app_name="strategy-execution-app",
            agent=MockAgent(),
            session_service=MockSessionService(),
            enhanced_config=enhanced_config
        )
        
        strategy_manager = runner.tool_strategy_manager
        yaml_context = YamlSystemContext(system_name="strategy-test")
        
        # Test different tool types
        context = Mock()
        
        # 1. Test MCP tool execution
        mcp_tool = AsyncMock(return_value={"mcp_result": "success"})
        mcp_tool.__name__ = "mcp_list_resources"
        
        result = await strategy_manager.execute_tool(
            mcp_tool, 
            context, 
            yaml_context.with_tool("mcp_list_resources"),
            {"tool_type": "mcp"}
        )
        assert result == {"mcp_result": "success"}
        
        # 2. Test OpenAPI tool execution
        openapi_tool = AsyncMock(return_value={"status": "ok", "data": "api_result"})
        openapi_tool.__name__ = "api_call"
        
        result = await strategy_manager.execute_tool(
            openapi_tool,
            context,
            yaml_context.with_tool("api_call"),
            {"tool_type": "openapi"}
        )
        assert result == {"status": "ok", "data": "api_result"}
        
        # 3. Test function tool execution (default strategy)
        function_tool = AsyncMock(return_value="function_result")
        function_tool.__name__ = "process_data"
        
        result = await strategy_manager.execute_tool(
            function_tool,
            context,
            yaml_context.with_tool("process_data")
        )
        assert result == "function_result"


class TestErrorHandlingIntegration:
    """Test error handling integration across components."""
    
    def test_error_context_propagation(self):
        """Test that error context propagates correctly through all components."""
        # Create system with nested context
        base_context = YamlSystemContext(
            system_name="error-propagation-system",
            config_path="/path/to/config.yaml"
        )
        
        agent_context = base_context.with_agent("error_agent")
        tool_context = agent_context.with_tool("failing_tool")
        invocation_context = tool_context.with_invocation("inv_123", "sess_456", "user_789")
        
        # Create nested errors
        original_error = ConnectionError("Network connection failed")
        
        tool_error = ToolExecutionError(
            "Tool execution failed due to network issue",
            invocation_context,
            original_error=original_error,
            tool_type="mcp",
            execution_time=25.0,
            timeout=30.0,
            suggested_fixes=["Check network connectivity", "Retry with exponential backoff"]
        )
        
        system_error = YamlSystemError(
            "System-level execution failed",
            invocation_context,
            original_error=tool_error,
            error_code="SYS_001",
            suggested_fixes=["Review system configuration", "Check component health"]
        )
        
        # Verify error context propagation
        assert system_error.context is invocation_context
        assert system_error.original_error is tool_error
        assert tool_error.original_error is original_error
        
        # Verify location string includes full context
        location = invocation_context.get_location_string()
        expected = "error-propagation-system -> agent:error_agent -> tool:failing_tool"
        assert location == expected
        
        # Verify comprehensive debug info
        debug_info = system_error.get_debug_info()
        
        # System error info
        assert debug_info['error_type'] == 'YamlSystemError'
        assert debug_info['error_code'] == 'SYS_001'
        assert len(debug_info['suggested_fixes']) == 2
        
        # Context info
        context_info = debug_info['context']
        assert context_info['system_name'] == 'error-propagation-system'
        assert context_info['config_path'] == '/path/to/config.yaml'
        assert context_info['current_agent'] == 'error_agent'
        assert context_info['current_tool'] == 'failing_tool'
        assert context_info['invocation_id'] == 'inv_123'
        assert context_info['session_id'] == 'sess_456'
        assert context_info['user_id'] == 'user_789'
        
        # Original error info
        original_info = debug_info['original_error']
        assert original_info['type'] == 'ToolExecutionError'
        assert 'network issue' in original_info['message']
        assert isinstance(original_info['traceback'], list)


class TestPerformanceMetricsIntegration:
    """Test performance metrics integration across operations."""
    
    @pytest.mark.asyncio
    async def test_performance_metrics_comprehensive_tracking(self):
        """Test comprehensive performance metrics tracking."""
        # Create runner with metrics tracking
        runner = EnhancedRunner(
            app_name="metrics-integration-app",
            agent=MockAgent(),
            session_service=MockSessionService(),
            enhanced_config=EnhancedRunConfig(
                debug_config={'enabled': True, 'performance_profiling': True}
            )
        )
        
        # Simulate multiple operations with different outcomes
        operations = [
            (0.5, True),   # Fast success
            (1.2, True),   # Medium success  
            (2.1, False),  # Slow failure
            (0.8, True),   # Fast success
            (3.0, False),  # Very slow failure
        ]
        
        for execution_time, success in operations:
            runner._performance_metrics['total_invocations'] += 1
            runner._update_performance_metrics(execution_time, success)
        
        # Simulate tool executions
        tool_operations = [
            (0.2, True),   # Fast tool success
            (0.5, True),   # Medium tool success
            (1.0, False),  # Slow tool failure
            (0.3, True),   # Fast tool success
        ]
        
        for tool_time, tool_success in tool_operations:
            runner._update_tool_metrics(tool_time, tool_success)
        
        # Verify comprehensive metrics
        metrics = runner.get_performance_metrics()
        
        # Invocation metrics
        assert metrics['total_invocations'] == 5
        expected_avg_time = (0.5 + 1.2 + 2.1 + 0.8 + 3.0) / 5  # 1.52
        assert abs(metrics['avg_invocation_time'] - expected_avg_time) < 0.01
        
        # Error metrics
        assert metrics['error_count'] == 2  # 2 failures out of 5
        assert metrics['error_rate'] == 0.4  # 2/5 = 0.4
        assert metrics['success_rate'] == 0.6  # 3/5 = 0.6
        
        # Tool execution metrics  
        assert metrics['total_tool_executions'] == 4
        expected_tool_avg = (0.2 + 0.5 + 1.0 + 0.3) / 4  # 0.5
        assert abs(metrics['avg_tool_execution_time'] - expected_tool_avg) < 0.01
        
        # Test metrics reset
        runner.reset_performance_metrics()
        reset_metrics = runner.get_performance_metrics()
        
        assert reset_metrics['total_invocations'] == 0
        assert reset_metrics['error_count'] == 0
        assert reset_metrics['avg_invocation_time'] == 0.0
        assert reset_metrics['error_rate'] == 0.0
        assert reset_metrics['success_rate'] == 0.0


class TestConfigurationUpdateIntegration:
    """Test configuration update integration scenarios."""
    
    def test_runtime_configuration_updates(self):
        """Test runtime configuration updates and their effects."""
        # Initial configuration
        initial_yaml = {
            'max_llm_calls': 100,
            'tool_timeouts': {'mcp_tools': 30.0},
            'debug': {'enabled': False},
            'max_concurrent_tools': 5
        }
        
        runner = EnhancedRunner(
            app_name="config-update-app",
            agent=MockAgent(),
            session_service=MockSessionService(),
            enhanced_config=EnhancedRunConfig.from_yaml_dict(initial_yaml)
        )
        
        # Verify initial state
        assert runner.enhanced_config.base_config.max_llm_calls == 100
        assert runner.enhanced_config.tool_timeouts.mcp_tools == 30.0
        assert runner.enhanced_config.debug_config.enabled is False
        assert runner.enhanced_config.max_concurrent_tools == 5
        
        initial_strategy_manager = runner.tool_strategy_manager
        initial_mcp_timeout = initial_strategy_manager.strategies['mcp'].timeout
        assert initial_mcp_timeout == 30.0
        
        # Update configuration
        update_yaml = {
            'max_llm_calls': 200,  # Change
            'tool_timeouts': {
                'mcp_tools': 60.0,  # Change
                'openapi_tools': 120.0  # Add
            },
            'debug': {'enabled': True, 'trace_agent_flow': True},  # Change and add
            'max_concurrent_tools': 10,  # Change
            'enable_circuit_breaker': True  # Add new
        }
        
        runner.merge_config_from_yaml(update_yaml)
        
        # Verify updates
        assert runner.enhanced_config.base_config.max_llm_calls == 200
        assert runner.enhanced_config.tool_timeouts.mcp_tools == 60.0
        assert runner.enhanced_config.tool_timeouts.openapi_tools == 120.0
        assert runner.enhanced_config.debug_config.enabled is True
        assert runner.enhanced_config.debug_config.trace_agent_flow is True
        assert runner.enhanced_config.max_concurrent_tools == 10
        assert runner.enhanced_config.enable_circuit_breaker is True
        
        # Verify strategy manager was recreated with new timeouts
        new_strategy_manager = runner.tool_strategy_manager
        assert new_strategy_manager is not initial_strategy_manager
        
        new_mcp_timeout = new_strategy_manager.strategies['mcp'].timeout
        assert new_mcp_timeout == 60.0  # Updated timeout
    
    def test_yaml_context_updates(self):
        """Test YAML context updates and their propagation."""
        runner = EnhancedRunner(
            app_name="context-update-app",
            agent=MockAgent(),
            session_service=MockSessionService(),
            yaml_context=YamlSystemContext(
                system_name="initial-system",
                config_path="/initial/path.yaml"
            )
        )
        
        # Verify initial context
        assert runner.yaml_context.system_name == "initial-system"
        assert runner.yaml_context.config_path == "/initial/path.yaml"
        assert runner.yaml_context.current_agent is None
        
        # Update context
        new_context = YamlSystemContext(
            system_name="updated-system",
            config_path="/updated/path.yaml",
            current_agent="updated_agent",
            current_tool="updated_tool",
            additional_context={"version": "2.0", "environment": "production"}
        )
        
        runner.update_yaml_context(new_context)
        
        # Verify context update
        assert runner.yaml_context is new_context
        assert runner.yaml_context.system_name == "updated-system"
        assert runner.yaml_context.config_path == "/updated/path.yaml"
        assert runner.yaml_context.current_agent == "updated_agent"
        assert runner.yaml_context.current_tool == "updated_tool"
        assert runner.yaml_context.additional_context["version"] == "2.0"
        assert runner.yaml_context.additional_context["environment"] == "production"


@pytest.mark.integration
class TestPhase1FullIntegration:
    """Comprehensive Phase 1 integration tests."""
    
    @pytest.mark.asyncio
    async def test_complete_phase1_workflow(self):
        """Test the complete Phase 1 workflow from YAML to execution."""
        # 1. Create comprehensive YAML configuration
        yaml_config = {
            'streaming_mode': 'NONE',
            'max_llm_calls': 150,
            'tool_timeouts': {
                'mcp_tools': 45.0,
                'openapi_tools': 90.0,
                'function_tools': 15.0,
                'tool_specific_timeouts': {
                    'critical_mcp_tool': 120.0,
                    'fast_function': 5.0
                }
            },
            'retry_policies': {
                'default': {
                    'max_attempts': 3,
                    'strategy': 'exponential_backoff',
                    'base_delay': 1.0,
                    'jitter': True
                },
                'mcp_tools': {
                    'max_attempts': 2,
                    'strategy': 'immediate'
                }
            },
            'debug': {
                'enabled': True,
                'trace_agent_flow': True,
                'performance_profiling': True,
                'log_level': 'DEBUG'
            },
            'enable_circuit_breaker': True,
            'max_concurrent_tools': 8,
            'validate_tool_configs': True
        }
        
        # 2. Create enhanced configuration from YAML
        enhanced_config = EnhancedRunConfig.from_yaml_dict(yaml_config)
        
        # 3. Create YAML system context
        yaml_context = YamlSystemContext(
            system_name="phase1-integration-system",
            config_path="/integration/test/config.yaml",
            current_agent="integration_agent"
        )
        
        # 4. Create mock services
        agent = MockAgent("phase1_integration_agent")
        session_service = MockSessionService()
        
        # 5. Initialize enhanced runner
        runner = EnhancedRunner(
            app_name="phase1-integration-app",
            agent=agent,
            session_service=session_service,
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # 6. Verify complete initialization
        assert runner.enhanced_config.base_config.max_llm_calls == 150
        assert runner.enhanced_config.debug_config.enabled is True
        assert runner.yaml_context.system_name == "phase1-integration-system"
        assert isinstance(runner.tool_strategy_manager, ToolExecutionStrategyManager)
        
        # 7. Test configuration access methods
        assert runner.enhanced_config.get_tool_timeout('regular_mcp', 'mcp') == 45.0
        assert runner.enhanced_config.get_tool_timeout('critical_mcp_tool', 'mcp') == 120.0
        assert runner.enhanced_config.get_retry_config('mcp_tools').max_attempts == 2
        assert runner.enhanced_config.get_retry_config('unknown').max_attempts == 3  # default
        
        # 8. Test tool execution integration
        context = Mock()
        tool_context = yaml_context.with_tool("integration_test_tool")
        
        # Mock different tool types
        mcp_tool = AsyncMock(return_value="mcp_integration_result")
        openapi_tool = AsyncMock(return_value={"status": "success", "data": "api_result"})
        function_tool = AsyncMock(return_value="function_integration_result")
        
        # Execute tools through strategy manager
        mcp_result = await runner.tool_strategy_manager.execute_tool(
            mcp_tool, context, tool_context, {"tool_type": "mcp"}
        )
        assert mcp_result == "mcp_integration_result"
        
        openapi_result = await runner.tool_strategy_manager.execute_tool(
            openapi_tool, context, tool_context, {"tool_type": "openapi"}
        )
        assert openapi_result == {"status": "success", "data": "api_result"}
        
        function_result = await runner.tool_strategy_manager.execute_tool(
            function_tool, context, tool_context
        )
        assert function_result == "function_integration_result"
        
        # 9. Test complete execution flow
        mock_events = [
            MockEvent(author="phase1_integration_agent", content="Starting processing"),
            MockEvent(author="phase1_integration_agent", content="Tool execution complete"),
            MockEvent(author="phase1_integration_agent", content="Final response")
        ]
        
        with patch.object(runner.__class__.__bases__[0], 'run_async') as mock_parent_run:
            async def mock_event_generator():
                for event in mock_events:
                    yield event
            
            mock_parent_run.return_value = mock_event_generator()
            
            # Execute complete workflow
            collected_events = []
            async for event in runner.run_async(
                user_id="phase1_integration_user",
                session_id="phase1_integration_session",
                new_message=types.Content(parts=[types.Part(text="Complete integration test")])
            ):
                collected_events.append(event)
        
        # 10. Verify complete execution
        assert len(collected_events) == 3
        assert collected_events == mock_events
        
        # 11. Verify performance metrics
        metrics = runner.get_performance_metrics()
        assert metrics['total_invocations'] == 1
        assert metrics['error_count'] == 0
        assert metrics['success_rate'] == 1.0
        assert metrics['avg_invocation_time'] > 0
        
        # 12. Test debug information
        debug_info = runner.get_debug_info()
        assert debug_info['runner_type'] == 'EnhancedRunner'
        assert debug_info['app_name'] == 'phase1-integration-app'
        assert debug_info['yaml_context']['system_name'] == 'phase1-integration-system'
        assert debug_info['enhanced_config']['debug_enabled'] is True
        assert debug_info['enhanced_config']['circuit_breaker_enabled'] is True
        assert len(debug_info['tool_strategies']) >= 3  # mcp, openapi, function
        
        # 13. Test configuration updates
        update_config = {
            'max_llm_calls': 200,
            'tool_timeouts': {'mcp_tools': 60.0},
            'debug': {'trace_tool_execution': True}
        }
        
        runner.merge_config_from_yaml(update_config)
        
        assert runner.enhanced_config.base_config.max_llm_calls == 200
        assert runner.enhanced_config.tool_timeouts.mcp_tools == 60.0
        assert runner.enhanced_config.debug_config.trace_tool_execution is True
        
        # Verify strategy manager was recreated
        updated_mcp_strategy = runner.tool_strategy_manager.strategies['mcp']
        assert updated_mcp_strategy.timeout == 60.0
        
        # 14. Test error handling integration
        with patch.object(runner.__class__.__bases__[0], 'run_async') as mock_error_run:
            mock_error_run.side_effect = RuntimeError("Integration test error")
            
            with pytest.raises(YamlSystemError) as exc_info:
                async for _ in runner.run_async(
                    user_id="error_user",
                    session_id="error_session",
                    new_message=types.Content(parts=[types.Part(text="Error test")])
                ):
                    pass
            
            error = exc_info.value
            assert "Enhanced runner execution failed" in str(error)
            assert isinstance(error.original_error, RuntimeError)
            assert "phase1-integration-system -> agent:integration_agent" in str(error)
        
        # 15. Verify final state
        final_metrics = runner.get_performance_metrics()
        assert final_metrics['total_invocations'] == 2  # Success + error
        assert final_metrics['error_count'] == 1
        assert final_metrics['success_rate'] == 0.5