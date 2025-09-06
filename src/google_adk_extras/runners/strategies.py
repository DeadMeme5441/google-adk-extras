"""Tool execution strategies for enhanced runners.

This module provides configurable strategies for executing different types
of tools (MCP, OpenAPI, function tools) with advanced features like
timeouts, retries, circuit breakers, and error handling.
"""

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional, Type, Union

from google.adk.agents.invocation_context import InvocationContext

from .config import CircuitBreakerConfig, CircuitBreakerState, RetryConfig, RetryStrategy
from .errors import ToolExecutionError, YamlSystemContext

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker implementation for tool execution.
    
    Implements the circuit breaker pattern to prevent cascading failures
    when external services (like MCP servers or APIs) are failing.
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        """Initialize circuit breaker.
        
        Args:
            config: Circuit breaker configuration
        """
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
    
    async def call(self, func, *args, **kwargs):
        """Execute a function through the circuit breaker.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Any: Function result
            
        Raises:
            ToolExecutionError: If circuit breaker is open or function fails
        """
        if self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time is not None and time.time() - self.last_failure_time < self.config.recovery_timeout:
                raise ToolExecutionError(
                    "Circuit breaker is OPEN - rejecting request",
                    context=kwargs.get('context', YamlSystemContext('unknown')),
                    error_code="CIRCUIT_BREAKER_OPEN"
                )
            else:
                # Try to recover
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            # Success - update state
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
            elif self.state == CircuitBreakerState.CLOSED:
                self.failure_count = max(0, self.failure_count - 1)
            
            return result
            
        except Exception as e:
            # Failure - update state
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
            elif self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
            
            raise e
    
    def can_execute(self) -> bool:
        """Check if circuit breaker allows execution.
        
        Returns:
            bool: True if execution is allowed, False if circuit is open
        """
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time is not None and time.time() - self.last_failure_time >= self.config.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record a successful execution."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success in closed state
            self.failure_count = 0
    
    def record_failure(self):
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Any failure in half-open goes back to open
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0


class RetryExecutor:
    """Retry executor with configurable retry strategies."""
    
    def __init__(self, config: RetryConfig):
        """Initialize retry executor.
        
        Args:
            config: Retry configuration
        """
        self.config = config
    
    async def execute_with_retry(self, func, context: YamlSystemContext, *args, **kwargs):
        """Execute function with retry logic.
        
        Args:
            func: Function to execute
            context: YAML system context
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Any: Function result
            
        Raises:
            ToolExecutionError: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.config.max_attempts - 1:
                    # Last attempt failed
                    break
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt)
                logger.debug(f"Retry attempt {attempt + 1} failed, waiting {delay:.2f}s: {e}")
                await asyncio.sleep(delay)
        
        # All attempts failed
        raise ToolExecutionError(
            f"Tool execution failed after {self.config.max_attempts} attempts",
            context=context,
            original_error=last_exception,
            suggested_fixes=[
                "Check if the external service is available",
                "Increase retry attempts or timeout values",
                "Verify tool configuration and parameters"
            ]
        )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            float: Delay in seconds
        """
        if self.config.strategy == RetryStrategy.IMMEDIATE:
            delay = 0.0
        elif self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * (attempt + 1)
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** attempt)
        else:
            delay = self.config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter and delay > 0:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay
    
    async def execute(self, func):
        """Simple execute method for testing without context.
        
        Args:
            func: Function to execute with retry logic
            
        Returns:
            Any: Function result
            
        Raises:
            Exception: The last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                result = await func()
                return result
            except Exception as e:
                last_exception = e
                logger.debug(f"Attempt {attempt + 1} failed: {e}")
                
                # Don't wait after the last attempt
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    if delay > 0:
                        await asyncio.sleep(delay)
        
        # All attempts failed, re-raise the last exception
        raise last_exception


class ToolExecutionStrategy(ABC):
    """Abstract base class for tool execution strategies.
    
    Tool execution strategies define how different types of tools
    should be executed, with support for timeouts, retries,
    circuit breakers, and error handling.
    """
    
    @abstractmethod
    async def execute_tool(
        self,
        tool: Any,
        context: InvocationContext,
        yaml_context: YamlSystemContext,
        tool_config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a tool with the strategy's configuration.
        
        Args:
            tool: The tool to execute
            context: ADK invocation context
            yaml_context: YAML system context
            tool_config: Tool-specific configuration
            
        Returns:
            Any: Tool execution result
            
        Raises:
            ToolExecutionError: If tool execution fails
        """
        pass
    
    @abstractmethod
    def get_tool_type(self) -> str:
        """Get the tool type this strategy handles.
        
        Returns:
            str: Tool type identifier
        """
        pass


