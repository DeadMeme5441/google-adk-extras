"""Workflow execution strategies for enhanced agent composition.

This module provides execution strategies for different workflow patterns including
sequential, parallel, and loop execution with enhanced capabilities like circuit
breakers, retry policies, and performance monitoring.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types

from ..errors import YamlSystemContext, YamlSystemError
from .config import WorkflowConfig, FailureHandlingMode

logger = logging.getLogger(__name__)


class WorkflowExecutionError(Exception):
    """Exception raised during workflow execution."""
    
    def __init__(
        self,
        message: str,
        step_index: Optional[int] = None,
        agent_name: Optional[str] = None,
        original_error: Optional[Exception] = None,
        execution_context: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.step_index = step_index
        self.agent_name = agent_name
        self.original_error = original_error
        self.execution_context = execution_context or {}
        super().__init__(self.message)


class WorkflowStepResult:
    """Result of executing a single workflow step."""
    
    def __init__(
        self,
        step_index: int,
        agent_name: str,
        success: bool,
        events: List[Event],
        execution_time: float,
        error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.step_index = step_index
        self.agent_name = agent_name
        self.success = success
        self.events = events
        self.execution_time = execution_time
        self.error = error
        self.context = context or {}


class WorkflowExecutionStrategy(ABC):
    """Abstract base class for workflow execution strategies."""
    
    def __init__(
        self,
        config: WorkflowConfig,
        yaml_context: Optional[YamlSystemContext] = None,
    ):
        self.config = config
        self.yaml_context = yaml_context or YamlSystemContext()
        self._performance_metrics = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_execution_time': 0.0,
            'avg_execution_time': 0.0,
            'total_steps_executed': 0,
            'total_step_failures': 0,
        }
    
    @abstractmethod
    async def execute(
        self,
        agents: List[BaseAgent],
        invocation_context: InvocationContext,
        new_message: types.Content,
        state_delta: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Event, None]:
        """Execute workflow with the given agents.
        
        Args:
            agents: List of agents to execute in workflow
            invocation_context: Invocation context for execution
            new_message: Message content to process
            state_delta: Optional state delta
            
        Yields:
            Event: Events from workflow execution
            
        Raises:
            WorkflowExecutionError: If workflow execution fails
        """
        pass
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this strategy.
        
        Returns:
            Dict containing performance metrics
        """
        return self._performance_metrics.copy()
    
    def _update_performance_metrics(
        self,
        execution_time: float,
        success: bool,
        steps_executed: int,
        step_failures: int = 0,
    ) -> None:
        """Update performance metrics.
        
        Args:
            execution_time: Total execution time
            success: Whether execution was successful
            steps_executed: Number of steps executed
            step_failures: Number of step failures
        """
        self._performance_metrics['total_executions'] += 1
        if success:
            self._performance_metrics['successful_executions'] += 1
        else:
            self._performance_metrics['failed_executions'] += 1
        
        self._performance_metrics['total_execution_time'] += execution_time
        self._performance_metrics['avg_execution_time'] = (
            self._performance_metrics['total_execution_time'] / 
            self._performance_metrics['total_executions']
        )
        
        self._performance_metrics['total_steps_executed'] += steps_executed
        self._performance_metrics['total_step_failures'] += step_failures
    
    @asynccontextmanager
    async def _execution_timeout(self, timeout: float):
        """Context manager for execution timeout.
        
        Args:
            timeout: Timeout in seconds
            
        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
        """
        try:
            async with asyncio.timeout(timeout):
                yield
        except asyncio.TimeoutError:
            logger.error(f"Workflow execution exceeded timeout of {timeout}s")
            raise WorkflowExecutionError(
                f"Workflow execution exceeded timeout of {timeout}s",
                execution_context={'timeout': timeout}
            )


