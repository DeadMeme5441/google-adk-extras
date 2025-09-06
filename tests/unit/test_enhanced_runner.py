"""Unit tests for EnhancedRunner."""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Any, Dict

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions.base_session_service import BaseSessionService
from google.genai import types

from google_adk_extras.runners.config import (
    A2AConfig,
    DebugConfig,
    EnhancedRunConfig,
    RetryConfig,
    ToolTimeoutConfig,
)
from google_adk_extras.runners.enhanced_runner import EnhancedRunner
from google_adk_extras.runners.errors import YamlSystemContext, YamlSystemError
from google_adk_extras.runners.strategies import ToolExecutionStrategyManager


class TestEnhancedRunnerInitialization:
    """Test cases for EnhancedRunner initialization."""
    
    def test_basic_initialization(self):
        """Test basic EnhancedRunner initialization."""
        app_name = "test-app"
        agent = Mock(spec=BaseAgent)
        session_service = Mock(spec=BaseSessionService)
        
        runner = EnhancedRunner(
            app_name=app_name,
            agent=agent,
            session_service=session_service
        )
        
        assert runner.app_name == app_name
        assert runner.agent is agent
        assert isinstance(runner.enhanced_config, EnhancedRunConfig)
        assert isinstance(runner.yaml_context, YamlSystemContext)
        assert runner.yaml_context.system_name == app_name
        assert isinstance(runner.tool_strategy_manager, ToolExecutionStrategyManager)
        assert runner._performance_metrics['total_invocations'] == 0
    
    def test_initialization_with_enhanced_config(self):
        """Test initialization with custom EnhancedRunConfig."""
        app_name = "enhanced-app"
        agent = Mock(spec=BaseAgent)
        session_service = Mock(spec=BaseSessionService)
        
        base_config = RunConfig(max_llm_calls=200, streaming_mode=StreamingMode.NONE)
        enhanced_config = EnhancedRunConfig(
            base_config=base_config,
            tool_timeouts=ToolTimeoutConfig(mcp_tools=45.0),
            debug_config=DebugConfig(enabled=True, trace_agent_flow=True)
        )
        
        runner = EnhancedRunner(
            app_name=app_name,
            agent=agent,
            session_service=session_service,
            enhanced_config=enhanced_config
        )
        
        assert runner.enhanced_config is enhanced_config
        assert runner.enhanced_config.base_config is base_config
        assert runner.enhanced_config.tool_timeouts.mcp_tools == 45.0
        assert runner.enhanced_config.debug_config.enabled is True
    
    def test_initialization_with_yaml_context(self):
        """Test initialization with custom YAML context."""
        app_name = "yaml-app"
        agent = Mock(spec=BaseAgent)
        session_service = Mock(spec=BaseSessionService)
        
        yaml_context = YamlSystemContext(
            system_name="custom-system",
            config_path="/path/to/config.yaml",
            current_agent="initial_agent"
        )
        
        runner = EnhancedRunner(
            app_name=app_name,
            agent=agent,
            session_service=session_service,
            yaml_context=yaml_context
        )
        
        assert runner.yaml_context is yaml_context
        assert runner.yaml_context.system_name == "custom-system"
    
    def test_initialization_with_custom_strategy_manager(self):
        """Test initialization with custom tool strategy manager."""
        app_name = "strategy-app"
        agent = Mock(spec=BaseAgent)
        session_service = Mock(spec=BaseSessionService)
        
        custom_manager = Mock(spec=ToolExecutionStrategyManager)
        
        runner = EnhancedRunner(
            app_name=app_name,
            agent=agent,
            session_service=session_service,
            tool_strategy_manager=custom_manager
        )
        
        assert runner.tool_strategy_manager is custom_manager
    
    def test_create_default_strategy_manager(self):
        """Test creation of default strategy manager."""
        app_name = "default-strategy-app"
        agent = Mock(spec=BaseAgent)
        session_service = Mock(spec=BaseSessionService)
        
        runner = EnhancedRunner(
            app_name=app_name,
            agent=agent,
            session_service=session_service
        )
        
        manager = runner.tool_strategy_manager
        
        # Check that strategies are registered
        assert 'mcp' in manager.strategies
        assert 'openapi' in manager.strategies
        assert 'function' in manager.strategies
        assert manager.default_strategy is not None
        
        # Check that strategies use enhanced config timeouts
        mcp_strategy = manager.strategies['mcp']
        assert mcp_strategy.timeout == runner.enhanced_config.tool_timeouts.mcp_tools


