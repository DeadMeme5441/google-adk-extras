"""Unit tests for enhanced runner tool execution strategies."""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch

from google_adk_extras.runners.config import CircuitBreakerConfig, RetryConfig, RetryStrategy
from google_adk_extras.runners.errors import ToolExecutionError, YamlSystemContext
from google_adk_extras.runners.strategies import (
    CircuitBreaker,
    CircuitBreakerState,
    DefaultToolExecutionStrategy,
    FunctionToolExecutionStrategy,
    McpToolExecutionStrategy,
    OpenApiToolExecutionStrategy,
    RetryExecutor,
    ToolExecutionStrategyManager,
)


class TestCircuitBreaker:
    """Test cases for CircuitBreaker."""
    
    def test_default_initialization(self):
        """Test CircuitBreaker default initialization."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config)
        
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.last_failure_time is None
        assert cb.config is config
    
    def test_record_success_closed_state(self):
        """Test recording success in closed state."""
        cb = CircuitBreaker(CircuitBreakerConfig())
        cb.failure_count = 2
        
        cb.record_success()
        
        assert cb.failure_count == 0  # Reset on success
        assert cb.success_count == 0  # Not used in closed state
        assert cb.state == CircuitBreakerState.CLOSED
    
    def test_record_failure_transitions_to_open(self):
        """Test recording failures causes transition to open."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(config)
        
        # Record failures up to threshold
        for i in range(2):
            cb.record_failure()
            assert cb.state == CircuitBreakerState.CLOSED
            assert cb.failure_count == i + 1
        
        # Third failure should open circuit
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 3
        assert cb.last_failure_time is not None
    
    def test_can_execute_closed_state(self):
        """Test can_execute in closed state."""
        cb = CircuitBreaker(CircuitBreakerConfig())
        assert cb.can_execute() is True
    
    def test_can_execute_open_state_within_timeout(self):
        """Test can_execute in open state within recovery timeout."""
        cb = CircuitBreaker(CircuitBreakerConfig(recovery_timeout=60.0))
        cb.state = CircuitBreakerState.OPEN
        cb.last_failure_time = time.time()
        
        assert cb.can_execute() is False
    
    def test_can_execute_open_state_after_timeout(self):
        """Test can_execute in open state after recovery timeout."""
        cb = CircuitBreaker(CircuitBreakerConfig(recovery_timeout=1.0))
        cb.state = CircuitBreakerState.OPEN
        cb.last_failure_time = time.time() - 2.0  # 2 seconds ago
        
        result = cb.can_execute()
        assert result is True
        assert cb.state == CircuitBreakerState.HALF_OPEN
        assert cb.success_count == 0
    
    def test_can_execute_half_open_state(self):
        """Test can_execute in half-open state."""
        cb = CircuitBreaker(CircuitBreakerConfig())
        cb.state = CircuitBreakerState.HALF_OPEN
        
        assert cb.can_execute() is True
    
    def test_half_open_success_transitions_to_closed(self):
        """Test successful operations in half-open state transition to closed."""
        config = CircuitBreakerConfig(success_threshold=2)
        cb = CircuitBreaker(config)
        cb.state = CircuitBreakerState.HALF_OPEN
        
        # First success
        cb.record_success()
        assert cb.state == CircuitBreakerState.HALF_OPEN
        assert cb.success_count == 1
        
        # Second success should close circuit
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.success_count == 0
        assert cb.failure_count == 0
    
    def test_half_open_failure_transitions_to_open(self):
        """Test failure in half-open state transitions back to open."""
        cb = CircuitBreaker(CircuitBreakerConfig())
        cb.state = CircuitBreakerState.HALF_OPEN
        cb.success_count = 1
        
        cb.record_failure()
        
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 1
        assert cb.success_count == 0
        assert cb.last_failure_time is not None