class SequentialExecutionStrategy(WorkflowExecutionStrategy):
    """Strategy for sequential workflow execution with enhanced capabilities."""
    
    async def execute(
        self,
        agents: List[BaseAgent],
        invocation_context: InvocationContext,
        new_message: types.Content,
        state_delta: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Event, None]:
        """Execute agents sequentially with enhanced error handling and monitoring.
        
        Args:
            agents: List of agents to execute sequentially
            invocation_context: Invocation context for execution
            new_message: Message content to process
            state_delta: Optional state delta
            
        Yields:
            Event: Events from sequential execution
            
        Raises:
            WorkflowExecutionError: If sequential execution fails
        """
        start_time = time.time()
        executed_steps = 0
        step_failures = 0
        current_message = new_message
        
        try:
            async with self._execution_timeout(self.config.timeouts.sequential_step_timeout * len(agents)):
                for step_index, agent in enumerate(agents):
                    step_start_time = time.time()
                    step_success = False
                    
                    try:
                        # Execute single step with timeout
                        async with self._execution_timeout(self.config.timeouts.sequential_step_timeout):
                            step_events = []
                            
                            # Execute agent
                            async for event in agent.run_async(
                                invocation_context=invocation_context,
                                new_message=current_message,
                                state_delta=state_delta,
                            ):
                                step_events.append(event)
                                yield event
                            
                            # Update message for next step (use last event content if available)
                            if step_events and hasattr(step_events[-1], 'content'):
                                current_message = step_events[-1].content
                            
                            step_success = True
                            executed_steps += 1
                            
                    except Exception as e:
                        step_failures += 1
                        step_execution_time = time.time() - step_start_time
                        
                        logger.error(f"Sequential step {step_index} ({agent.name}) failed: {e}")
                        
                        # Handle failure based on configuration
                        if self.config.failure_handling == FailureHandlingMode.FAIL_FAST:
                            raise WorkflowExecutionError(
                                f"Sequential workflow failed at step {step_index} ({agent.name}): {str(e)}",
                                step_index=step_index,
                                agent_name=agent.name,
                                original_error=e,
                                execution_context={
                                    'execution_mode': 'sequential',
                                    'total_steps': len(agents),
                                    'completed_steps': executed_steps,
                                    'step_execution_time': step_execution_time,
                                }
                            )
                        elif self.config.failure_handling == FailureHandlingMode.CONTINUE_ON_FAILURE:
                            # Log and continue with next step
                            logger.warning(f"Continuing sequential workflow after step {step_index} failure")
                            continue
                        # Other failure handling modes can be implemented here
            
            # Update performance metrics
            total_execution_time = time.time() - start_time
            self._update_performance_metrics(
                execution_time=total_execution_time,
                success=(step_failures == 0),
                steps_executed=executed_steps,
                step_failures=step_failures,
            )
            
            logger.info(f"Sequential workflow completed: {executed_steps} steps, {step_failures} failures")
            
        except WorkflowExecutionError:
            # Re-raise workflow errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            total_execution_time = time.time() - start_time
            self._update_performance_metrics(
                execution_time=total_execution_time,
                success=False,
                steps_executed=executed_steps,
                step_failures=step_failures + 1,
            )
            
            raise WorkflowExecutionError(
                f"Sequential workflow execution failed: {str(e)}",
                original_error=e,
                execution_context={
                    'execution_mode': 'sequential',
                    'total_steps': len(agents),
                    'completed_steps': executed_steps,
                    'total_failures': step_failures,
                    'total_execution_time': total_execution_time,
                }
            )


