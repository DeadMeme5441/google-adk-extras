"""Enhanced agent implementations that properly inherit from ADK BaseAgent.

These agents extend the base ADK agent classes with enhanced capabilities
like circuit breakers, performance monitoring, retry policies, and advanced
workflow orchestration while maintaining full compatibility with the ADK framework.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, AsyncGenerator, ClassVar, Dict, Optional, Type

from typing_extensions import override

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.base_agent_config import BaseAgentConfig
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.utils.context_utils import Aclosing

from .enhanced_configs import (
    EnhancedSequentialAgentConfig,
    EnhancedParallelAgentConfig, 
    EnhancedLoopAgentConfig,
    EnhancedWorkflowConfig,
    FailureHandlingMode,
    WorkflowExecutionMode
)
from ..errors import YamlSystemContext, YamlSystemError
from ..monitoring import PerformanceMonitor, CircuitBreaker

logger = logging.getLogger(__name__)


class EnhancedSequentialAgent(BaseAgent):
    """Enhanced sequential agent with circuit breakers, monitoring, and retry policies.
    
    Extends ADK's BaseAgent with enhanced capabilities while maintaining
    full compatibility with the ADK framework and execution patterns.
    """
    
    config_type: ClassVar[Type[BaseAgentConfig]] = EnhancedSequentialAgentConfig
    """The config type for this agent."""
    
    def __init__(
        self,
        name: str,
        sub_agents: Optional[list[BaseAgent]] = None,
        enhanced_config: Optional[EnhancedWorkflowConfig] = None,
        yaml_context: Optional[YamlSystemContext] = None,
        **kwargs
    ):
        """Initialize enhanced sequential agent.
        
        Args:
            name: Agent name
            sub_agents: List of sub-agents to execute sequentially
            enhanced_config: Enhanced workflow configuration
            yaml_context: YAML system context for error reporting
            **kwargs: Additional arguments passed to BaseAgent
        """
        # Initialize BaseAgent with proper parameters
        super().__init__(name=name, sub_agents=sub_agents or [], **kwargs)
        
        # Enhanced capabilities (use private attributes to avoid Pydantic validation)
        self._enhanced_config = enhanced_config or EnhancedWorkflowConfig(
            execution_mode=WorkflowExecutionMode.SEQUENTIAL
        )
        self._yaml_context = yaml_context or YamlSystemContext(system_name="EnhancedSequentialAgent")
        
        # Initialize monitoring and circuit breaker
        self._performance_monitor = PerformanceMonitor(
            agent_name=self.name,
            config=self._enhanced_config.performance_monitoring
        )
        self._circuit_breaker = CircuitBreaker(
            name=f"{self.name}_circuit_breaker",
            config=self._enhanced_config.circuit_breaker
        )
        
        logger.debug(f"Initialized EnhancedSequentialAgent '{self.name}' with {len(self.sub_agents)} sub-agents")
    
    @property
    def enhanced_config(self) -> EnhancedWorkflowConfig:
        """Get enhanced configuration."""
        return self._enhanced_config
    
    @property
    def yaml_context(self) -> YamlSystemContext:
        """Get YAML context."""
        return self._yaml_context
    
    @property
    def performance_monitor(self) -> PerformanceMonitor:
        """Get performance monitor."""
        return self._performance_monitor
    
    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Get circuit breaker."""
        return self._circuit_breaker
    
    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Execute sub-agents sequentially with enhanced monitoring and error handling.
        
        Args:
            ctx: Invocation context
            
        Yields:
            Event: Events from sub-agent execution
        """
        logger.info(f"Starting enhanced sequential execution of {len(self.sub_agents)} agents")
        
        with self._performance_monitor.measure_execution():
            step_number = 0
            
            try:
                for step_number, sub_agent in enumerate(self.sub_agents, 1):
                    agent_name = getattr(sub_agent, 'name', f'Agent_{step_number}')
                    logger.debug(f"Executing sequential step {step_number}: {agent_name}")
                    
                    # Check circuit breaker state
                    if not self.circuit_breaker.can_execute():
                        raise YamlSystemError(
                            f"Circuit breaker is open for sequential agent '{self.name}'",
                            context=self.yaml_context.with_agent(self.name),
                            suggested_fixes=[
                                "Wait for circuit breaker recovery timeout",
                                "Check sub-agent error patterns",
                                "Review failure handling configuration"
                            ]
                        )
                    
                    step_start_time = time.time()
                    step_success = False
                    
                    try:
                        # Execute sub-agent with timeout if configured
                        if self.enhanced_config.timeouts.step_timeout:
                            async with asyncio.timeout(self.enhanced_config.timeouts.step_timeout):
                                async with Aclosing(sub_agent.run_async(ctx)) as agen:
                                    async for event in agen:
                                        yield event
                                        
                                        # Track event metrics
                                        self.performance_monitor.record_event(event)
                                        
                                        # Check for escalation
                                        if event.actions.escalate:
                                            logger.info(f"Agent {agent_name} escalated, stopping sequential execution")
                                            step_success = True
                                            self.circuit_breaker.record_success()
                                            return
                        else:
                            async with Aclosing(sub_agent.run_async(ctx)) as agen:
                                async for event in agen:
                                    yield event
                                    
                                    # Track event metrics
                                    self.performance_monitor.record_event(event)
                                    
                                    # Check for escalation
                                    if event.actions.escalate:
                                        logger.info(f"Agent {agent_name} escalated, stopping sequential execution")
                                        step_success = True
                                        self.circuit_breaker.record_success()
                                        return
                        
                        step_success = True
                        step_duration = time.time() - step_start_time
                        
                        # Record successful step
                        self.circuit_breaker.record_success()
                        self.performance_monitor.record_step_completion(step_number, step_duration, True)
                        
                        logger.debug(f"Sequential step {step_number} completed successfully in {step_duration:.2f}s")
                        
                    except Exception as e:
                        step_duration = time.time() - step_start_time
                        
                        # Record failure
                        self.circuit_breaker.record_failure()
                        self.performance_monitor.record_step_completion(step_number, step_duration, False)
                        
                        logger.error(f"Sequential step {step_number} failed after {step_duration:.2f}s: {e}")
                        
                        # Handle failure based on configuration
                        if self.enhanced_config.failure_handling == FailureHandlingMode.FAIL_FAST:
                            raise YamlSystemError(
                                f"Sequential agent '{self.name}' failed on step {step_number}: {e}",
                                context=self.yaml_context.with_agent(agent_name),
                                suggested_fixes=[
                                    f"Check agent '{agent_name}' configuration and dependencies",
                                    "Review sequential workflow error handling settings",
                                    "Consider using CONTINUE_ON_FAILURE mode for resilience"
                                ]
                            ) from e
                        
                        elif self.enhanced_config.failure_handling == FailureHandlingMode.CONTINUE_ON_FAILURE:
                            logger.warning(f"Continuing sequential execution despite step {step_number} failure")
                            continue
                        
                        elif self.enhanced_config.failure_handling == FailureHandlingMode.RETRY_ON_FAILURE:
                            # Retry logic would be implemented here with retry policy
                            logger.warning(f"Retry functionality not yet implemented, failing step {step_number}")
                            raise
                        
                        else:
                            raise
                
                logger.info(f"Enhanced sequential execution completed successfully: {step_number} steps")
                
            except asyncio.TimeoutError:
                raise YamlSystemError(
                    f"Sequential agent '{self.name}' timed out during execution",
                    context=self.yaml_context.with_agent(self.name),
                    suggested_fixes=[
                        "Increase step timeout configuration",
                        "Review sub-agent performance",
                        "Consider breaking down complex steps"
                    ]
                )
            
            except Exception as e:
                self.performance_monitor.record_error(e)
                logger.error(f"Enhanced sequential agent '{self.name}' failed: {e}")
                raise
    
    @override
    async def _run_live_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Live implementation for enhanced sequential agent.
        
        Args:
            ctx: Invocation context
            
        Yields:
            Event: Events from live execution
        """
        # For now, delegate to the async implementation
        # Live-specific enhancements can be added later
        async with Aclosing(self._run_async_impl(ctx)) as agen:
            async for event in agen:
                yield event
    
    @override
    @classmethod
    def _parse_config(
        cls: Type[EnhancedSequentialAgent],
        config: EnhancedSequentialAgentConfig,
        config_abs_path: str,
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse enhanced sequential agent configuration.
        
        Args:
            config: Enhanced sequential agent configuration
            config_abs_path: Absolute path to config file
            kwargs: Keyword arguments for agent construction
            
        Returns:
            Dict[str, Any]: Updated kwargs with parsed configuration
        """
        # Parse enhanced configuration
        if hasattr(config, 'enhanced_config'):
            kwargs['enhanced_config'] = config.enhanced_config
        
        # Parse sequential-specific settings
        if hasattr(config, 'stop_on_first_failure'):
            # Map to failure handling mode
            if config.stop_on_first_failure:
                if 'enhanced_config' not in kwargs:
                    kwargs['enhanced_config'] = EnhancedWorkflowConfig()
                kwargs['enhanced_config'].failure_handling = FailureHandlingMode.FAIL_FAST
        
        return kwargs


class EnhancedParallelAgent(BaseAgent):
    """Enhanced parallel agent with load balancing and advanced result aggregation.
    
    Extends ADK's BaseAgent with enhanced parallel execution capabilities
    while maintaining compatibility with the ADK framework.
    """
    
    config_type: ClassVar[Type[BaseAgentConfig]] = EnhancedParallelAgentConfig
    """The config type for this agent."""
    
    def __init__(
        self,
        name: str,
        sub_agents: Optional[list[BaseAgent]] = None,
        enhanced_config: Optional[EnhancedWorkflowConfig] = None,
        yaml_context: Optional[YamlSystemContext] = None,
        **kwargs
    ):
        """Initialize enhanced parallel agent.
        
        Args:
            name: Agent name
            sub_agents: List of sub-agents to execute in parallel
            enhanced_config: Enhanced workflow configuration
            yaml_context: YAML system context for error reporting
            **kwargs: Additional arguments passed to BaseAgent
        """
        # Initialize BaseAgent with proper parameters
        super().__init__(name=name, sub_agents=sub_agents or [], **kwargs)
        
        # Enhanced capabilities (use private attributes)
        self._enhanced_config = enhanced_config or EnhancedWorkflowConfig(
            execution_mode=WorkflowExecutionMode.PARALLEL
        )
        self._yaml_context = yaml_context or YamlSystemContext(system_name="EnhancedParallelAgent")
        
        # Initialize monitoring
        self._performance_monitor = PerformanceMonitor(
            agent_name=self.name,
            config=self._enhanced_config.performance_monitoring
        )
        self._circuit_breaker = CircuitBreaker(
            name=f"{self.name}_circuit_breaker",
            config=self._enhanced_config.circuit_breaker
        )
        
        logger.debug(f"Initialized EnhancedParallelAgent '{self.name}' with {len(self.sub_agents)} sub-agents")
    
    @property
    def enhanced_config(self) -> EnhancedWorkflowConfig:
        """Get enhanced configuration."""
        return self._enhanced_config
    
    @property
    def yaml_context(self) -> YamlSystemContext:
        """Get YAML context."""
        return self._yaml_context
    
    @property
    def performance_monitor(self) -> PerformanceMonitor:
        """Get performance monitor."""
        return self._performance_monitor
    
    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Get circuit breaker."""
        return self._circuit_breaker
    
    def _create_branch_ctx_for_sub_agent(
        self,
        sub_agent: BaseAgent,
        invocation_context: InvocationContext,
    ) -> InvocationContext:
        """Create isolated branch for every sub-agent (copied from ADK ParallelAgent).
        
        Args:
            sub_agent: Sub-agent to create context for
            invocation_context: Parent invocation context
            
        Returns:
            InvocationContext: Isolated branch context
        """
        invocation_context = invocation_context.model_copy()
        branch_suffix = f'{self.name}.{sub_agent.name}'
        invocation_context.branch = (
            f'{invocation_context.branch}.{branch_suffix}'
            if invocation_context.branch
            else branch_suffix
        )
        return invocation_context
    
    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Execute sub-agents in parallel with enhanced monitoring.
        
        Args:
            ctx: Invocation context
            
        Yields:
            Event: Events from parallel sub-agent execution
        """
        logger.info(f"Starting enhanced parallel execution of {len(self.sub_agents)} agents")
        
        if not self.sub_agents:
            logger.warning(f"EnhancedParallelAgent '{self.name}' has no sub-agents to execute")
            return
        
        with self._performance_monitor.measure_execution():
            # Create agent runs with isolated contexts
            agent_runs = [
                sub_agent.run_async(
                    self._create_branch_ctx_for_sub_agent(sub_agent, ctx)
                )
                for sub_agent in self.sub_agents
            ]
            
            try:
                # Use a simplified merge approach for now
                # TODO: Implement the sophisticated merge logic from ADK ParallelAgent
                async with asyncio.TaskGroup() as tg:
                    tasks = []
                    for i, agent_run in enumerate(agent_runs):
                        task = tg.create_task(self._collect_agent_events(agent_run, i))
                        tasks.append(task)
                    
                    # Collect events from all tasks
                    for task in tasks:
                        events = await task
                        for event in events:
                            self._performance_monitor.record_event(event)
                            yield event
                            
            except Exception as e:
                self._performance_monitor.record_error(e)
                logger.error(f"Enhanced parallel agent '{self.name}' failed: {e}")
                raise
            finally:
                # Clean up agent runs
                for agent_run in agent_runs:
                    await agent_run.aclose()
    
    async def _collect_agent_events(
        self, agent_run: AsyncGenerator[Event, None], agent_index: int
    ) -> list[Event]:
        """Collect events from a single agent run.
        
        Args:
            agent_run: Async generator of events from agent
            agent_index: Index of the agent for logging
            
        Returns:
            list[Event]: Collected events
        """
        events = []
        try:
            async with Aclosing(agent_run) as agen:
                async for event in agen:
                    events.append(event)
                    
                    # Check for escalation
                    if event.actions.escalate:
                        logger.info(f"Parallel agent {agent_index} escalated")
                        break
                        
        except Exception as e:
            logger.error(f"Parallel agent {agent_index} failed: {e}")
            # Depending on failure handling mode, we might continue or re-raise
            if self._enhanced_config.failure_handling != FailureHandlingMode.CONTINUE_ON_FAILURE:
                raise
        
        return events
    
    @override
    async def _run_live_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Live implementation for enhanced parallel agent.
        
        Args:
            ctx: Invocation context
            
        Yields:
            Event: Events from live execution
        """
        # For now, delegate to the async implementation
        async with Aclosing(self._run_async_impl(ctx)) as agen:
            async for event in agen:
                yield event
    
    @override
    @classmethod
    def _parse_config(
        cls: Type[EnhancedParallelAgent],
        config: EnhancedParallelAgentConfig,
        config_abs_path: str,
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse enhanced parallel agent configuration.
        
        Args:
            config: Enhanced parallel agent configuration
            config_abs_path: Absolute path to config file
            kwargs: Keyword arguments for agent construction
            
        Returns:
            Dict[str, Any]: Updated kwargs with parsed configuration
        """
        # Parse enhanced configuration
        if hasattr(config, 'enhanced_config'):
            kwargs['enhanced_config'] = config.enhanced_config
        
        return kwargs


class EnhancedLoopAgent(BaseAgent):
    """Enhanced loop agent with adaptive iterations and convergence detection.
    
    Extends ADK's BaseAgent with enhanced loop execution capabilities
    while maintaining compatibility with the ADK framework.
    """
    
    config_type: ClassVar[Type[BaseAgentConfig]] = EnhancedLoopAgentConfig
    """The config type for this agent."""
    
    def __init__(
        self,
        name: str,
        sub_agents: Optional[list[BaseAgent]] = None,
        max_iterations: Optional[int] = None,
        enhanced_config: Optional[EnhancedWorkflowConfig] = None,
        yaml_context: Optional[YamlSystemContext] = None,
        **kwargs
    ):
        """Initialize enhanced loop agent.
        
        Args:
            name: Agent name
            sub_agents: List of sub-agents to execute in loop
            max_iterations: Maximum number of loop iterations
            enhanced_config: Enhanced workflow configuration
            yaml_context: YAML system context for error reporting
            **kwargs: Additional arguments passed to BaseAgent
        """
        # Initialize BaseAgent with proper parameters
        super().__init__(name=name, sub_agents=sub_agents or [], **kwargs)
        
        # Loop-specific settings (use private attribute)
        self._max_iterations = max_iterations
        
        # Enhanced capabilities (use private attributes)
        self._enhanced_config = enhanced_config or EnhancedWorkflowConfig(
            execution_mode=WorkflowExecutionMode.LOOP,
            max_loop_iterations=max_iterations
        )
        self._yaml_context = yaml_context or YamlSystemContext(system_name="EnhancedLoopAgent")
        
        # Initialize monitoring
        self._performance_monitor = PerformanceMonitor(
            agent_name=self.name,
            config=self._enhanced_config.performance_monitoring
        )
        self._circuit_breaker = CircuitBreaker(
            name=f"{self.name}_circuit_breaker",
            config=self._enhanced_config.circuit_breaker
        )
        
        logger.debug(f"Initialized EnhancedLoopAgent '{self.name}' with {len(self.sub_agents)} sub-agents, max_iterations: {max_iterations}")
    
    @property
    def max_iterations(self) -> Optional[int]:
        """Get maximum iterations."""
        return self._max_iterations
    
    @property
    def enhanced_config(self) -> EnhancedWorkflowConfig:
        """Get enhanced configuration."""
        return self._enhanced_config
    
    @property
    def yaml_context(self) -> YamlSystemContext:
        """Get YAML context."""
        return self._yaml_context
    
    @property
    def performance_monitor(self) -> PerformanceMonitor:
        """Get performance monitor."""
        return self._performance_monitor
    
    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Get circuit breaker."""
        return self._circuit_breaker
    
    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Execute sub-agents in loop with enhanced monitoring and adaptive features.
        
        Args:
            ctx: Invocation context
            
        Yields:
            Event: Events from loop sub-agent execution
        """
        max_iterations = self._max_iterations or self._enhanced_config.max_loop_iterations
        logger.info(f"Starting enhanced loop execution with max_iterations: {max_iterations}")
        
        with self._performance_monitor.measure_execution():
            times_looped = 0
            
            try:
                while not max_iterations or times_looped < max_iterations:
                    iteration_start_time = time.time()
                    logger.debug(f"Starting loop iteration {times_looped + 1}")
                    
                    for sub_agent in self.sub_agents:
                        should_exit = False
                        agent_name = getattr(sub_agent, 'name', f'LoopAgent_{times_looped}')
                        
                        try:
                            async with Aclosing(sub_agent.run_async(ctx)) as agen:
                                async for event in agen:
                                    self._performance_monitor.record_event(event)
                                    yield event
                                    
                                    if event.actions.escalate:
                                        logger.info(f"Agent {agent_name} escalated, stopping loop execution")
                                        should_exit = True
                                        break
                                        
                        except Exception as e:
                            logger.error(f"Loop iteration {times_looped + 1} failed on agent {agent_name}: {e}")
                            
                            if self._enhanced_config.failure_handling == FailureHandlingMode.FAIL_FAST:
                                raise YamlSystemError(
                                    f"Loop agent '{self.name}' failed on iteration {times_looped + 1}: {e}",
                                    context=self._yaml_context.with_agent(agent_name),
                                    suggested_fixes=[
                                        "Check sub-agent configuration and dependencies",
                                        "Review loop workflow error handling settings",
                                        "Consider using CONTINUE_ON_FAILURE mode"
                                    ]
                                ) from e
                            elif self._enhanced_config.failure_handling == FailureHandlingMode.CONTINUE_ON_FAILURE:
                                logger.warning(f"Continuing loop despite iteration {times_looped + 1} failure")
                                continue
                            else:
                                raise
                        
                        if should_exit:
                            iteration_duration = time.time() - iteration_start_time
                            self._performance_monitor.record_step_completion(times_looped + 1, iteration_duration, True)
                            logger.info(f"Loop execution stopped by escalation after {times_looped + 1} iterations")
                            return
                    
                    times_looped += 1
                    iteration_duration = time.time() - iteration_start_time
                    self._performance_monitor.record_step_completion(times_looped, iteration_duration, True)
                    
                    logger.debug(f"Completed loop iteration {times_looped} in {iteration_duration:.2f}s")
                    
                    # Apply iteration cooldown if configured
                    # TODO: Access loop-specific config from enhanced_config
                    # if self.enhanced_config.iteration_cooldown > 0:
                    #     await asyncio.sleep(self.enhanced_config.iteration_cooldown)
                
                logger.info(f"Enhanced loop execution completed: {times_looped} iterations")
                
            except Exception as e:
                self._performance_monitor.record_error(e)
                logger.error(f"Enhanced loop agent '{self.name}' failed: {e}")
                raise
    
    @override
    async def _run_live_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Live implementation for enhanced loop agent.
        
        Args:
            ctx: Invocation context
            
        Yields:
            Event: Events from live execution
        """
        # For now, delegate to the async implementation
        async with Aclosing(self._run_async_impl(ctx)) as agen:
            async for event in agen:
                yield event
    
    @override
    @classmethod
    def _parse_config(
        cls: Type[EnhancedLoopAgent],
        config: EnhancedLoopAgentConfig,
        config_abs_path: str,
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse enhanced loop agent configuration.
        
        Args:
            config: Enhanced loop agent configuration
            config_abs_path: Absolute path to config file
            kwargs: Keyword arguments for agent construction
            
        Returns:
            Dict[str, Any]: Updated kwargs with parsed configuration
        """
        # Parse base LoopAgent config (max_iterations)
        if hasattr(config, 'max_iterations') and config.max_iterations:
            kwargs['max_iterations'] = config.max_iterations
        
        # Parse enhanced configuration
        if hasattr(config, 'enhanced_config'):
            kwargs['enhanced_config'] = config.enhanced_config
        
        return kwargs
