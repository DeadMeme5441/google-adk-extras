"""Enhanced agent composition classes.

This module provides enhanced agent composition classes that extend Google ADK's
composition agents with advanced capabilities including circuit breakers, 
performance monitoring, retry policies, and workflow orchestration.
"""

import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.events.event import Event
from google.genai import types

from ..errors import YamlSystemContext, YamlSystemError
from .config import WorkflowConfig, WorkflowExecutionMode
from .strategies import (
    LoopExecutionStrategy,
    ParallelExecutionStrategy,
    SequentialExecutionStrategy,
    WorkflowExecutionError,
    WorkflowStrategyManager,
)

logger = logging.getLogger(__name__)


class EnhancedWorkflowAgent(BaseAgent):
    """Base class for enhanced workflow agents with monitoring and resilience."""
    
    def __init__(
        self,
        *,
        name: str,
        sub_agents: List[BaseAgent],
        workflow_config: Optional[WorkflowConfig] = None,
        yaml_context: Optional[YamlSystemContext] = None,
        strategy_manager: Optional[WorkflowStrategyManager] = None,
        **kwargs
    ):
        """Initialize enhanced workflow agent.
        
        Args:
            name: Agent name
            sub_agents: List of sub-agents to orchestrate
            workflow_config: Configuration for workflow execution
            yaml_context: YAML system context for error handling
            strategy_manager: Workflow strategy manager
            **kwargs: Additional arguments passed to BaseAgent
        """
        super().__init__(name=name, **kwargs)
        
        self.sub_agents = sub_agents
        self.workflow_config = workflow_config or WorkflowConfig()
        self.yaml_context = yaml_context or YamlSystemContext(agent_name=name)
        self.strategy_manager = strategy_manager or self._create_default_strategy_manager()
        
        # Performance metrics
        self._performance_metrics = {
            'total_invocations': 0,
            'successful_invocations': 0,
            'failed_invocations': 0,
            'total_execution_time': 0.0,
            'avg_execution_time': 0.0,
            'total_sub_agent_executions': 0,
            'sub_agent_failures': 0,
        }
        
        # Circuit breaker state
        self._circuit_breaker_state = {
            'state': 'closed',  # closed, open, half_open
            'failure_count': 0,
            'last_failure_time': 0.0,
            'success_count': 0,
        }
        
        logger.info(f"Initialized EnhancedWorkflowAgent '{name}' with {len(sub_agents)} sub-agents")
    
    def _create_default_strategy_manager(self) -> WorkflowStrategyManager:
        """Create default workflow strategy manager.
        
        Returns:
            WorkflowStrategyManager: Configured strategy manager
        """
        manager = WorkflowStrategyManager()
        
        # Create strategies with workflow configuration
        sequential_strategy = SequentialExecutionStrategy(
            config=self.workflow_config,
            yaml_context=self.yaml_context,
        )
        
        parallel_strategy = ParallelExecutionStrategy(
            config=self.workflow_config,
            yaml_context=self.yaml_context,
        )
        
        loop_strategy = LoopExecutionStrategy(
            config=self.workflow_config,
            yaml_context=self.yaml_context,
        )
        
        # Register strategies
        manager.register_strategy('sequential', sequential_strategy)
        manager.register_strategy('parallel', parallel_strategy)
        manager.register_strategy('loop', loop_strategy)
        manager.set_default_strategy(sequential_strategy)
        
        return manager
    
    async def run_async(
        self,
        *,
        invocation_context: InvocationContext,
        new_message: types.Content,
        state_delta: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Event, None]:
        """Execute workflow with enhanced monitoring and error handling.
        
        Args:
            invocation_context: Invocation context for execution
            new_message: Message content to process
            state_delta: Optional state delta
            
        Yields:
            Event: Events from workflow execution
            
        Raises:
            YamlSystemError: Enhanced error with YAML system context
        """
        start_time = time.time()
        
        # Check circuit breaker state
        if self._circuit_breaker_state['state'] == 'open':
            if (time.time() - self._circuit_breaker_state['last_failure_time']) < \
               self.workflow_config.circuit_breaker.workflow_circuit_breaker.recovery_timeout:
                raise YamlSystemError(
                    f"Workflow agent '{self.name}' circuit breaker is OPEN",
                    context=self.yaml_context,
                    suggested_fixes=[
                        f"Wait {self.workflow_config.circuit_breaker.workflow_circuit_breaker.recovery_timeout}s for circuit recovery",
                        "Check workflow configuration and sub-agent health",
                        "Reduce load or fix underlying issues"
                    ]
                )
            else:
                # Transition to half-open for testing
                self._circuit_breaker_state['state'] = 'half_open'
                self._circuit_breaker_state['success_count'] = 0
        
        try:
            # Update YAML context with workflow details
            current_context = self.yaml_context.with_agent(
                agent_name=self.name,
                tool_name=f"workflow_{self.workflow_config.execution_mode.value}"
            )
            
            # Get execution strategy
            strategy = self._get_execution_strategy()
            
            # Update performance metrics
            self._performance_metrics['total_invocations'] += 1
            
            # Execute workflow
            sub_agent_count = 0
            async for event in strategy.execute(
                agents=self.sub_agents,
                invocation_context=invocation_context,
                new_message=new_message,
                state_delta=state_delta,
            ):
                sub_agent_count += 1
                yield event
            
            # Update success metrics
            execution_time = time.time() - start_time
            self._update_performance_metrics(execution_time, success=True, sub_agent_executions=sub_agent_count)
            self._update_circuit_breaker_success()
            
            logger.info(f"Workflow agent '{self.name}' completed successfully in {execution_time:.2f}s")
            
        except WorkflowExecutionError as e:
            # Handle workflow-specific errors
            execution_time = time.time() - start_time
            self._update_performance_metrics(execution_time, success=False)
            self._update_circuit_breaker_failure()
            
            # Convert to YamlSystemError
            enhanced_error = YamlSystemError(
                f"Workflow agent '{self.name}' execution failed: {e.message}",
                context=current_context if 'current_context' in locals() else self.yaml_context,
                original_error=e,
                suggested_fixes=[
                    "Check sub-agent configurations",
                    "Verify workflow execution strategy",
                    "Review failure handling mode",
                    "Check timeout and retry configurations"
                ]
            )
            
            logger.error(f"Workflow agent error: {enhanced_error}")
            raise enhanced_error
            
        except Exception as e:
            # Handle unexpected errors
            execution_time = time.time() - start_time
            self._update_performance_metrics(execution_time, success=False)
            self._update_circuit_breaker_failure()
            
            # Wrap with enhanced error context
            enhanced_error = YamlSystemError(
                f"Workflow agent '{self.name}' execution failed: {str(e)}",
                context=current_context if 'current_context' in locals() else self.yaml_context,
                original_error=e,
                suggested_fixes=[
                    "Check workflow configuration",
                    "Verify sub-agent implementations",
                    "Check system resources and connectivity"
                ]
            )
            
            logger.error(f"Workflow agent unexpected error: {enhanced_error}")
            raise enhanced_error
    
    def _get_execution_strategy(self):
        """Get the appropriate execution strategy for this workflow.
        
        Returns:
            WorkflowExecutionStrategy: Strategy for executing this workflow
        """
        strategy_name = self.workflow_config.execution_mode.value
        strategy = self.strategy_manager.get_strategy(strategy_name)
        
        if not strategy:
            # Fall back to default strategy
            strategy = self.strategy_manager.get_default_strategy()
            if not strategy:
                raise YamlSystemError(
                    f"No execution strategy available for workflow '{self.name}'",
                    context=self.yaml_context,
                    suggested_fixes=[
                        "Register a default execution strategy",
                        f"Register strategy for mode '{strategy_name}'",
                        "Check workflow configuration"
                    ]
                )
            
            logger.warning(f"Using default strategy for workflow '{self.name}' (requested: {strategy_name})")
        
        return strategy
    
    def _update_performance_metrics(
        self, 
        execution_time: float, 
        success: bool, 
        sub_agent_executions: int = 0
    ) -> None:
        """Update performance metrics.
        
        Args:
            execution_time: Total execution time
            success: Whether execution was successful
            sub_agent_executions: Number of sub-agent executions
        """
        if success:
            self._performance_metrics['successful_invocations'] += 1
        else:
            self._performance_metrics['failed_invocations'] += 1
            
        self._performance_metrics['total_execution_time'] += execution_time
        self._performance_metrics['avg_execution_time'] = (
            self._performance_metrics['total_execution_time'] / 
            self._performance_metrics['total_invocations']
        )
        
        self._performance_metrics['total_sub_agent_executions'] += sub_agent_executions
    
    def _update_circuit_breaker_success(self) -> None:
        """Update circuit breaker state on successful execution."""
        if not self.workflow_config.circuit_breaker.enable_workflow_circuit_breaker:
            return
            
        if self._circuit_breaker_state['state'] == 'half_open':
            self._circuit_breaker_state['success_count'] += 1
            if (self._circuit_breaker_state['success_count'] >= 
                self.workflow_config.circuit_breaker.workflow_circuit_breaker.success_threshold):
                # Close the circuit
                self._circuit_breaker_state['state'] = 'closed'
                self._circuit_breaker_state['failure_count'] = 0
                logger.info(f"Circuit breaker for workflow '{self.name}' closed after successful recovery")
        else:
            # Reset failure count on successful execution
            self._circuit_breaker_state['failure_count'] = 0
    
    def _update_circuit_breaker_failure(self) -> None:
        """Update circuit breaker state on failed execution."""
        if not self.workflow_config.circuit_breaker.enable_workflow_circuit_breaker:
            return
            
        self._circuit_breaker_state['failure_count'] += 1
        self._circuit_breaker_state['last_failure_time'] = time.time()
        
        failure_threshold = self.workflow_config.circuit_breaker.workflow_circuit_breaker.failure_threshold
        
        if (self._circuit_breaker_state['failure_count'] >= failure_threshold and 
            self._circuit_breaker_state['state'] != 'open'):
            # Open the circuit
            self._circuit_breaker_state['state'] = 'open'
            self._performance_metrics['sub_agent_failures'] += 1
            logger.warning(f"Circuit breaker for workflow '{self.name}' opened after {failure_threshold} failures")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this workflow agent.
        
        Returns:
            Dict containing performance metrics
        """
        metrics = self._performance_metrics.copy()
        metrics['circuit_breaker_state'] = self._circuit_breaker_state.copy()
        
        # Add strategy-specific metrics
        if self.strategy_manager:
            metrics['strategy_metrics'] = self.strategy_manager.get_all_performance_metrics()
        
        return metrics
    
    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker state to closed."""
        self._circuit_breaker_state = {
            'state': 'closed',
            'failure_count': 0,
            'last_failure_time': 0.0,
            'success_count': 0,
        }
        logger.info(f"Circuit breaker for workflow '{self.name}' reset to closed state")