class TestRetryExecutor:
    """Test cases for RetryExecutor."""
    
    @pytest.mark.asyncio
    async def test_no_retry_on_success(self):
        """Test no retry when operation succeeds immediately."""
        config = RetryConfig(max_attempts=3)
        executor = RetryExecutor(config)
        
        async def successful_operation():
            return "success"
        
        result = await executor.execute(successful_operation)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_on_failure_then_success(self):
        """Test retry on failure then success."""
        config = RetryConfig(max_attempts=3, strategy=RetryStrategy.IMMEDIATE)
        executor = RetryExecutor(config)
        
        attempt_count = 0
        async def flaky_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Temporary failure")
            return f"success_on_attempt_{attempt_count}"
        
        result = await executor.execute(flaky_operation)
        assert result == "success_on_attempt_2"
        assert attempt_count == 2
    
    @pytest.mark.asyncio
    async def test_exhaust_all_attempts(self):
        """Test exhausting all retry attempts."""
        config = RetryConfig(max_attempts=2, strategy=RetryStrategy.IMMEDIATE)
        executor = RetryExecutor(config)
        
        attempt_count = 0
        async def failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            raise RuntimeError(f"Failure {attempt_count}")
        
        with pytest.raises(RuntimeError, match="Failure 2"):
            await executor.execute(failing_operation)
        
        assert attempt_count == 2
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff delays."""
        config = RetryConfig(
            max_attempts=3,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=0.1,
            backoff_multiplier=2.0,
            jitter=False  # Disable jitter for predictable testing
        )
        executor = RetryExecutor(config)
        
        attempt_times = []
        async def timing_operation():
            attempt_times.append(time.time())
            if len(attempt_times) < 3:
                raise ValueError("Not yet")
            return "success"
        
        start_time = time.time()
        result = await executor.execute(timing_operation)
        
        assert result == "success"
        assert len(attempt_times) == 3
        
        # Check delays (approximately)
        delay_1 = attempt_times[1] - attempt_times[0]
        delay_2 = attempt_times[2] - attempt_times[1]
        
        assert 0.08 <= delay_1 <= 0.12  # ~0.1s base delay
        assert 0.18 <= delay_2 <= 0.22  # ~0.2s (base * multiplier)
    
    @pytest.mark.asyncio
    async def test_fixed_delay_timing(self):
        """Test fixed delay timing."""
        config = RetryConfig(
            max_attempts=3,
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=0.1,
            jitter=False
        )
        executor = RetryExecutor(config)
        
        attempt_times = []
        async def timing_operation():
            attempt_times.append(time.time())
            if len(attempt_times) < 2:
                raise ValueError("Not yet")
            return "success"
        
        result = await executor.execute(timing_operation)
        
        assert result == "success"
        assert len(attempt_times) == 2
        
        delay = attempt_times[1] - attempt_times[0]
        assert 0.08 <= delay <= 0.12  # ~0.1s fixed delay
    
    @pytest.mark.asyncio
    async def test_immediate_strategy_no_delay(self):
        """Test immediate strategy has no delay."""
        config = RetryConfig(
            max_attempts=3,
            strategy=RetryStrategy.IMMEDIATE,
            base_delay=1.0  # Should be ignored
        )
        executor = RetryExecutor(config)
        
        attempt_times = []
        async def timing_operation():
            attempt_times.append(time.time())
            if len(attempt_times) < 2:
                raise ValueError("Not yet")
            return "success"
        
        start_time = time.time()
        result = await executor.execute(timing_operation)
        end_time = time.time()
        
        assert result == "success"
        assert len(attempt_times) == 2
        assert end_time - start_time < 0.05  # Should be very fast


class TestDefaultToolExecutionStrategy:
    """Test cases for DefaultToolExecutionStrategy."""
    
    def test_initialization(self):
        """Test DefaultToolExecutionStrategy initialization."""
        retry_config = RetryConfig(max_attempts=3)
        strategy = DefaultToolExecutionStrategy(
            timeout=30.0,
            retry_config=retry_config
        )
        
        assert strategy.timeout == 30.0
        assert strategy.retry_config is retry_config
        assert isinstance(strategy.retry_executor, RetryExecutor)
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Test successful tool execution."""
        strategy = DefaultToolExecutionStrategy(timeout=30.0)
        
        tool = AsyncMock()
        tool.return_value = "tool_result"
        context = Mock()
        yaml_context = YamlSystemContext(system_name="test")
        
        result = await strategy.execute_tool(tool, context, yaml_context)
        
        assert result == "tool_result"
        tool.assert_called_once_with(context)
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_timeout(self):
        """Test tool execution timeout."""
        strategy = DefaultToolExecutionStrategy(timeout=0.1)
        
        async def slow_tool(context):
            await asyncio.sleep(0.2)
            return "should_not_reach"
        
        context = Mock()
        yaml_context = YamlSystemContext(system_name="test")
        
        with pytest.raises(ToolExecutionError, match="Tool execution timed out"):
            await strategy.execute_tool(slow_tool, context, yaml_context)
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_retry(self):
        """Test tool execution with retry on failure."""
        retry_config = RetryConfig(max_attempts=3, strategy=RetryStrategy.IMMEDIATE)
        strategy = DefaultToolExecutionStrategy(
            timeout=30.0,
            retry_config=retry_config
        )
        
        attempt_count = 0
        async def flaky_tool(context):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise RuntimeError("Temporary failure")
            return f"success_attempt_{attempt_count}"
        
        context = Mock()
        yaml_context = YamlSystemContext(system_name="test")
        
        result = await strategy.execute_tool(flaky_tool, context, yaml_context)
        
        assert result == "success_attempt_2"
        assert attempt_count == 2