class TestEnhancedRunnerAsyncExecution:
    """Test cases for EnhancedRunner async execution."""
    
    @pytest.fixture
    def runner_setup(self):
        """Set up runner for async execution tests."""
        app_name = "async-test-app"
        agent = Mock(spec=BaseAgent)
        session_service = Mock(spec=BaseSessionService)
        
        enhanced_config = EnhancedRunConfig(
            base_config=RunConfig(max_llm_calls=100),
            debug_config=DebugConfig(enabled=True)
        )
        
        runner = EnhancedRunner(
            app_name=app_name,
            agent=agent,
            session_service=session_service,
            enhanced_config=enhanced_config
        )
        
        return runner
    
    @pytest.mark.asyncio
    async def test_run_async_success_flow(self, runner_setup):
        """Test successful async execution flow."""
        runner = runner_setup
        
        # Mock the parent run_async method
        mock_events = [Mock(), Mock(), Mock()]  # Simulate some events
        
        with patch.object(runner.__class__.__bases__[0], 'run_async') as mock_parent_run:
            async def mock_event_generator():
                for event in mock_events:
                    yield event
            
            mock_parent_run.return_value = mock_event_generator()
            
            # Execute run_async
            events = []
            async for event in runner.run_async(
                user_id="test_user",
                session_id="test_session",
                new_message=types.Content(parts=[types.Part(text="Hello")])
            ):
                events.append(event)
        
        # Verify events were yielded
        assert len(events) == 3
        assert events == mock_events
        
        # Verify performance metrics were updated
        assert runner._performance_metrics['total_invocations'] == 1
        assert runner._performance_metrics['avg_invocation_time'] > 0
        assert runner._performance_metrics['error_count'] == 0
    
    @pytest.mark.asyncio
    async def test_run_async_with_custom_run_config(self, runner_setup):
        """Test async execution with custom run config."""
        runner = runner_setup
        
        custom_run_config = RunConfig(max_llm_calls=50)
        
        with patch.object(runner.__class__.__bases__[0], 'run_async') as mock_parent_run:
            async def mock_event_generator():
                yield Mock()
            
            mock_parent_run.return_value = mock_event_generator()
            
            # Execute with custom config
            events = []
            async for event in runner.run_async(
                user_id="test_user",
                session_id="test_session", 
                new_message=types.Content(parts=[types.Part(text="Hello")]),
                run_config=custom_run_config
            ):
                events.append(event)
        
        # Verify custom config was passed
        mock_parent_run.assert_called_once()
        call_args = mock_parent_run.call_args[1]
        assert call_args['run_config'] is custom_run_config
    
    @pytest.mark.asyncio
    async def test_run_async_error_handling(self, runner_setup):
        """Test error handling in async execution."""
        runner = runner_setup
        
        # Mock the parent run_async to raise an exception
        with patch.object(runner.__class__.__bases__[0], 'run_async') as mock_parent_run:
            mock_parent_run.side_effect = RuntimeError("Execution failed")
            
            # Should wrap the error in YamlSystemError
            with pytest.raises(YamlSystemError) as exc_info:
                async for _ in runner.run_async(
                    user_id="test_user",
                    session_id="test_session",
                    new_message=types.Content(parts=[types.Part(text="Hello")])
                ):
                    pass
            
            error = exc_info.value
            assert "Enhanced runner execution failed" in str(error)
            assert isinstance(error.original_error, RuntimeError)
            assert "Execution failed" in str(error.original_error)
            
            # Verify error metrics were updated
            assert runner._performance_metrics['error_count'] == 1
    
    @pytest.mark.asyncio
    async def test_run_async_yaml_system_error_passthrough(self, runner_setup):
        """Test that YamlSystemError is passed through unchanged."""
        runner = runner_setup
        
        yaml_context = YamlSystemContext(system_name="test")
        original_yaml_error = YamlSystemError("Original YAML error", yaml_context)
        
        with patch.object(runner.__class__.__bases__[0], 'run_async') as mock_parent_run:
            mock_parent_run.side_effect = original_yaml_error
            
            # Should re-raise the same YamlSystemError
            with pytest.raises(YamlSystemError) as exc_info:
                async for _ in runner.run_async(
                    user_id="test_user",
                    session_id="test_session",
                    new_message=types.Content(parts=[types.Part(text="Hello")])
                ):
                    pass
            
            # Should be the same error object
            assert exc_info.value is original_yaml_error
    
    @pytest.mark.asyncio
    async def test_execution_context_manager(self, runner_setup):
        """Test the async execution context manager."""
        runner = runner_setup
        yaml_context = YamlSystemContext(system_name="test", current_agent="test_agent")
        
        # Test successful context management
        async with runner._execution_context(yaml_context) as exec_context:
            assert exec_context.context is yaml_context
            assert exec_context.current_agent == "test_agent"
    
    @pytest.mark.asyncio
    async def test_execution_context_debug_logging(self, runner_setup):
        """Test debug logging in execution context."""
        runner = runner_setup
        runner.enhanced_config.debug_config.enabled = True
        
        yaml_context = YamlSystemContext(system_name="debug-test")
        
        with patch('google_adk_extras.runners.enhanced_runner.logger') as mock_logger:
            async with runner._execution_context(yaml_context) as exec_context:
                pass  # Context manager completes
            
            # Verify debug logging
            assert mock_logger.info.call_count == 2  # Start and completion logs
            start_call = mock_logger.info.call_args_list[0][0][0]
            end_call = mock_logger.info.call_args_list[1][0][0]
            
            assert "Starting enhanced execution" in start_call
            assert "Completed enhanced execution" in end_call