class EnhancedSequentialAgent(EnhancedWorkflowAgent):
    """Enhanced sequential agent with circuit breakers and performance monitoring."""
    
    def __init__(
        self,
        *,
        name: str,
        sub_agents: List[BaseAgent],
        workflow_config: Optional[WorkflowConfig] = None,
        yaml_context: Optional[YamlSystemContext] = None,
        strategy_manager: Optional[WorkflowStrategyManager] = None,
        **kwargs
    ):
        """Initialize enhanced sequential agent.
        
        Args:
            name: Agent name
            sub_agents: List of sub-agents to execute sequentially
            workflow_config: Configuration for workflow execution
            yaml_context: YAML system context for error handling
            strategy_manager: Workflow strategy manager
            **kwargs: Additional arguments passed to BaseAgent
        """
        # Set default execution mode to sequential
        if workflow_config is None:
            workflow_config = WorkflowConfig(execution_mode=WorkflowExecutionMode.SEQUENTIAL)
        else:
            workflow_config.execution_mode = WorkflowExecutionMode.SEQUENTIAL
        
        super().__init__(
            name=name,
            sub_agents=sub_agents,
            workflow_config=workflow_config,
            yaml_context=yaml_context,
            strategy_manager=strategy_manager,
            **kwargs
        )
        
        logger.info(f"Initialized EnhancedSequentialAgent '{name}' with enhanced capabilities")