class TestMcpToolExecutionStrategy:
    """Test cases for McpToolExecutionStrategy."""
    
    def test_initialization(self):
        """Test McpToolExecutionStrategy initialization."""
        retry_config = RetryConfig(max_attempts=2)
        strategy = McpToolExecutionStrategy(
            timeout=45.0,
            connection_timeout=15.0,
            retry_config=retry_config
        )
        
        assert strategy.timeout == 45.0
        assert strategy.connection_timeout == 15.0
        assert strategy.retry_config is retry_config
    
    @pytest.mark.asyncio
    async def test_execute_tool_mcp_specific_handling(self):
        """Test MCP-specific tool execution."""
        strategy = McpToolExecutionStrategy(timeout=30.0, connection_timeout=10.0)
        
        tool = AsyncMock()
        tool.return_value = {"result": "mcp_data", "metadata": {"server": "test-server"}}
        context = Mock()
        yaml_context = YamlSystemContext(system_name="test", current_tool="mcp_tool")
        
        result = await strategy.execute_tool(tool, context, yaml_context)
        
        assert result == {"result": "mcp_data", "metadata": {"server": "test-server"}}
    
    @pytest.mark.asyncio
    async def test_execute_tool_connection_timeout(self):
        """Test MCP tool with connection timeout."""
        strategy = McpToolExecutionStrategy(timeout=30.0, connection_timeout=0.1)
        
        async def connection_slow_tool(context):
            # Simulate slow connection establishment
            await asyncio.sleep(0.2)
            return "should_not_reach"
        
        context = Mock()
        yaml_context = YamlSystemContext(system_name="test", current_tool="mcp_tool")
        
        with pytest.raises(ToolExecutionError) as exc_info:
            await strategy.execute_tool(connection_slow_tool, context, yaml_context)
        
        assert "timeout" in str(exc_info.value).lower()


