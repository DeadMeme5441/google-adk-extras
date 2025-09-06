"""Configuration classes for enhanced agent composition.

This module provides configuration models for workflow composition including
timeouts, retry policies, circuit breakers, and workflow-specific settings.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..config import RetryConfig, CircuitBreakerConfig, RetryStrategy

logger = logging.getLogger(__name__)


class WorkflowExecutionMode(str, Enum):
    """Workflow execution mode options."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel" 
    LOOP = "loop"
    CONDITIONAL = "conditional"
    PIPELINE = "pipeline"


class FailureHandlingMode(str, Enum):
    """How to handle failures in workflow execution."""
    FAIL_FAST = "fail_fast"           # Stop on first failure
    CONTINUE_ON_FAILURE = "continue"  # Continue with remaining steps
    RETRY_FAILED_STEPS = "retry"      # Retry failed steps before continuing
    ROLLBACK_ON_FAILURE = "rollback" # Rollback previous steps on failure


@dataclass
class WorkflowTimeoutConfig:
    """Configuration for workflow-specific timeouts."""
    
    sequential_step_timeout: float = 300.0
    """Timeout for individual steps in sequential workflows."""
    
    parallel_total_timeout: float = 600.0
    """Total timeout for parallel workflow completion."""
    
    parallel_step_timeout: float = 300.0
    """Timeout for individual steps in parallel workflows."""
    
    loop_iteration_timeout: float = 300.0
    """Timeout for individual loop iterations."""
    
    loop_total_timeout: float = 1800.0
    """Total timeout for loop workflow completion."""
    
    workflow_startup_timeout: float = 30.0
    """Timeout for workflow initialization."""
    
    workflow_shutdown_timeout: float = 30.0
    """Timeout for workflow cleanup."""


@dataclass
class WorkflowRetryConfig:
    """Configuration for workflow-level retry policies."""
    
    step_retry: RetryConfig = field(default_factory=lambda: RetryConfig(
        max_attempts=3,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        base_delay=1.0,
        max_delay=30.0
    ))
    """Retry configuration for individual workflow steps."""
    
    workflow_retry: RetryConfig = field(default_factory=lambda: RetryConfig(
        max_attempts=2,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        base_delay=5.0,
        max_delay=60.0
    ))
    """Retry configuration for entire workflow failures."""
    
    enable_step_retry: bool = True
    """Whether to enable step-level retries."""
    
    enable_workflow_retry: bool = False
    """Whether to enable workflow-level retries."""


@dataclass
class WorkflowCircuitBreakerConfig:
    """Configuration for workflow circuit breakers."""
    
    step_circuit_breaker: CircuitBreakerConfig = field(default_factory=lambda: CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30.0,
        success_threshold=2,
        timeout=300.0
    ))
    """Circuit breaker configuration for workflow steps."""
    
    workflow_circuit_breaker: CircuitBreakerConfig = field(default_factory=lambda: CircuitBreakerConfig(
        failure_threshold=2,
        recovery_timeout=60.0,
        success_threshold=1,
        timeout=600.0
    ))
    """Circuit breaker configuration for entire workflows."""
    
    enable_step_circuit_breaker: bool = True
    """Whether to enable circuit breakers for individual steps."""
    
    enable_workflow_circuit_breaker: bool = True
    """Whether to enable circuit breakers for entire workflows."""


@dataclass
class WorkflowPerformanceConfig:
    """Configuration for workflow performance monitoring."""
    
    enable_step_metrics: bool = True
    """Whether to collect metrics for individual steps."""
    
    enable_workflow_metrics: bool = True
    """Whether to collect metrics for entire workflows."""
    
    enable_execution_tracing: bool = False
    """Whether to enable detailed execution tracing."""
    
    metrics_collection_interval: float = 1.0
    """Interval for collecting performance metrics (seconds)."""
    
    max_trace_history: int = 1000
    """Maximum number of execution traces to keep."""