class EnhancedParallelAgent(EnhancedWorkflowAgent):
    """Enhanced parallel agent with performance monitoring and resource management."""
    
    def __init__(
        self,
        *,
        name: str,
        sub_agents: List[BaseAgent],
        workflow_config: Optional[WorkflowConfig] = None,
        yaml_context: Optional[YamlSystemContext] = None,
        strategy_manager: Optional[WorkflowStrategyManager] = None,
        **kwargs
    ):
        """Initialize enhanced parallel agent.
        
        Args:
            name: Agent name
            sub_agents: List of sub-agents to execute in parallel
            workflow_config: Configuration for workflow execution
            yaml_context: YAML system context for error handling
            strategy_manager: Workflow strategy manager
            **kwargs: Additional arguments passed to BaseAgent
        """
        # Set default execution mode to parallel
        if workflow_config is None:
            workflow_config = WorkflowConfig(execution_mode=WorkflowExecutionMode.PARALLEL)
        else:
            workflow_config.execution_mode = WorkflowExecutionMode.PARALLEL
        
        super().__init__(
            name=name,
            sub_agents=sub_agents,
            workflow_config=workflow_config,
            yaml_context=yaml_context,
            strategy_manager=strategy_manager,
            **kwargs
        )
        
        logger.info(f"Initialized EnhancedParallelAgent '{name}' with enhanced capabilities")