class TestOpenApiToolExecutionStrategy:
    """Test cases for OpenApiToolExecutionStrategy."""
    
    def test_initialization(self):
        """Test OpenApiToolExecutionStrategy initialization."""
        circuit_breaker_config = CircuitBreakerConfig(failure_threshold=3)
        strategy = OpenApiToolExecutionStrategy(
            timeout=60.0,
            connection_timeout=20.0,
            circuit_breaker_config=circuit_breaker_config
        )
        
        assert strategy.timeout == 60.0
        assert strategy.connection_timeout == 20.0
        assert isinstance(strategy.circuit_breaker, CircuitBreaker)
        assert strategy.circuit_breaker.config is circuit_breaker_config
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_circuit_breaker_closed(self):
        """Test OpenAPI tool execution with circuit breaker closed."""
        strategy = OpenApiToolExecutionStrategy(timeout=30.0)
        
        tool = AsyncMock()
        tool.return_value = {"status": "success", "data": {"key": "value"}}
        context = Mock()
        yaml_context = YamlSystemContext(system_name="test", current_tool="openapi_tool")
        
        result = await strategy.execute_tool(tool, context, yaml_context)
        
        assert result == {"status": "success", "data": {"key": "value"}}
        assert strategy.circuit_breaker.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_execute_tool_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after multiple failures."""
        config = CircuitBreakerConfig(failure_threshold=2)
        strategy = OpenApiToolExecutionStrategy(timeout=30.0, circuit_breaker_config=config)
        
        async def failing_tool(context):
            raise RuntimeError("API failure")
        
        context = Mock()
        yaml_context = YamlSystemContext(system_name="test", current_tool="openapi_tool")
        
        # First failure
        with pytest.raises(ToolExecutionError):
            await strategy.execute_tool(failing_tool, context, yaml_context)
        assert strategy.circuit_breaker.state == CircuitBreakerState.CLOSED
        
        # Second failure should open circuit
        with pytest.raises(ToolExecutionError):
            await strategy.execute_tool(failing_tool, context, yaml_context)
        assert strategy.circuit_breaker.state == CircuitBreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_execute_tool_circuit_breaker_rejects_when_open(self):
        """Test circuit breaker rejects requests when open."""
        strategy = OpenApiToolExecutionStrategy(timeout=30.0)
        strategy.circuit_breaker.state = CircuitBreakerState.OPEN
        strategy.circuit_breaker.last_failure_time = time.time()
        
        tool = AsyncMock()
        context = Mock()
        yaml_context = YamlSystemContext(system_name="test", current_tool="openapi_tool")
        
        with pytest.raises(ToolExecutionError, match="Circuit breaker is open"):
            await strategy.execute_tool(tool, context, yaml_context)
        
        # Tool should not have been called
        tool.assert_not_called()


class TestFunctionToolExecutionStrategy:
    """Test cases for FunctionToolExecutionStrategy."""
    
    def test_initialization(self):
        """Test FunctionToolExecutionStrategy initialization."""
        retry_config = RetryConfig(max_attempts=5)
        strategy = FunctionToolExecutionStrategy(
            timeout=15.0,
            retry_config=retry_config
        )
        
        assert strategy.timeout == 15.0
        assert strategy.retry_config is retry_config
    
    @pytest.mark.asyncio
    async def test_execute_tool_function_handling(self):
        """Test function tool execution."""
        strategy = FunctionToolExecutionStrategy(timeout=30.0)
        
        def sync_tool(context):
            return f"processed_{context.value}"
        
        context = Mock()
        context.value = "test_data"
        yaml_context = YamlSystemContext(system_name="test", current_tool="function_tool")
        
        result = await strategy.execute_tool(sync_tool, context, yaml_context)
        
        assert result == "processed_test_data"
    
    @pytest.mark.asyncio
    async def test_execute_tool_async_function(self):
        """Test async function tool execution."""
        strategy = FunctionToolExecutionStrategy(timeout=30.0)
        
        async def async_tool(context):
            await asyncio.sleep(0.01)  # Small delay
            return f"async_processed_{context.value}"
        
        context = Mock()
        context.value = "async_data"
        yaml_context = YamlSystemContext(system_name="test", current_tool="async_function_tool")
        
        result = await strategy.execute_tool(async_tool, context, yaml_context)
        
        assert result == "async_processed_async_data"


class TestToolExecutionStrategyManager:
    """Test cases for ToolExecutionStrategyManager."""
    
    def test_initialization(self):
        """Test ToolExecutionStrategyManager initialization."""
        manager = ToolExecutionStrategyManager()
        
        assert manager.strategies == {}
        assert manager.default_strategy is None
    
    def test_register_strategy(self):
        """Test registering tool execution strategies."""
        manager = ToolExecutionStrategyManager()
        strategy = DefaultToolExecutionStrategy(timeout=30.0)
        
        manager.register_strategy("test_type", strategy)
        
        assert "test_type" in manager.strategies
        assert manager.strategies["test_type"] is strategy
    
    def test_set_default_strategy(self):
        """Test setting default strategy."""
        manager = ToolExecutionStrategyManager()
        strategy = DefaultToolExecutionStrategy(timeout=30.0)
        
        manager.set_default_strategy(strategy)
        
        assert manager.default_strategy is strategy
    
    def test_get_strategy_by_type(self):
        """Test getting strategy by tool type."""
        manager = ToolExecutionStrategyManager()
        mcp_strategy = McpToolExecutionStrategy(timeout=30.0)
        default_strategy = DefaultToolExecutionStrategy(timeout=15.0)
        
        manager.register_strategy("mcp", mcp_strategy)
        manager.set_default_strategy(default_strategy)
        
        assert manager.get_strategy("mcp") is mcp_strategy
        assert manager.get_strategy("unknown_type") is default_strategy
    
    def test_get_strategy_no_default(self):
        """Test getting strategy with no default set."""
        manager = ToolExecutionStrategyManager()
        
        with pytest.raises(ValueError, match="No strategy registered for tool type"):
            manager.get_strategy("unknown_type")
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_manager(self):
        """Test tool execution through manager."""
        manager = ToolExecutionStrategyManager()
        
        # Setup strategies
        mcp_strategy = McpToolExecutionStrategy(timeout=30.0)
        default_strategy = DefaultToolExecutionStrategy(timeout=15.0)
        
        manager.register_strategy("mcp", mcp_strategy)
        manager.set_default_strategy(default_strategy)
        
        # Mock tool and context
        tool = AsyncMock()
        tool.return_value = "mcp_result"
        context = Mock()
        yaml_context = YamlSystemContext(system_name="test", current_tool="test_tool")
        tool_config = {"tool_type": "mcp"}
        
        # Execute tool
        result = await manager.execute_tool(tool, context, yaml_context, tool_config)
        
        assert result == "mcp_result"
    
    @pytest.mark.asyncio
    async def test_execute_tool_detect_type_from_name(self):
        """Test tool execution with type detection from tool name."""
        manager = ToolExecutionStrategyManager()
        
        # Create mock strategies with different behaviors
        mcp_strategy = Mock()
        mcp_strategy.execute_tool = AsyncMock(return_value="mcp_executed")
        
        default_strategy = Mock()
        default_strategy.execute_tool = AsyncMock(return_value="default_executed")
        
        manager.register_strategy("mcp", mcp_strategy)
        manager.set_default_strategy(default_strategy)
        
        # Mock tool with MCP-like name
        tool = Mock()
        tool.__name__ = "mcp_list_files"
        
        context = Mock()
        yaml_context = YamlSystemContext(system_name="test", current_tool="mcp_list_files")
        
        # Should detect MCP type from tool name
        result = await manager.execute_tool(tool, context, yaml_context)
        
        assert result == "mcp_executed"
        mcp_strategy.execute_tool.assert_called_once()
        default_strategy.execute_tool.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_tool_fallback_to_default(self):
        """Test tool execution falls back to default strategy."""
        manager = ToolExecutionStrategyManager()
        
        default_strategy = Mock()
        default_strategy.execute_tool = AsyncMock(return_value="default_executed")
        
        manager.set_default_strategy(default_strategy)
        
        # Mock tool with unknown type
        tool = Mock()
        tool.__name__ = "unknown_tool"
        
        context = Mock()
        yaml_context = YamlSystemContext(system_name="test", current_tool="unknown_tool")
        
        result = await manager.execute_tool(tool, context, yaml_context)
        
        assert result == "default_executed"
        default_strategy.execute_tool.assert_called_once()


class TestStrategyIntegration:
    """Integration tests for strategy system."""
    
    @pytest.mark.asyncio
    async def test_complete_strategy_workflow(self):
        """Test complete workflow with multiple strategies and error handling."""
        # Setup manager with different strategies
        manager = ToolExecutionStrategyManager()
        
        # MCP strategy with circuit breaker
        mcp_strategy = McpToolExecutionStrategy(
            timeout=30.0,
            connection_timeout=10.0,
            retry_config=RetryConfig(max_attempts=2, strategy=RetryStrategy.IMMEDIATE)
        )
        
        # OpenAPI strategy with circuit breaker
        openapi_strategy = OpenApiToolExecutionStrategy(
            timeout=60.0,
            connection_timeout=15.0,
            circuit_breaker_config=CircuitBreakerConfig(failure_threshold=3)
        )
        
        # Default strategy
        default_strategy = DefaultToolExecutionStrategy(
            timeout=15.0,
            retry_config=RetryConfig(max_attempts=3)
        )
        
        manager.register_strategy("mcp", mcp_strategy)
        manager.register_strategy("openapi", openapi_strategy)
        manager.set_default_strategy(default_strategy)
        
        # Test different tool executions
        context = Mock()
        yaml_context = YamlSystemContext(system_name="integration-test")
        
        # 1. Successful MCP tool
        mcp_tool = AsyncMock(return_value="mcp_success")
        result = await manager.execute_tool(
            mcp_tool, 
            context, 
            yaml_context.with_tool("mcp_list_resources"),
            {"tool_type": "mcp"}
        )
        assert result == "mcp_success"
        
        # 2. Successful OpenAPI tool
        openapi_tool = AsyncMock(return_value={"status": "ok", "data": "api_success"})
        result = await manager.execute_tool(
            openapi_tool,
            context,
            yaml_context.with_tool("api_call"),
            {"tool_type": "openapi"}
        )
        assert result == {"status": "ok", "data": "api_success"}
        
        # 3. Default strategy tool
        function_tool = AsyncMock(return_value="function_success")
        result = await manager.execute_tool(
            function_tool,
            context,
            yaml_context.with_tool("process_data")
        )
        assert result == "function_success"
        
        # Verify strategies maintain their state
        assert mcp_strategy.retry_executor.config.max_attempts == 2
        assert openapi_strategy.circuit_breaker.state == CircuitBreakerState.CLOSED
        assert default_strategy.timeout == 15.0