class TestEnhancedRunnerPerformanceMetrics:
    """Test cases for performance metrics functionality."""
    
    @pytest.fixture
    def runner(self):
        """Create runner for metrics tests."""
        return EnhancedRunner(
            app_name="metrics-test-app",
            agent=Mock(spec=BaseAgent),
            session_service=Mock(spec=BaseSessionService)
        )
    
    def test_initial_performance_metrics(self, runner):
        """Test initial state of performance metrics."""
        metrics = runner.get_performance_metrics()
        
        expected_metrics = {
            'total_invocations': 0,
            'total_tool_executions': 0,
            'avg_invocation_time': 0.0,
            'avg_tool_execution_time': 0.0,
            'error_count': 0,
            'error_rate': 0.0,
            'success_rate': 0.0,
        }
        
        assert metrics == expected_metrics
    
    def test_update_performance_metrics_success(self, runner):
        """Test updating performance metrics for successful execution."""
        # Simulate some invocations
        runner._performance_metrics['total_invocations'] = 1
        runner._update_performance_metrics(2.5, success=True)
        
        metrics = runner.get_performance_metrics()
        assert metrics['avg_invocation_time'] == 2.5
        assert metrics['error_count'] == 0
        assert metrics['error_rate'] == 0.0
        assert metrics['success_rate'] == 1.0
    
    def test_update_performance_metrics_failure(self, runner):
        """Test updating performance metrics for failed execution."""
        # Simulate some invocations
        runner._performance_metrics['total_invocations'] = 2
        runner._update_performance_metrics(1.0, success=True)  # First success
        runner._update_performance_metrics(3.0, success=False)  # Second failure
        
        metrics = runner.get_performance_metrics()
        assert metrics['avg_invocation_time'] == 2.0  # (1.0 + 3.0) / 2
        assert metrics['error_count'] == 1
        assert metrics['error_rate'] == 0.5  # 1 error out of 2 invocations
        assert metrics['success_rate'] == 0.5
    
    def test_update_tool_metrics(self, runner):
        """Test updating tool execution metrics."""
        runner._update_tool_metrics(1.5, success=True)
        runner._update_tool_metrics(2.5, success=True)
        
        metrics = runner._performance_metrics
        assert metrics['total_tool_executions'] == 2
        assert metrics['avg_tool_execution_time'] == 2.0  # (1.5 + 2.5) / 2
    
    def test_reset_performance_metrics(self, runner):
        """Test resetting performance metrics."""
        # Set some metrics
        runner._performance_metrics['total_invocations'] = 5
        runner._performance_metrics['error_count'] = 2
        runner._performance_metrics['avg_invocation_time'] = 1.5
        
        # Reset
        runner.reset_performance_metrics()
        
        # Verify reset
        metrics = runner.get_performance_metrics()
        assert metrics['total_invocations'] == 0
        assert metrics['error_count'] == 0
        assert metrics['avg_invocation_time'] == 0.0
        assert metrics['error_rate'] == 0.0