class EnhancedLoopAgent(EnhancedWorkflowAgent):
    """Enhanced loop agent with retry policies and iteration control."""
    
    def __init__(
        self,
        *,
        name: str,
        sub_agents: List[BaseAgent],
        workflow_config: Optional[WorkflowConfig] = None,
        yaml_context: Optional[YamlSystemContext] = None,
        strategy_manager: Optional[WorkflowStrategyManager] = None,
        max_iterations: Optional[int] = None,
        **kwargs
    ):
        """Initialize enhanced loop agent.
        
        Args:
            name: Agent name
            sub_agents: List of sub-agents to execute in loop
            workflow_config: Configuration for workflow execution
            yaml_context: YAML system context for error handling
            strategy_manager: Workflow strategy manager
            max_iterations: Maximum number of loop iterations (overrides config)
            **kwargs: Additional arguments passed to BaseAgent
        """
        # Set default execution mode to loop
        if workflow_config is None:
            workflow_config = WorkflowConfig(execution_mode=WorkflowExecutionMode.LOOP)
        else:
            workflow_config.execution_mode = WorkflowExecutionMode.LOOP
        
        # Override max iterations if specified
        if max_iterations is not None:
            workflow_config.max_loop_iterations = max_iterations
        
        super().__init__(
            name=name,
            sub_agents=sub_agents,
            workflow_config=workflow_config,
            yaml_context=yaml_context,
            strategy_manager=strategy_manager,
            **kwargs
        )
        
        # Additional loop-specific metrics
        self._loop_metrics = {
            'total_iterations': 0,
            'successful_iterations': 0,
            'failed_iterations': 0,
            'avg_iteration_time': 0.0,
        }
        
        logger.info(f"Initialized EnhancedLoopAgent '{name}' with enhanced capabilities")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics including loop-specific metrics.
        
        Returns:
            Dict containing performance metrics
        """
        metrics = super().get_performance_metrics()
        metrics['loop_metrics'] = self._loop_metrics.copy()
        return metrics