class ParallelExecutionStrategy(WorkflowExecutionStrategy):
    """Strategy for parallel workflow execution with enhanced capabilities."""
    
    async def execute(
        self,
        agents: List[BaseAgent],
        invocation_context: InvocationContext,
        new_message: types.Content,
        state_delta: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Event, None]:
        """Execute agents in parallel with enhanced monitoring and error handling.
        
        Args:
            agents: List of agents to execute in parallel
            invocation_context: Invocation context for execution
            new_message: Message content to process
            state_delta: Optional state delta
            
        Yields:
            Event: Events from parallel execution
            
        Raises:
            WorkflowExecutionError: If parallel execution fails
        """
        start_time = time.time()
        executed_steps = 0
        step_failures = 0
        
        try:
            async with self._execution_timeout(self.config.timeouts.parallel_total_timeout):
                # Limit concurrent execution
                max_concurrent = min(len(agents), self.config.max_concurrent_steps)
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def execute_agent(step_index: int, agent: BaseAgent) -> WorkflowStepResult:
                    """Execute a single agent with semaphore control."""
                    async with semaphore:
                        step_start_time = time.time()
                        step_events = []
                        error = None
                        
                        try:
                            async with self._execution_timeout(self.config.timeouts.parallel_step_timeout):
                                async for event in agent.run_async(
                                    invocation_context=invocation_context,
                                    new_message=new_message,
                                    state_delta=state_delta,
                                ):
                                    step_events.append(event)
                                    
                        except Exception as e:
                            error = e
                            logger.error(f"Parallel step {step_index} ({agent.name}) failed: {e}")
                        
                        step_execution_time = time.time() - step_start_time
                        return WorkflowStepResult(
                            step_index=step_index,
                            agent_name=agent.name,
                            success=(error is None),
                            events=step_events,
                            execution_time=step_execution_time,
                            error=error,
                        )
                
                # Create tasks for all agents
                tasks = [
                    execute_agent(i, agent) 
                    for i, agent in enumerate(agents)
                ]
                
                # Execute all tasks and collect results
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results and yield events
                for result in results:
                    if isinstance(result, Exception):
                        step_failures += 1
                        if self.config.failure_handling == FailureHandlingMode.FAIL_FAST:
                            raise WorkflowExecutionError(
                                f"Parallel workflow failed: {str(result)}",
                                original_error=result,
                                execution_context={'execution_mode': 'parallel'}
                            )
                    elif isinstance(result, WorkflowStepResult):
                        executed_steps += 1
                        if not result.success:
                            step_failures += 1
                            
                        # Yield all events from this step
                        for event in result.events:
                            yield event
                        
                        if not result.success and self.config.failure_handling == FailureHandlingMode.FAIL_FAST:
                            raise WorkflowExecutionError(
                                f"Parallel workflow failed at step {result.step_index} ({result.agent_name}): {result.error}",
                                step_index=result.step_index,
                                agent_name=result.agent_name,
                                original_error=result.error,
                                execution_context={'execution_mode': 'parallel'}
                            )
            
            # Update performance metrics
            total_execution_time = time.time() - start_time
            self._update_performance_metrics(
                execution_time=total_execution_time,
                success=(step_failures == 0),
                steps_executed=executed_steps,
                step_failures=step_failures,
            )
            
            logger.info(f"Parallel workflow completed: {executed_steps} steps, {step_failures} failures")
            
        except WorkflowExecutionError:
            # Re-raise workflow errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            total_execution_time = time.time() - start_time
            self._update_performance_metrics(
                execution_time=total_execution_time,
                success=False,
                steps_executed=executed_steps,
                step_failures=step_failures + 1,
            )
            
            raise WorkflowExecutionError(
                f"Parallel workflow execution failed: {str(e)}",
                original_error=e,
                execution_context={
                    'execution_mode': 'parallel',
                    'total_steps': len(agents),
                    'completed_steps': executed_steps,
                    'total_failures': step_failures,
                    'total_execution_time': total_execution_time,
                }
            )