class TestEnhancedRunnerConfigurationManagement:
    """Test cases for configuration management."""
    
    @pytest.fixture
    def runner(self):
        """Create runner for configuration tests."""
        return EnhancedRunner(
            app_name="config-test-app",
            agent=Mock(spec=BaseAgent),
            session_service=Mock(spec=BaseSessionService)
        )
    
    def test_update_yaml_context(self, runner):
        """Test updating YAML context."""
        new_context = YamlSystemContext(
            system_name="updated-system",
            config_path="/new/path/config.yaml",
            current_agent="new_agent"
        )
        
        runner.update_yaml_context(new_context)
        
        assert runner.yaml_context is new_context
        assert runner.yaml_context.system_name == "updated-system"
    
    def test_update_enhanced_config(self, runner):
        """Test updating enhanced configuration."""
        new_config = EnhancedRunConfig(
            base_config=RunConfig(max_llm_calls=300),
            tool_timeouts=ToolTimeoutConfig(mcp_tools=60.0)
        )
        
        original_strategy_manager = runner.tool_strategy_manager
        
        runner.update_enhanced_config(new_config)
        
        assert runner.enhanced_config is new_config
        assert runner.enhanced_config.base_config.max_llm_calls == 300
        assert runner.enhanced_config.tool_timeouts.mcp_tools == 60.0
        
        # Strategy manager should be recreated
        assert runner.tool_strategy_manager is not original_strategy_manager
    
    def test_merge_config_from_yaml(self, runner):
        """Test merging configuration from YAML."""
        original_mcp_timeout = runner.enhanced_config.tool_timeouts.mcp_tools
        
        additional_yaml = {
            'tool_timeouts': {
                'mcp_tools': 90.0,
                'openapi_tools': 120.0
            },
            'enable_circuit_breaker': True,
            'max_concurrent_tools': 15
        }
        
        runner.merge_config_from_yaml(additional_yaml)
        
        # Verify merge
        assert runner.enhanced_config.tool_timeouts.mcp_tools == 90.0
        assert runner.enhanced_config.tool_timeouts.openapi_tools == 120.0
        assert runner.enhanced_config.enable_circuit_breaker is True
        assert runner.enhanced_config.max_concurrent_tools == 15


class TestEnhancedRunnerToolExecution:
    """Test cases for enhanced tool execution."""
    
    @pytest.fixture
    def runner(self):
        """Create runner for tool execution tests."""
        return EnhancedRunner(
            app_name="tool-test-app",
            agent=Mock(spec=BaseAgent),
            session_service=Mock(spec=BaseSessionService)
        )
    
    @pytest.mark.asyncio
    async def test_execute_tool_enhanced_success(self, runner):
        """Test successful enhanced tool execution."""
        tool = AsyncMock()
        tool.return_value = "tool_result"
        tool.name = "test_tool"
        
        context = Mock()
        
        result = await runner._execute_tool_enhanced(tool, context)
        
        assert result == "tool_result"
        
        # Verify metrics updated
        metrics = runner._performance_metrics
        assert metrics['total_tool_executions'] == 1
        assert metrics['avg_tool_execution_time'] > 0
    
    @pytest.mark.asyncio
    async def test_execute_tool_enhanced_with_config(self, runner):
        """Test enhanced tool execution with tool config."""
        tool = AsyncMock()
        tool.return_value = "configured_result"
        tool.name = "configured_tool"
        
        context = Mock()
        tool_config = {"timeout": 45.0, "retry_attempts": 2}
        
        # Mock the strategy manager
        with patch.object(runner.tool_strategy_manager, 'execute_tool') as mock_execute:
            mock_execute.return_value = "strategy_result"
            
            result = await runner._execute_tool_enhanced(tool, context, tool_config)
            
            assert result == "strategy_result"
            
            # Verify strategy manager was called correctly
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args[0][0] is tool
            assert call_args[0][1] is context
            assert call_args[1] is tool_config  # tool_config passed
    
    @pytest.mark.asyncio
    async def test_execute_tool_enhanced_error_handling(self, runner):
        """Test error handling in enhanced tool execution."""
        tool = Mock()
        tool.__name__ = "failing_tool"
        context = Mock()
        
        # Mock the strategy manager to raise an exception
        with patch.object(runner.tool_strategy_manager, 'execute_tool') as mock_execute:
            mock_execute.side_effect = RuntimeError("Strategy execution failed")
            
            # Should wrap in ToolExecutionError
            from google_adk_extras.runners.errors import ToolExecutionError
            with pytest.raises(ToolExecutionError) as exc_info:
                await runner._execute_tool_enhanced(tool, context)
            
            error = exc_info.value
            assert "Unexpected tool execution error" in str(error)
            assert isinstance(error.original_error, RuntimeError)
            
            # Verify error metrics updated
            assert runner._performance_metrics['total_tool_executions'] == 1


