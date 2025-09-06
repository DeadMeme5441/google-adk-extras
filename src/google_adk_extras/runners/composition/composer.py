"""Workflow composition API for building complex agent workflows.

This module provides fluent APIs for composing complex agent workflows using
enhanced agent composition classes that properly inherit from ADK BaseAgent
with advanced configuration options and monitoring capabilities.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from google.adk.agents.base_agent import BaseAgent

from ..errors import YamlSystemContext, YamlSystemError
from .enhanced_agents import (
    EnhancedLoopAgent,
    EnhancedParallelAgent,
    EnhancedSequentialAgent,
)
from .enhanced_configs import (
    EnhancedWorkflowConfig,
    FailureHandlingMode,
    WorkflowExecutionMode,
    CircuitBreakerConfig,
    RetryPolicyConfig,
    TimeoutConfig,
)

logger = logging.getLogger(__name__)


class WorkflowBuilder:
    """Fluent builder for constructing enhanced agent workflows.
    
    This class provides a fluent interface for building complex workflows
    with method chaining and validation using proper ADK BaseAgent subclasses.
    """
    
    def __init__(
        self,
        name: str,
        execution_mode: WorkflowExecutionMode,
        composer: 'WorkflowComposer'
    ):
        """Initialize workflow builder.
        
        Args:
            name: Name of the workflow
            execution_mode: Primary execution mode
            composer: Parent composer instance
        """
        self.name = name
        self.execution_mode = execution_mode
        self.composer = composer
        
        # Build configuration
        self._agents: List[BaseAgent] = []
        self._config = EnhancedWorkflowConfig(execution_mode=execution_mode)
        self._yaml_context: Optional[YamlSystemContext] = None
        self._max_iterations: Optional[int] = None
        
        logger.debug(f"Initialized WorkflowBuilder '{name}' with mode {execution_mode.value}")
    
    def add_agent(self, agent: BaseAgent) -> 'WorkflowBuilder':
        """Add a single agent to the workflow.
        
        Args:
            agent: Agent to add
            
        Returns:
            Self for method chaining
        """
        self._agents.append(agent)
        logger.debug(f"Added agent '{getattr(agent, 'name', type(agent).__name__)}' to workflow '{self.name}'")
        return self
    
    def add_agents(self, agents: List[BaseAgent]) -> 'WorkflowBuilder':
        """Add multiple agents to the workflow.
        
        Args:
            agents: List of agents to add
            
        Returns:
            Self for method chaining
        """
        self._agents.extend(agents)
        logger.debug(f"Added {len(agents)} agents to workflow '{self.name}'")
        return self
    
    def with_config(self, config: EnhancedWorkflowConfig) -> 'WorkflowBuilder':
        """Set enhanced workflow configuration.
        
        Args:
            config: Enhanced workflow configuration
            
        Returns:
            Self for method chaining
        """
        # Preserve execution mode
        config.execution_mode = self.execution_mode
        self._config = config
        logger.debug(f"Applied enhanced workflow configuration to '{self.name}'")
        return self
    
    def with_failure_handling(self, mode: FailureHandlingMode) -> 'WorkflowBuilder':
        """Set failure handling mode.
        
        Args:
            mode: Failure handling mode
            
        Returns:
            Self for method chaining
        """
        self._config.failure_handling = mode
        logger.debug(f"Set failure handling mode to {mode.value} for workflow '{self.name}'")
        return self
    
    def with_timeout(
        self, 
        step_timeout: float, 
        total_timeout: Optional[float] = None
    ) -> 'WorkflowBuilder':
        """Set timeout configuration.
        
        Args:
            step_timeout: Timeout for individual steps
            total_timeout: Total workflow timeout (optional)
            
        Returns:
            Self for method chaining
        """
        self._config.timeouts.step_timeout = step_timeout
        if total_timeout:
            self._config.timeouts.total_timeout = total_timeout
        
        logger.debug(f"Set timeout configuration for workflow '{self.name}'")
        return self
    
    def with_retry_policy(
        self, 
        max_attempts: int = 3, 
        base_delay: float = 1.0
    ) -> 'WorkflowBuilder':
        """Configure retry policy.
        
        Args:
            max_attempts: Maximum retry attempts
            base_delay: Base delay between retries
            
        Returns:
            Self for method chaining
        """
        self._config.retry_policy.max_attempts = max_attempts
        self._config.retry_policy.base_delay = base_delay
        
        logger.debug(f"Set retry policy for workflow '{self.name}': {max_attempts} attempts, {base_delay}s base delay")
        return self
    
    def with_circuit_breaker(
        self, 
        failure_threshold: int = 3, 
        recovery_timeout: float = 60.0
    ) -> 'WorkflowBuilder':
        """Enable circuit breaker with custom configuration.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            
        Returns:
            Self for method chaining
        """
        self._config.circuit_breaker.failure_threshold = failure_threshold
        self._config.circuit_breaker.recovery_timeout = recovery_timeout
        
        logger.debug(f"Enabled circuit breaker for workflow '{self.name}': {failure_threshold} failures, {recovery_timeout}s recovery")
        return self
    
    def with_max_iterations(self, max_iterations: int) -> 'WorkflowBuilder':
        """Set maximum iterations for loop workflows.
        
        Args:
            max_iterations: Maximum number of iterations
            
        Returns:
            Self for method chaining
            
        Raises:
            YamlSystemError: If not a loop workflow
        """
        if self.execution_mode != WorkflowExecutionMode.LOOP:
            raise YamlSystemError(
                f"max_iterations only applies to loop workflows, not {self.execution_mode.value}",
                context=YamlSystemContext(agent_name=self.name),
                suggested_fixes=[
                    "Use composer.loop() to create a loop workflow",
                    "Remove max_iterations for non-loop workflows"
                ]
            )
        
        self._max_iterations = max_iterations
        self._config.max_loop_iterations = max_iterations
        logger.debug(f"Set max iterations to {max_iterations} for loop workflow '{self.name}'")
        return self
    
    def with_concurrency_limit(self, max_concurrent: int) -> 'WorkflowBuilder':
        """Set concurrency limit for parallel workflows.
        
        Args:
            max_concurrent: Maximum concurrent executions
            
        Returns:
            Self for method chaining
        """
        self._config.max_concurrent_steps = max_concurrent
        logger.debug(f"Set concurrency limit to {max_concurrent} for workflow '{self.name}'")
        return self
    
    def with_yaml_context(self, yaml_context: YamlSystemContext) -> 'WorkflowBuilder':
        """Set YAML system context for enhanced error handling.
        
        Args:
            yaml_context: YAML system context
            
        Returns:
            Self for method chaining
        """
        self._yaml_context = yaml_context
        logger.debug(f"Applied YAML context to workflow '{self.name}'")
        return self
    
    def with_performance_monitoring(
        self, 
        enable_timing: bool = True,
        enable_event_metrics: bool = True
    ) -> 'WorkflowBuilder':
        """Configure performance monitoring.
        
        Args:
            enable_timing: Enable execution timing
            enable_event_metrics: Enable event metrics collection
            
        Returns:
            Self for method chaining
        """
        self._config.performance_monitoring.enable_timing = enable_timing
        self._config.performance_monitoring.enable_event_metrics = enable_event_metrics
        
        logger.debug(f"Configured performance monitoring for workflow '{self.name}'")
        return self
    
    def with_metadata(self, **metadata) -> 'WorkflowBuilder':
        """Add metadata to workflow configuration.
        
        Args:
            **metadata: Arbitrary metadata key-value pairs
            
        Returns:
            Self for method chaining
        """
        self._config.workflow_metadata.update(metadata)
        logger.debug(f"Added metadata to workflow '{self.name}': {list(metadata.keys())}")
        return self
    
    def build(self) -> BaseAgent:
        """Build the configured enhanced workflow agent.
        
        Returns:
            BaseAgent: Configured enhanced workflow agent
            
        Raises:
            YamlSystemError: If configuration is invalid
        """
        if not self._agents:
            raise YamlSystemError(
                f"Workflow '{self.name}' has no agents configured",
                context=self._yaml_context or YamlSystemContext(system_name=self.name),
                suggested_fixes=[
                    "Add at least one agent using add_agent() or add_agents()",
                    "Check workflow configuration"
                ]
            )
        
        # Build agent based on execution mode
        agent_kwargs = {
            'name': self.name,
            'sub_agents': self._agents,
            'enhanced_config': self._config,
            'yaml_context': self._yaml_context,
        }
        
        if self.execution_mode == WorkflowExecutionMode.SEQUENTIAL:
            agent = EnhancedSequentialAgent(**agent_kwargs)
        elif self.execution_mode == WorkflowExecutionMode.PARALLEL:
            agent = EnhancedParallelAgent(**agent_kwargs)
        elif self.execution_mode == WorkflowExecutionMode.LOOP:
            if self._max_iterations is not None:
                agent_kwargs['max_iterations'] = self._max_iterations
            agent = EnhancedLoopAgent(**agent_kwargs)
        else:
            raise YamlSystemError(
                f"Unsupported execution mode: {self.execution_mode}",
                context=self._yaml_context or YamlSystemContext(system_name=self.name),
                suggested_fixes=[
                    "Use SEQUENTIAL, PARALLEL, or LOOP execution mode",
                    "Check workflow configuration"
                ]
            )
        
        logger.info(f"Built {self.execution_mode.value} enhanced agent '{self.name}' with {len(self._agents)} sub-agents")
        return agent


class WorkflowComposer:
    """Main composer class for building complex agent workflows.
    
    This class provides factory methods and composition utilities for creating
    enhanced workflow agents with fluent configuration APIs.
    """
    
    def __init__(self):
        """Initialize enhanced workflow composer."""
        self._default_yaml_context = YamlSystemContext(system_name="EnhancedWorkflowComposer")
        logger.debug("Initialized Enhanced WorkflowComposer")
    
    def sequential(self, name: str) -> WorkflowBuilder:
        """Create a sequential workflow builder.
        
        Args:
            name: Name of the workflow
            
        Returns:
            WorkflowBuilder: Builder for sequential workflow
        """
        return WorkflowBuilder(name, WorkflowExecutionMode.SEQUENTIAL, self)
    
    def parallel(self, name: str) -> WorkflowBuilder:
        """Create a parallel workflow builder.
        
        Args:
            name: Name of the workflow
            
        Returns:
            WorkflowBuilder: Builder for parallel workflow
        """
        return WorkflowBuilder(name, WorkflowExecutionMode.PARALLEL, self)
    
    def loop(self, name: str) -> WorkflowBuilder:
        """Create a loop workflow builder.
        
        Args:
            name: Name of the workflow
            
        Returns:
            WorkflowBuilder: Builder for loop workflow
        """
        return WorkflowBuilder(name, WorkflowExecutionMode.LOOP, self)
    
    def builder(self, name: str, mode: WorkflowExecutionMode = WorkflowExecutionMode.SEQUENTIAL) -> WorkflowBuilder:
        """Create a generic workflow builder with specified execution mode.
        
        Args:
            name: Name of the workflow
            mode: Execution mode
            
        Returns:
            WorkflowBuilder: Builder for workflow
        """
        return WorkflowBuilder(name, mode, self)
    
    def create_simple_sequential(
        self, 
        name: str, 
        agents: List[BaseAgent], 
        config: Optional[EnhancedWorkflowConfig] = None
    ) -> EnhancedSequentialAgent:
        """Create a simple sequential workflow with minimal configuration.
        
        Args:
            name: Name of the workflow
            agents: List of agents to execute sequentially
            config: Optional enhanced workflow configuration
            
        Returns:
            EnhancedSequentialAgent: Configured enhanced sequential agent
        """
        return EnhancedSequentialAgent(
            name=name,
            sub_agents=agents,
            enhanced_config=config or EnhancedWorkflowConfig(execution_mode=WorkflowExecutionMode.SEQUENTIAL),
            yaml_context=self._default_yaml_context.with_agent(name),
        )
    
    def create_simple_parallel(
        self, 
        name: str, 
        agents: List[BaseAgent], 
        config: Optional[EnhancedWorkflowConfig] = None
    ) -> EnhancedParallelAgent:
        """Create a simple parallel workflow with minimal configuration.
        
        Args:
            name: Name of the workflow
            agents: List of agents to execute in parallel
            config: Optional enhanced workflow configuration
            
        Returns:
            EnhancedParallelAgent: Configured enhanced parallel agent
        """
        return EnhancedParallelAgent(
            name=name,
            sub_agents=agents,
            enhanced_config=config or EnhancedWorkflowConfig(execution_mode=WorkflowExecutionMode.PARALLEL),
            yaml_context=self._default_yaml_context.with_agent(name),
        )
    
    def create_simple_loop(
        self, 
        name: str, 
        agents: List[BaseAgent], 
        max_iterations: int = 10,
        config: Optional[EnhancedWorkflowConfig] = None
    ) -> EnhancedLoopAgent:
        """Create a simple loop workflow with minimal configuration.
        
        Args:
            name: Name of the workflow
            agents: List of agents to execute in loop
            max_iterations: Maximum number of iterations
            config: Optional enhanced workflow configuration
            
        Returns:
            EnhancedLoopAgent: Configured enhanced loop agent
        """
        loop_config = config or EnhancedWorkflowConfig(execution_mode=WorkflowExecutionMode.LOOP)
        loop_config.max_loop_iterations = max_iterations
        
        return EnhancedLoopAgent(
            name=name,
            sub_agents=agents,
            max_iterations=max_iterations,
            enhanced_config=loop_config,
            yaml_context=self._default_yaml_context.with_agent(name),
        )
    
    def create_pipeline(
        self, 
        name: str, 
        stages: List[List[BaseAgent]],
        config: Optional[EnhancedWorkflowConfig] = None
    ) -> EnhancedSequentialAgent:
        """Create a pipeline workflow with sequential stages of parallel agents.
        
        This creates a sequential workflow where each stage contains agents that
        run in parallel, but stages execute sequentially.
        
        Args:
            name: Name of the pipeline
            stages: List of agent lists, each list represents a parallel stage
            config: Optional workflow configuration
            
        Returns:
            EnhancedSequentialAgent: Pipeline workflow agent
        """
        if not stages:
            raise YamlSystemError(
                f"Pipeline '{name}' has no stages configured",
                context=self._default_yaml_context.with_system(name),
                suggested_fixes=[
                    "Add at least one stage with agents",
                    "Check pipeline configuration"
                ]
            )
        
        # Create parallel agents for each stage
        stage_agents = []
        for i, stage_agent_list in enumerate(stages):
            if not stage_agent_list:
                continue
                
            if len(stage_agent_list) == 1:
                # Single agent, use directly
                stage_agents.append(stage_agent_list[0])
            else:
                # Multiple agents, create parallel wrapper
                stage_name = f"{name}_stage_{i}"
                parallel_agent = self.create_simple_parallel(
                    name=stage_name,
                    agents=stage_agent_list,
                    config=config
                )
                stage_agents.append(parallel_agent)
        
        # Create sequential workflow of stages
        pipeline_config = config or EnhancedWorkflowConfig(execution_mode=WorkflowExecutionMode.SEQUENTIAL)
        pipeline = EnhancedSequentialAgent(
            name=name,
            sub_agents=stage_agents,
            enhanced_config=pipeline_config,
            yaml_context=self._default_yaml_context.with_agent(name),
        )
        
        logger.info(f"Created pipeline workflow '{name}' with {len(stages)} stages")
        return pipeline
    
    def create_conditional_workflow(
        self,
        name: str,
        condition_agent: BaseAgent,
        success_agents: List[BaseAgent],
        failure_agents: Optional[List[BaseAgent]] = None,
        config: Optional[EnhancedWorkflowConfig] = None
    ) -> EnhancedSequentialAgent:
        """Create a conditional workflow based on condition agent result.
        
        This is a simplified conditional workflow implementation. For more complex
        conditional logic, implement custom agents with condition handling.
        
        Args:
            name: Name of the workflow
            condition_agent: Agent that determines the condition
            success_agents: Agents to execute on success condition
            failure_agents: Optional agents to execute on failure condition
            config: Optional workflow configuration
            
        Returns:
            EnhancedSequentialAgent: Conditional workflow agent
        """
        # For now, create a sequential workflow that includes the condition agent
        # followed by success agents. More sophisticated conditional logic would
        # require custom agent implementation.
        all_agents = [condition_agent] + success_agents
        
        if failure_agents:
            # In a real implementation, this would need custom logic to handle
            # conditional execution based on condition_agent result
            logger.warning(f"Conditional workflow '{name}': failure_agents specified but not yet fully supported")
        
        conditional_config = config or EnhancedWorkflowConfig(
            execution_mode=WorkflowExecutionMode.SEQUENTIAL,
            failure_handling=FailureHandlingMode.CONTINUE_ON_FAILURE
        )
        
        workflow = EnhancedSequentialAgent(
            name=name,
            sub_agents=all_agents,
            enhanced_config=conditional_config,
            yaml_context=self._default_yaml_context.with_agent(name),
        )
        
        logger.info(f"Created conditional workflow '{name}' (simplified implementation)")
        return workflow