class LoopExecutionStrategy(WorkflowExecutionStrategy):
    """Strategy for loop workflow execution with enhanced capabilities."""
    
    async def execute(
        self,
        agents: List[BaseAgent],
        invocation_context: InvocationContext,
        new_message: types.Content,
        state_delta: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Event, None]:
        """Execute agents in loop with enhanced monitoring and error handling.
        
        Args:
            agents: List of agents to execute in loop
            invocation_context: Invocation context for execution
            new_message: Message content to process
            state_delta: Optional state delta
            
        Yields:
            Event: Events from loop execution
            
        Raises:
            WorkflowExecutionError: If loop execution fails
        """
        start_time = time.time()
        executed_steps = 0
        step_failures = 0
        current_message = new_message
        iteration = 0
        
        try:
            async with self._execution_timeout(self.config.timeouts.loop_total_timeout):
                while iteration < self.config.max_loop_iterations:
                    iteration_start_time = time.time()
                    iteration_success = True
                    
                    try:
                        # Execute all agents in the loop iteration
                        async with self._execution_timeout(self.config.timeouts.loop_iteration_timeout):
                            for step_index, agent in enumerate(agents):
                                step_events = []
                                
                                try:
                                    async for event in agent.run_async(
                                        invocation_context=invocation_context,
                                        new_message=current_message,
                                        state_delta=state_delta,
                                    ):
                                        step_events.append(event)
                                        yield event
                                    
                                    executed_steps += 1
                                    
                                    # Update message for next step
                                    if step_events and hasattr(step_events[-1], 'content'):
                                        current_message = step_events[-1].content
                                        
                                except Exception as e:
                                    step_failures += 1
                                    iteration_success = False
                                    logger.error(f"Loop iteration {iteration}, step {step_index} ({agent.name}) failed: {e}")
                                    
                                    if self.config.failure_handling == FailureHandlingMode.FAIL_FAST:
                                        raise WorkflowExecutionError(
                                            f"Loop workflow failed at iteration {iteration}, step {step_index} ({agent.name}): {str(e)}",
                                            step_index=step_index,
                                            agent_name=agent.name,
                                            original_error=e,
                                            execution_context={
                                                'execution_mode': 'loop',
                                                'iteration': iteration,
                                                'total_steps': len(agents),
                                            }
                                        )
                        
                        iteration += 1
                        
                        # Loop termination logic can be added here
                        # For now, we'll break after one successful iteration unless configured otherwise
                        if iteration_success:
                            logger.info(f"Loop iteration {iteration} completed successfully")
                            # This is a simple implementation - more sophisticated termination logic can be added
                            break
                            
                    except WorkflowExecutionError:
                        raise
                    except Exception as e:
                        step_failures += 1
                        logger.error(f"Loop iteration {iteration} failed: {e}")
                        
                        if self.config.failure_handling == FailureHandlingMode.FAIL_FAST:
                            raise WorkflowExecutionError(
                                f"Loop workflow failed at iteration {iteration}: {str(e)}",
                                original_error=e,
                                execution_context={
                                    'execution_mode': 'loop',
                                    'iteration': iteration,
                                    'total_steps': len(agents),
                                }
                            )
            
            # Update performance metrics
            total_execution_time = time.time() - start_time
            self._update_performance_metrics(
                execution_time=total_execution_time,
                success=(step_failures == 0),
                steps_executed=executed_steps,
                step_failures=step_failures,
            )
            
            logger.info(f"Loop workflow completed: {iteration} iterations, {executed_steps} steps, {step_failures} failures")
            
        except WorkflowExecutionError:
            # Re-raise workflow errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            total_execution_time = time.time() - start_time
            self._update_performance_metrics(
                execution_time=total_execution_time,
                success=False,
                steps_executed=executed_steps,
                step_failures=step_failures + 1,
            )
            
            raise WorkflowExecutionError(
                f"Loop workflow execution failed: {str(e)}",
                original_error=e,
                execution_context={
                    'execution_mode': 'loop',
                    'iterations_completed': iteration,
                    'total_steps': executed_steps,
                    'total_failures': step_failures,
                    'total_execution_time': total_execution_time,
                }
            )


class WorkflowStrategyManager:
    """Manager for workflow execution strategies."""
    
    def __init__(self):
        self._strategies: Dict[str, WorkflowExecutionStrategy] = {}
        self._default_strategy: Optional[WorkflowExecutionStrategy] = None
    
    def register_strategy(self, name: str, strategy: WorkflowExecutionStrategy) -> None:
        """Register a workflow execution strategy.
        
        Args:
            name: Strategy name
            strategy: Strategy implementation
        """
        self._strategies[name] = strategy
        logger.info(f"Registered workflow strategy: {name}")
    
    def get_strategy(self, name: str) -> Optional[WorkflowExecutionStrategy]:
        """Get a workflow execution strategy by name.
        
        Args:
            name: Strategy name
            
        Returns:
            Strategy implementation or None if not found
        """
        return self._strategies.get(name)
    
    def set_default_strategy(self, strategy: WorkflowExecutionStrategy) -> None:
        """Set the default workflow execution strategy.
        
        Args:
            strategy: Default strategy implementation
        """
        self._default_strategy = strategy
        logger.info("Set default workflow strategy")
    
    def get_default_strategy(self) -> Optional[WorkflowExecutionStrategy]:
        """Get the default workflow execution strategy.
        
        Returns:
            Default strategy implementation or None if not set
        """
        return self._default_strategy
    
    def list_strategies(self) -> List[str]:
        """List all registered strategy names.
        
        Returns:
            List of strategy names
        """
        return list(self._strategies.keys())
    
    def get_all_performance_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for all registered strategies.
        
        Returns:
            Dict mapping strategy names to their performance metrics
        """
        return {
            name: strategy.get_performance_metrics()
            for name, strategy in self._strategies.items()
        }