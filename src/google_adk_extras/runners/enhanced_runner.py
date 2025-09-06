"""Enhanced ADK Runner with YAML system support.

This module provides the EnhancedRunner class which extends Google ADK's
Runner with advanced features for YAML-driven agent systems.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.run_config import RunConfig
from google.adk.artifacts.base_artifact_service import BaseArtifactService
from google.adk.auth.credential_service.base_credential_service import BaseCredentialService
from google.adk.events.event import Event
from google.adk.memory.base_memory_service import BaseMemoryService
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.genai import types

from .config import EnhancedRunConfig
from .errors import YamlSystemContext, YamlSystemError, ToolExecutionError
from .strategies import (
    DefaultToolExecutionStrategy,
    FunctionToolExecutionStrategy,
    McpToolExecutionStrategy,
    OpenApiToolExecutionStrategy,
    ToolExecutionStrategyManager,
)

logger = logging.getLogger(__name__)


class EnhancedRunner(Runner):
    """Enhanced ADK Runner with YAML system support.
    
    This runner extends Google ADK's Runner with advanced features including:
    - YAML-driven configuration through EnhancedRunConfig
    - Rich error handling with YAML system context
    - Configurable tool execution strategies 
    - Support for agent and tool registries
    - Performance monitoring and debugging capabilities
    
    The EnhancedRunner is designed as a drop-in replacement for ADK's Runner
    while providing significantly enhanced capabilities for YAML-driven systems.
    
    Examples:
        Basic usage (drop-in replacement):
        ```python
        runner = EnhancedRunner(
            app_name="my-system",
            agent=root_agent,
            session_service=session_service,
            artifact_service=artifact_service,
            memory_service=memory_service
        )
        ```
        
        With enhanced configuration:
        ```python
        enhanced_config = EnhancedRunConfig.from_yaml_dict({
            'max_llm_calls': 200,
            'tool_timeouts': {'mcp_tools': 30.0},
            'debug': {'enabled': True}
        })
        
        runner = EnhancedRunner(
            app_name="yaml-system",
            agent=root_agent,
            session_service=session_service,
            enhanced_config=enhanced_config,
            yaml_context=YamlSystemContext(
                system_name="my-system",
                config_path="/path/to/config.yaml"
            )
        )
        ```
        
        With custom tool strategies:
        ```python
        strategy_manager = ToolExecutionStrategyManager()
        strategy_manager.register_strategy('mcp', McpToolExecutionStrategy(timeout=45.0))
        
        runner = EnhancedRunner(
            app_name="advanced-system",
            agent=root_agent,
            session_service=session_service,
            enhanced_config=enhanced_config,
            tool_strategy_manager=strategy_manager
        )
        ```
    """
    
    def __init__(
        self,
        *,
        app_name: str,
        agent: BaseAgent,
        plugins: Optional[List[BasePlugin]] = None,
        artifact_service: Optional[BaseArtifactService] = None,
        session_service: BaseSessionService,
        memory_service: Optional[BaseMemoryService] = None,
        credential_service: Optional[BaseCredentialService] = None,
        # Enhanced features
        enhanced_config: Optional[EnhancedRunConfig] = None,
        yaml_context: Optional[YamlSystemContext] = None,
        tool_strategy_manager: Optional[ToolExecutionStrategyManager] = None,
        # Registry support (for Phase 2)
        tool_registry: Optional[Any] = None,
        agent_registry: Optional[Any] = None,
    ):
        """Initialize EnhancedRunner.
        
        Args:
            app_name: Application name
            agent: Root agent to run
            plugins: List of plugins
            artifact_service: Artifact service
            session_service: Session service
            memory_service: Memory service
            credential_service: Credential service
            enhanced_config: Enhanced configuration (optional)
            yaml_context: YAML system context (optional)
            tool_strategy_manager: Tool execution strategy manager (optional)
            tool_registry: Tool registry (for Phase 2)
            agent_registry: Agent registry (for Phase 2)
        """
        # Initialize base Runner with the base RunConfig
        if enhanced_config:
            base_config = enhanced_config.to_base_run_config()
        else:
            base_config = RunConfig()
            enhanced_config = EnhancedRunConfig(base_config=base_config)
        
        # Store enhanced features before calling super().__init__
        self.enhanced_config = enhanced_config
        self.yaml_context = yaml_context or YamlSystemContext(system_name=app_name)
        self.tool_registry = tool_registry
        self.agent_registry = agent_registry
        
        # Initialize tool execution strategy manager
        if tool_strategy_manager:
            self.tool_strategy_manager = tool_strategy_manager
        else:
            self.tool_strategy_manager = self._create_default_strategy_manager()
        
        # Performance tracking
        self._performance_metrics = {
            'total_invocations': 0,
            'total_tool_executions': 0,
            'avg_invocation_time': 0.0,
            'avg_tool_execution_time': 0.0,
            'error_count': 0,
        }
        
        # Initialize base Runner
        super().__init__(
            app_name=app_name,
            agent=agent,
            plugins=plugins,
            artifact_service=artifact_service,
            session_service=session_service,
            memory_service=memory_service,
            credential_service=credential_service,
        )
        
        logger.info(
            f"Initialized EnhancedRunner '{app_name}' with system '{self.yaml_context.system_name}'"
        )
    
    def _create_default_strategy_manager(self) -> ToolExecutionStrategyManager:
        """Create default tool execution strategy manager.
        
        Returns:
            ToolExecutionStrategyManager: Configured strategy manager
        """
        manager = ToolExecutionStrategyManager()
        
        # Create strategies with enhanced config timeouts
        default_strategy = DefaultToolExecutionStrategy(
            timeout=self.enhanced_config.tool_timeouts.function_tools,
            retry_config=self.enhanced_config.get_retry_config('default')
        )
        
        mcp_strategy = McpToolExecutionStrategy(
            timeout=self.enhanced_config.tool_timeouts.mcp_tools,
            connection_timeout=self.enhanced_config.tool_timeouts.mcp_connection_timeout,
            retry_config=self.enhanced_config.get_retry_config('mcp_tools')
        )
        
        openapi_strategy = OpenApiToolExecutionStrategy(
            timeout=self.enhanced_config.tool_timeouts.openapi_tools,
            connection_timeout=self.enhanced_config.tool_timeouts.openapi_connection_timeout,
            retry_config=self.enhanced_config.get_retry_config('openapi_tools')
        )
        
        function_strategy = FunctionToolExecutionStrategy(
            timeout=self.enhanced_config.tool_timeouts.function_tools,
            retry_config=self.enhanced_config.get_retry_config('default')
        )
        
        # Register strategies
        manager.register_strategy('mcp', mcp_strategy)
        manager.register_strategy('openapi', openapi_strategy)
        manager.register_strategy('function', function_strategy)
        manager.set_default_strategy(default_strategy)
        
        return manager
    
    async def run_async(
        self,
        *,
        user_id: str,
        session_id: str,
        new_message: types.Content,
        state_delta: Optional[Dict[str, Any]] = None,
        run_config: Optional[RunConfig] = None,
    ) -> AsyncGenerator[Event, None]:
        """Enhanced run_async with YAML system context and error handling.
        
        This method wraps ADK's run_async with enhanced error handling,
        performance monitoring, and YAML system context.
        
        Args:
            user_id: User ID
            session_id: Session ID  
            new_message: New message content
            state_delta: Optional state delta
            run_config: Optional run config (will be merged with enhanced config)
            
        Yields:
            Event: Events from agent execution
            
        Raises:
            YamlSystemError: Enhanced error with YAML system context
        """
        start_time = time.time()
        invocation_context = None
        
        try:
            # Update YAML context with invocation details
            current_context = self.yaml_context.with_invocation(
                invocation_id=f"inv_{int(time.time() * 1000)}",
                session_id=session_id,
                user_id=user_id
            )
            
            # Use enhanced run config if no override provided
            if run_config is None:
                run_config = self.enhanced_config.to_base_run_config()
            
            # Update performance metrics
            self._performance_metrics['total_invocations'] += 1
            
            # Call base runner with enhanced error handling
            async with self._execution_context(current_context) as exec_context:
                async for event in super().run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=new_message,
                    state_delta=state_delta,
                    run_config=run_config,
                ):
                    # Update context if agent changes
                    if hasattr(event, 'author') and event.author:
                        exec_context.current_agent = event.author
                    
                    yield event
            
            # Update success metrics
            execution_time = time.time() - start_time
            self._update_performance_metrics(execution_time, success=True)
            
        except Exception as e:
            # Update error metrics
            execution_time = time.time() - start_time
            self._update_performance_metrics(execution_time, success=False)
            
            # Wrap with enhanced error context
            if not isinstance(e, YamlSystemError):
                enhanced_error = YamlSystemError(
                    f"Enhanced runner execution failed: {str(e)}",
                    context=current_context if 'current_context' in locals() else self.yaml_context,
                    original_error=e,
                    suggested_fixes=[
                        "Check YAML system configuration",
                        "Verify agent and tool configurations",
                        "Check service connectivity"
                    ]
                )
                logger.error(f"Enhanced runner error: {enhanced_error}")
                raise enhanced_error
            else:
                # Re-raise YAML system errors as-is
                raise
    
    @asynccontextmanager
    async def _execution_context(self, yaml_context: YamlSystemContext):
        """Async context manager for enhanced execution.
        
        Args:
            yaml_context: YAML system context
            
        Yields:
            YamlSystemContext: Current execution context
        """
        class ExecutionContext:
            def __init__(self, context: YamlSystemContext):
                self.context = context
                self.current_agent = context.current_agent
                self.current_tool = context.current_tool
        
        exec_context = ExecutionContext(yaml_context)
        
        try:
            if self.enhanced_config.debug_config.enabled:
                logger.info(f"Starting enhanced execution: {yaml_context.get_location_string()}")
            
            yield exec_context
            
        finally:
            if self.enhanced_config.debug_config.enabled:
                logger.info(f"Completed enhanced execution: {yaml_context.get_location_string()}")
    
    def _update_performance_metrics(self, execution_time: float, success: bool):
        """Update performance metrics.
        
        Note: This method updates metrics for a completed execution.
        total_invocations should be managed separately.
        
        Args:
            execution_time: Execution time in seconds
            success: Whether execution was successful
        """
        metrics = self._performance_metrics
        
        # Update average invocation time using running average
        total_invocations = metrics['total_invocations']
        current_avg = metrics['avg_invocation_time']
        current_total_time = current_avg * (total_invocations - 1) if total_invocations > 0 else 0.0
        
        new_total_time = current_total_time + execution_time
        metrics['avg_invocation_time'] = new_total_time / max(1, total_invocations)
        
        # Update error count
        if not success:
            metrics['error_count'] += 1
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics.
        
        Returns:
            Dict[str, Any]: Performance metrics
        """
        metrics = self._performance_metrics.copy()
        
        # Calculate derived metrics
        if metrics['total_invocations'] > 0:
            metrics['error_rate'] = metrics['error_count'] / metrics['total_invocations']
            metrics['success_rate'] = 1.0 - metrics['error_rate']
        else:
            metrics['error_rate'] = 0.0
            metrics['success_rate'] = 0.0
        
        return metrics
    
    def reset_performance_metrics(self):
        """Reset performance metrics."""
        self._performance_metrics = {
            'total_invocations': 0,
            'total_tool_executions': 0,
            'avg_invocation_time': 0.0,
            'avg_tool_execution_time': 0.0,
            'error_count': 0,
        }
        logger.info("Reset performance metrics")
    
    def update_yaml_context(self, context: YamlSystemContext):
        """Update the YAML system context.
        
        Args:
            context: New YAML system context
        """
        self.yaml_context = context
        logger.debug(f"Updated YAML context: {context.get_location_string()}")
    
    def update_enhanced_config(self, config: EnhancedRunConfig):
        """Update the enhanced configuration.
        
        Args:
            config: New enhanced configuration
        """
        self.enhanced_config = config
        
        # Recreate strategy manager with new config
        self.tool_strategy_manager = self._create_default_strategy_manager()
        
        logger.info("Updated enhanced configuration and recreated tool strategies")
    
    def merge_config_from_yaml(self, yaml_config: Dict[str, Any]):
        """Merge additional YAML configuration.
        
        Args:
            yaml_config: YAML configuration to merge
        """
        merged_config = self.enhanced_config.merge_with_yaml(yaml_config)
        self.update_enhanced_config(merged_config)
    
    # Tool execution enhancement (will be used in future phases)
    async def _execute_tool_enhanced(
        self,
        tool: Any,
        context: InvocationContext,
        tool_config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute tool with enhanced strategy.
        
        This method will be integrated with ADK's tool execution in future phases.
        
        Args:
            tool: Tool to execute
            context: Invocation context
            tool_config: Tool-specific configuration
            
        Returns:
            Any: Tool execution result
        """
        start_time = time.time()
        
        try:
            # Update YAML context for tool execution
            tool_name = getattr(tool, 'name', getattr(tool, '__name__', 'unknown_tool'))
            tool_context = self.yaml_context.with_tool(tool_name)
            
            # Execute with appropriate strategy
            result = await self.tool_strategy_manager.execute_tool(
                tool, context, tool_context, tool_config
            )
            
            # Update metrics
            execution_time = time.time() - start_time
            self._update_tool_metrics(execution_time, success=True)
            
            return result
            
        except Exception as e:
            # Update error metrics
            execution_time = time.time() - start_time
            self._update_tool_metrics(execution_time, success=False)
            
            # Re-raise tool execution errors
            if isinstance(e, ToolExecutionError):
                raise
            else:
                # Wrap other errors
                raise ToolExecutionError(
                    f"Unexpected tool execution error: {str(e)}",
                    context=self.yaml_context.with_tool(
                        getattr(tool, 'name', 'unknown_tool')
                    ),
                    original_error=e
                )
    
    def _update_tool_metrics(self, execution_time: float, success: bool):
        """Update tool execution metrics.
        
        Args:
            execution_time: Execution time in seconds
            success: Whether execution was successful
        """
        metrics = self._performance_metrics
        
        # Update tool execution count and average time
        metrics['total_tool_executions'] += 1
        current_avg = metrics['avg_tool_execution_time']
        total_executions = metrics['total_tool_executions']
        
        metrics['avg_tool_execution_time'] = (
            (current_avg * (total_executions - 1) + execution_time) / total_executions
        )
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get comprehensive debug information.
        
        Returns:
            Dict[str, Any]: Debug information
        """
        return {
            'runner_type': self.__class__.__name__,
            'app_name': self.app_name,
            'yaml_context': {
                'system_name': self.yaml_context.system_name,
                'config_path': str(self.yaml_context.config_path) if self.yaml_context.config_path else None,
                'current_agent': self.yaml_context.current_agent,
                'current_tool': self.yaml_context.current_tool,
            },
            'enhanced_config': {
                'debug_enabled': self.enhanced_config.debug_config.enabled,
                'tool_registry_enabled': self.enhanced_config.enable_tool_registry,
                'agent_registry_enabled': self.enhanced_config.enable_agent_registry,
                'circuit_breaker_enabled': self.enhanced_config.enable_circuit_breaker,
                'max_concurrent_tools': self.enhanced_config.max_concurrent_tools,
            },
            'performance_metrics': self.get_performance_metrics(),
            'tool_strategies': list(self.tool_strategy_manager.strategies.keys()),
            'registries': {
                'tool_registry': self.tool_registry is not None,
                'agent_registry': self.agent_registry is not None,
            }
        }
    
    def __repr__(self) -> str:
        """String representation of enhanced runner."""
        return (
            f"EnhancedRunner(app_name='{self.app_name}', "
            f"system='{self.yaml_context.system_name}', "
            f"agent='{self.agent.name if hasattr(self.agent, 'name') else 'unknown'}', "
            f"invocations={self._performance_metrics['total_invocations']})"
        )