@dataclass
class WorkflowConfig:
    """Comprehensive configuration for workflow composition."""
    
    execution_mode: WorkflowExecutionMode = WorkflowExecutionMode.SEQUENTIAL
    """Primary execution mode for the workflow."""
    
    failure_handling: FailureHandlingMode = FailureHandlingMode.FAIL_FAST
    """How to handle failures during execution."""
    
    timeouts: WorkflowTimeoutConfig = field(default_factory=WorkflowTimeoutConfig)
    """Timeout configuration for workflow execution."""
    
    retry: WorkflowRetryConfig = field(default_factory=WorkflowRetryConfig)
    """Retry configuration for workflow execution."""
    
    circuit_breaker: WorkflowCircuitBreakerConfig = field(default_factory=WorkflowCircuitBreakerConfig)
    """Circuit breaker configuration for workflow execution."""
    
    performance: WorkflowPerformanceConfig = field(default_factory=WorkflowPerformanceConfig)
    """Performance monitoring configuration."""
    
    # Advanced configuration options
    enable_context_propagation: bool = True
    """Whether to propagate YAML system context through workflow steps."""
    
    enable_state_persistence: bool = False
    """Whether to persist workflow state between steps."""
    
    enable_step_isolation: bool = True
    """Whether to isolate step execution (affects error propagation)."""
    
    max_concurrent_steps: int = 10
    """Maximum number of steps that can execute concurrently in parallel workflows."""
    
    max_loop_iterations: int = 100
    """Maximum number of iterations for loop workflows."""
    
    workflow_metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata for the workflow."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Dict containing configuration values
        """
        return {
            'execution_mode': self.execution_mode.value,
            'failure_handling': self.failure_handling.value,
            'timeouts': {
                'sequential_step_timeout': self.timeouts.sequential_step_timeout,
                'parallel_total_timeout': self.timeouts.parallel_total_timeout,
                'parallel_step_timeout': self.timeouts.parallel_step_timeout,
                'loop_iteration_timeout': self.timeouts.loop_iteration_timeout,
                'loop_total_timeout': self.timeouts.loop_total_timeout,
                'workflow_startup_timeout': self.timeouts.workflow_startup_timeout,
                'workflow_shutdown_timeout': self.timeouts.workflow_shutdown_timeout,
            },
            'retry': {
                'enable_step_retry': self.retry.enable_step_retry,
                'enable_workflow_retry': self.retry.enable_workflow_retry,
                'step_retry': {
                    'max_attempts': self.retry.step_retry.max_attempts,
                    'strategy': self.retry.step_retry.strategy.value,
                    'base_delay': self.retry.step_retry.base_delay,
                    'max_delay': self.retry.step_retry.max_delay,
                },
                'workflow_retry': {
                    'max_attempts': self.retry.workflow_retry.max_attempts,
                    'strategy': self.retry.workflow_retry.strategy.value,
                    'base_delay': self.retry.workflow_retry.base_delay,
                    'max_delay': self.retry.workflow_retry.max_delay,
                }
            },
            'circuit_breaker': {
                'enable_step_circuit_breaker': self.circuit_breaker.enable_step_circuit_breaker,
                'enable_workflow_circuit_breaker': self.circuit_breaker.enable_workflow_circuit_breaker,
            },
            'performance': {
                'enable_step_metrics': self.performance.enable_step_metrics,
                'enable_workflow_metrics': self.performance.enable_workflow_metrics,
                'enable_execution_tracing': self.performance.enable_execution_tracing,
            },
            'options': {
                'enable_context_propagation': self.enable_context_propagation,
                'enable_state_persistence': self.enable_state_persistence,
                'enable_step_isolation': self.enable_step_isolation,
                'max_concurrent_steps': self.max_concurrent_steps,
                'max_loop_iterations': self.max_loop_iterations,
            },
            'metadata': self.workflow_metadata,
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'WorkflowConfig':
        """Create configuration from dictionary.
        
        Args:
            config_dict: Dictionary containing configuration values
            
        Returns:
            WorkflowConfig instance
        """
        config = cls()
        
        if 'execution_mode' in config_dict:
            config.execution_mode = WorkflowExecutionMode(config_dict['execution_mode'])
            
        if 'failure_handling' in config_dict:
            config.failure_handling = FailureHandlingMode(config_dict['failure_handling'])
            
        if 'timeouts' in config_dict:
            timeouts = config_dict['timeouts']
            config.timeouts = WorkflowTimeoutConfig(
                sequential_step_timeout=timeouts.get('sequential_step_timeout', 300.0),
                parallel_total_timeout=timeouts.get('parallel_total_timeout', 600.0),
                parallel_step_timeout=timeouts.get('parallel_step_timeout', 300.0),
                loop_iteration_timeout=timeouts.get('loop_iteration_timeout', 300.0),
                loop_total_timeout=timeouts.get('loop_total_timeout', 1800.0),
                workflow_startup_timeout=timeouts.get('workflow_startup_timeout', 30.0),
                workflow_shutdown_timeout=timeouts.get('workflow_shutdown_timeout', 30.0),
            )
            
        # Apply other configuration values...
        return config