class TestEnhancedRunnerDebugInfo:
    """Test cases for debug information."""
    
    def test_get_debug_info(self):
        """Test getting comprehensive debug information."""
        app_name = "debug-info-app"
        agent = Mock(spec=BaseAgent)
        agent.name = "test_agent"
        session_service = Mock(spec=BaseSessionService)
        
        enhanced_config = EnhancedRunConfig(
            debug_config=DebugConfig(enabled=True),
            enable_circuit_breaker=True,
            max_concurrent_tools=10
        )
        
        yaml_context = YamlSystemContext(
            system_name="debug-system",
            config_path="/debug/config.yaml",
            current_agent="debug_agent",
            current_tool="debug_tool"
        )
        
        runner = EnhancedRunner(
            app_name=app_name,
            agent=agent,
            session_service=session_service,
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Set some performance metrics
        runner._performance_metrics['total_invocations'] = 5
        runner._performance_metrics['error_count'] = 1
        
        debug_info = runner.get_debug_info()
        
        # Verify debug info structure
        assert debug_info['runner_type'] == 'EnhancedRunner'
        assert debug_info['app_name'] == app_name
        
        # Verify YAML context info
        yaml_info = debug_info['yaml_context']
        assert yaml_info['system_name'] == 'debug-system'
        assert yaml_info['config_path'] == '/debug/config.yaml'
        assert yaml_info['current_agent'] == 'debug_agent'
        assert yaml_info['current_tool'] == 'debug_tool'
        
        # Verify enhanced config info
        config_info = debug_info['enhanced_config']
        assert config_info['debug_enabled'] is True
        assert config_info['circuit_breaker_enabled'] is True
        assert config_info['max_concurrent_tools'] == 10
        
        # Verify performance metrics
        perf_metrics = debug_info['performance_metrics']
        assert perf_metrics['total_invocations'] == 5
        assert perf_metrics['error_count'] == 1
        
        # Verify tool strategies
        assert 'mcp' in debug_info['tool_strategies']
        assert 'openapi' in debug_info['tool_strategies']
        assert 'function' in debug_info['tool_strategies']
    
    def test_string_representation(self):
        """Test string representation of EnhancedRunner."""
        app_name = "repr-test-app"
        agent = Mock(spec=BaseAgent)
        agent.name = "repr_agent"
        session_service = Mock(spec=BaseSessionService)
        
        yaml_context = YamlSystemContext(system_name="repr-system")
        
        runner = EnhancedRunner(
            app_name=app_name,
            agent=agent,
            session_service=session_service,
            yaml_context=yaml_context
        )
        
        # Set some metrics for representation
        runner._performance_metrics['total_invocations'] = 3
        
        repr_str = repr(runner)
        
        assert f"EnhancedRunner(app_name='{app_name}'" in repr_str
        assert "system='repr-system'" in repr_str
        assert "agent='repr_agent'" in repr_str
        assert "invocations=3)" in repr_str


class TestEnhancedRunnerIntegration:
    """Integration tests for EnhancedRunner."""
    
    @pytest.mark.asyncio
    async def test_complete_runner_workflow(self):
        """Test complete enhanced runner workflow."""
        # Setup
        app_name = "integration-test-app"
        agent = Mock(spec=BaseAgent)
        agent.name = "integration_agent"
        session_service = Mock(spec=BaseSessionService)
        
        enhanced_config = EnhancedRunConfig(
            base_config=RunConfig(max_llm_calls=50),
            tool_timeouts=ToolTimeoutConfig(mcp_tools=30.0),
            debug_config=DebugConfig(enabled=True, trace_agent_flow=True),
            enable_circuit_breaker=True
        )
        
        yaml_context = YamlSystemContext(
            system_name="integration-system",
            config_path="/integration/config.yaml"
        )
        
        runner = EnhancedRunner(
            app_name=app_name,
            agent=agent,
            session_service=session_service,
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Mock successful execution
        mock_events = [Mock(author="test_agent"), Mock(), Mock()]
        
        with patch.object(runner.__class__.__bases__[0], 'run_async') as mock_parent_run:
            async def mock_event_generator():
                for event in mock_events:
                    yield event
            
            mock_parent_run.return_value = mock_event_generator()
            
            # Execute
            events = []
            async for event in runner.run_async(
                user_id="integration_user",
                session_id="integration_session",
                new_message=types.Content(parts=[types.Part(text="Integration test")])
            ):
                events.append(event)
        
        # Verify complete workflow
        assert len(events) == 3
        assert runner._performance_metrics['total_invocations'] == 1
        assert runner._performance_metrics['error_count'] == 0
        
        # Verify configuration integration
        debug_info = runner.get_debug_info()
        assert debug_info['enhanced_config']['debug_enabled'] is True
        assert debug_info['enhanced_config']['circuit_breaker_enabled'] is True
        
        # Verify YAML context integration
        assert debug_info['yaml_context']['system_name'] == 'integration-system'