class DefaultToolExecutionStrategy(ToolExecutionStrategy):
    """Default tool execution strategy with basic timeout and retry support."""
    
    def __init__(
        self,
        timeout: float = 30.0,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    ):
        """Initialize default strategy.
        
        Args:
            timeout: Execution timeout in seconds
            retry_config: Retry configuration
            circuit_breaker_config: Circuit breaker configuration
        """
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.retry_executor = RetryExecutor(self.retry_config)
        
        self.circuit_breaker = None
        if circuit_breaker_config:
            self.circuit_breaker = CircuitBreaker(circuit_breaker_config)
    
    async def execute_tool(
        self,
        tool: Any,
        context: InvocationContext,
        yaml_context: YamlSystemContext,
        tool_config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute tool with default strategy."""
        start_time = time.time()
        
        async def _execute():
            try:
                # Execute the tool with timeout
                if hasattr(tool, '__call__'):
                    if asyncio.iscoroutinefunction(tool):
                        result = await asyncio.wait_for(tool(context), timeout=self.timeout)
                    else:
                        result = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None, tool, context
                            ),
                            timeout=self.timeout
                        )
                else:
                    # Assume it's a tool object with an execute method
                    if hasattr(tool, 'execute'):
                        result = await asyncio.wait_for(tool.execute(context), timeout=self.timeout)
                    else:
                        raise ToolExecutionError(
                            f"Tool {tool} is not callable and has no execute method",
                            context=yaml_context,
                            tool_type=self.get_tool_type(),
                            suggested_fixes=[
                                "Ensure tool is properly configured",
                                "Check tool implementation"
                            ]
                        )
                
                return result
                
            except asyncio.TimeoutError:
                execution_time = time.time() - start_time
                raise ToolExecutionError(
                    f"Tool execution timed out",
                    context=yaml_context,
                    tool_type=self.get_tool_type(),
                    execution_time=execution_time,
                    timeout=self.timeout,
                    suggested_fixes=[
                        "Increase tool timeout in configuration",
                        "Check if external service is responsive",
                        "Optimize tool implementation"
                    ]
                )
            except Exception as e:
                execution_time = time.time() - start_time
                raise ToolExecutionError(
                    f"Tool execution failed: {str(e)}",
                    context=yaml_context,
                    tool_type=self.get_tool_type(),
                    execution_time=execution_time,
                    original_error=e
                )
        
        # Execute with circuit breaker if configured
        if self.circuit_breaker:
            return await self.circuit_breaker.call(_execute, context=yaml_context)
        
        # Execute with retry
        return await self.retry_executor.execute_with_retry(_execute, yaml_context)
    
    def get_tool_type(self) -> str:
        """Get tool type."""
        return "function"


class McpToolExecutionStrategy(DefaultToolExecutionStrategy):
    """Execution strategy optimized for MCP (Model Context Protocol) tools."""
    
    def __init__(
        self,
        timeout: float = 30.0,
        connection_timeout: float = 10.0,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    ):
        """Initialize MCP strategy.
        
        Args:
            timeout: Tool execution timeout
            connection_timeout: MCP server connection timeout
            retry_config: Retry configuration (optimized for MCP)
            circuit_breaker_config: Circuit breaker configuration
        """
        # Default retry config for MCP tools
        if retry_config is None:
            retry_config = RetryConfig(
                max_attempts=2,  # MCP servers can be flaky
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=0.5,
                max_delay=5.0
            )
        
        super().__init__(timeout, retry_config, circuit_breaker_config)
        self.connection_timeout = connection_timeout
    
    async def execute_tool(
        self,
        tool: Any,
        context: InvocationContext,
        yaml_context: YamlSystemContext,
        tool_config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute MCP tool with specialized handling."""
        # Update context for MCP tool
        mcp_context = yaml_context.with_tool(getattr(tool, 'name', 'unknown_mcp_tool'))
        mcp_context = mcp_context.add_context('tool_type', 'mcp')
        
        try:
            return await super().execute_tool(tool, context, mcp_context, tool_config)
        except ToolExecutionError as e:
            # Add MCP-specific suggestions
            e.suggested_fixes.extend([
                "Check if MCP server is running and accessible",
                "Verify MCP server stdio/SSE/HTTP configuration",
                "Check MCP server logs for errors"
            ])
            raise
    
    def get_tool_type(self) -> str:
        """Get tool type."""
        return "mcp"


class OpenApiToolExecutionStrategy(DefaultToolExecutionStrategy):
    """Execution strategy optimized for OpenAPI/REST API tools."""
    
    def __init__(
        self,
        timeout: float = 60.0,  # API calls can take longer
        connection_timeout: float = 15.0,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    ):
        """Initialize OpenAPI strategy.
        
        Args:
            timeout: API call timeout
            connection_timeout: HTTP connection timeout
            retry_config: Retry configuration (optimized for HTTP)
            circuit_breaker_config: Circuit breaker configuration
        """
        # Default retry config for API calls
        if retry_config is None:
            retry_config = RetryConfig(
                max_attempts=3,  # APIs can have transient failures
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=1.0,
                max_delay=30.0
            )
        
        super().__init__(timeout, retry_config, circuit_breaker_config)
        self.connection_timeout = connection_timeout
    
    async def execute_tool(
        self,
        tool: Any,
        context: InvocationContext,
        yaml_context: YamlSystemContext,
        tool_config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute OpenAPI tool with specialized handling."""
        # Update context for OpenAPI tool
        api_context = yaml_context.with_tool(getattr(tool, 'name', 'unknown_api_tool'))
        api_context = api_context.add_context('tool_type', 'openapi')
        
        try:
            return await super().execute_tool(tool, context, api_context, tool_config)
        except ToolExecutionError as e:
            # Add OpenAPI-specific suggestions
            e.suggested_fixes.extend([
                "Check if API endpoint is accessible",
                "Verify API authentication credentials",
                "Check API rate limits and quotas",
                "Validate request parameters and format"
            ])
            raise
    
    def get_tool_type(self) -> str:
        """Get tool type."""
        return "openapi"


class FunctionToolExecutionStrategy(DefaultToolExecutionStrategy):
    """Execution strategy optimized for Python function tools."""
    
    def __init__(
        self,
        timeout: float = 10.0,  # Function calls should be quick
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    ):
        """Initialize function tool strategy.
        
        Args:
            timeout: Function execution timeout
            retry_config: Retry configuration (minimal for functions)
            circuit_breaker_config: Circuit breaker configuration
        """
        # Default retry config for function tools
        if retry_config is None:
            retry_config = RetryConfig(
                max_attempts=1,  # Functions should work on first try
                strategy=RetryStrategy.IMMEDIATE
            )
        
        super().__init__(timeout, retry_config, circuit_breaker_config)
    
    async def execute_tool(
        self,
        tool: Any,
        context: InvocationContext,
        yaml_context: YamlSystemContext,
        tool_config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute function tool with specialized handling."""
        # Update context for function tool
        func_context = yaml_context.with_tool(getattr(tool, '__name__', 'unknown_function'))
        func_context = func_context.add_context('tool_type', 'function')
        
        try:
            return await super().execute_tool(tool, context, func_context, tool_config)
        except ToolExecutionError as e:
            # Add function-specific suggestions
            e.suggested_fixes.extend([
                "Check function implementation for errors",
                "Verify function parameters and types",
                "Check if required dependencies are installed"
            ])
            raise
    
    def get_tool_type(self) -> str:
        """Get tool type."""
        return "function"


class ToolExecutionStrategyManager:
    """Manager for different tool execution strategies.
    
    This class manages multiple execution strategies and routes
    tool executions to the appropriate strategy based on tool type.
    """
    
    def __init__(self):
        """Initialize strategy manager."""
        self.strategies: Dict[str, ToolExecutionStrategy] = {}
        self.default_strategy: Optional[ToolExecutionStrategy] = None
    
    def register_strategy(self, tool_type: str, strategy: ToolExecutionStrategy):
        """Register a strategy for a tool type.
        
        Args:
            tool_type: Tool type identifier
            strategy: Execution strategy
        """
        self.strategies[tool_type] = strategy
        logger.debug(f"Registered {strategy.__class__.__name__} for tool type: {tool_type}")
    
    def set_default_strategy(self, strategy: ToolExecutionStrategy):
        """Set default strategy for unknown tool types.
        
        Args:
            strategy: Default execution strategy
        """
        self.default_strategy = strategy
        logger.debug(f"Set default strategy: {strategy.__class__.__name__}")
    
    def get_strategy(self, tool_type: str) -> ToolExecutionStrategy:
        """Get strategy for a tool type.
        
        Args:
            tool_type: Tool type identifier
            
        Returns:
            ToolExecutionStrategy: Appropriate strategy
            
        Raises:
            ValueError: If no strategy found and no default set
        """
        strategy = self.strategies.get(tool_type)
        if strategy:
            return strategy
        
        if self.default_strategy:
            return self.default_strategy
        
        raise ValueError(f"No execution strategy found for tool type: {tool_type}")
    
    def detect_tool_type(self, tool: Any) -> str:
        """Detect tool type from tool object.
        
        Args:
            tool: Tool object to inspect
            
        Returns:
            str: Detected tool type
        """
        # Check if tool has explicit type marker
        if hasattr(tool, 'tool_type'):
            return tool.tool_type
        
        # Check class name patterns
        class_name = tool.__class__.__name__.lower()
        if 'mcp' in class_name:
            return 'mcp'
        elif 'openapi' in class_name or 'rest' in class_name or 'api' in class_name:
            return 'openapi'
        elif callable(tool):
            return 'function'
        
        # Default fallback
        return 'function'
    
    async def execute_tool(
        self,
        tool: Any,
        context: InvocationContext,
        yaml_context: YamlSystemContext,
        tool_config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute tool using appropriate strategy.
        
        Args:
            tool: Tool to execute
            context: ADK invocation context
            yaml_context: YAML system context
            tool_config: Tool-specific configuration
            
        Returns:
            Any: Tool execution result
        """
        tool_type = self.detect_tool_type(tool)
        strategy = self.get_strategy(tool_type)
        
        return await strategy.execute_tool(tool, context, yaml_context, tool_config)