"""Enhanced agent configuration classes that extend ADK config classes.

These configs add enhanced capabilities like circuit breakers, performance
monitoring, retry policies, and advanced workflow orchestration to the
base ADK agent configuration classes.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from google.adk.agents.base_agent_config import BaseAgentConfig
from google.adk.agents.sequential_agent_config import SequentialAgentConfig
from google.adk.agents.parallel_agent_config import ParallelAgentConfig
from google.adk.agents.loop_agent_config import LoopAgentConfig

logger = logging.getLogger(__name__)


class FailureHandlingMode(str, Enum):
    """Failure handling strategies for enhanced workflow execution."""
    FAIL_FAST = "fail_fast"
    CONTINUE_ON_FAILURE = "continue_on_failure"
    RETRY_ON_FAILURE = "retry_on_failure"
    CIRCUIT_BREAKER = "circuit_breaker"


class WorkflowExecutionMode(str, Enum):
    """Execution modes for enhanced workflow orchestration."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    LOOP = "loop"
    CUSTOM = "custom"


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker functionality."""
    model_config = ConfigDict(extra='forbid')
    
    failure_threshold: int = Field(
        default=3, description="Number of failures before opening circuit"
    )
    recovery_timeout: float = Field(
        default=60.0, description="Time to wait before attempting recovery (seconds)"
    )
    half_open_max_calls: int = Field(
        default=1, description="Max calls allowed in half-open state"
    )
    expected_exception_types: List[str] = Field(
        default_factory=list, description="Exception types that trigger circuit breaker"
    )


class RetryPolicyConfig(BaseModel):
    """Configuration for retry policies."""
    model_config = ConfigDict(extra='forbid')
    
    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    base_delay: float = Field(default=1.0, description="Base delay between retries (seconds)")
    max_delay: float = Field(default=60.0, description="Maximum delay between retries (seconds)")
    exponential_backoff: bool = Field(default=True, description="Use exponential backoff")
    jitter: bool = Field(default=True, description="Add random jitter to delays")
    retry_exceptions: List[str] = Field(
        default_factory=list, description="Exception types to retry on"
    )


class PerformanceMonitoringConfig(BaseModel):
    """Configuration for performance monitoring and metrics."""
    model_config = ConfigDict(extra='forbid')
    
    enable_timing: bool = Field(default=True, description="Enable execution timing")
    enable_memory_tracking: bool = Field(default=False, description="Enable memory usage tracking")
    enable_event_metrics: bool = Field(default=True, description="Enable event metrics collection")
    metrics_interval: float = Field(default=10.0, description="Metrics collection interval (seconds)")
    alert_thresholds: Dict[str, float] = Field(
        default_factory=dict, description="Performance alert thresholds"
    )


class TimeoutConfig(BaseModel):
    """Configuration for workflow timeouts."""
    model_config = ConfigDict(extra='forbid')
    
    step_timeout: Optional[float] = Field(
        default=None, description="Timeout for individual steps (seconds)"
    )
    total_timeout: Optional[float] = Field(
        default=None, description="Total workflow timeout (seconds)"
    )
    graceful_shutdown_timeout: float = Field(
        default=30.0, description="Time to wait for graceful shutdown (seconds)"
    )


class EnhancedWorkflowConfig(BaseModel):
    """Base configuration for enhanced workflow capabilities."""
    model_config = ConfigDict(extra='forbid')
    
    # Core workflow settings
    execution_mode: WorkflowExecutionMode = Field(
        default=WorkflowExecutionMode.SEQUENTIAL,
        description="Primary execution mode for the workflow"
    )
    failure_handling: FailureHandlingMode = Field(
        default=FailureHandlingMode.FAIL_FAST,
        description="How to handle failures during execution"
    )
    
    # Enhanced capabilities
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig,
        description="Circuit breaker configuration"
    )
    retry_policy: RetryPolicyConfig = Field(
        default_factory=RetryPolicyConfig,
        description="Retry policy configuration"
    )
    performance_monitoring: PerformanceMonitoringConfig = Field(
        default_factory=PerformanceMonitoringConfig,
        description="Performance monitoring configuration"
    )
    timeouts: TimeoutConfig = Field(
        default_factory=TimeoutConfig,
        description="Timeout configuration"
    )
    
    # Workflow orchestration
    max_concurrent_steps: Optional[int] = Field(
        default=None, description="Maximum concurrent steps (for parallel execution)"
    )
    max_loop_iterations: Optional[int] = Field(
        default=None, description="Maximum loop iterations (for loop execution)"
    )
    
    # Metadata and context
    workflow_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom workflow metadata"
    )
    enable_tracing: bool = Field(
        default=False, description="Enable distributed tracing"
    )
    trace_sampling_rate: float = Field(
        default=0.1, description="Tracing sampling rate (0.0-1.0)"
    )


class EnhancedSequentialAgentConfig(SequentialAgentConfig):
    """Enhanced configuration for sequential agent execution."""
    model_config = ConfigDict(extra='forbid')
    
    agent_class: Literal['EnhancedSequentialAgent'] = Field(
        default='EnhancedSequentialAgent',
        description='Enhanced sequential agent class identifier'
    )
    
    # Enhanced capabilities
    enhanced_config: EnhancedWorkflowConfig = Field(
        default_factory=lambda: EnhancedWorkflowConfig(
            execution_mode=WorkflowExecutionMode.SEQUENTIAL
        ),
        description="Enhanced workflow configuration"
    )
    
    # Sequential-specific settings
    stop_on_first_failure: bool = Field(
        default=True, description="Stop execution on first step failure"
    )
    enable_step_rollback: bool = Field(
        default=False, description="Enable rollback of completed steps on failure"
    )


class EnhancedParallelAgentConfig(ParallelAgentConfig):
    """Enhanced configuration for parallel agent execution."""
    model_config = ConfigDict(extra='forbid')
    
    agent_class: Literal['EnhancedParallelAgent'] = Field(
        default='EnhancedParallelAgent',
        description='Enhanced parallel agent class identifier'
    )
    
    # Enhanced capabilities
    enhanced_config: EnhancedWorkflowConfig = Field(
        default_factory=lambda: EnhancedWorkflowConfig(
            execution_mode=WorkflowExecutionMode.PARALLEL
        ),
        description="Enhanced workflow configuration"
    )
    
    # Parallel-specific settings
    max_concurrent_agents: Optional[int] = Field(
        default=None, description="Maximum number of agents to run concurrently"
    )
    load_balancing_strategy: str = Field(
        default="round_robin", description="Load balancing strategy for agent distribution"
    )
    result_aggregation_mode: str = Field(
        default="collect_all", description="How to aggregate results from parallel agents"
    )


class EnhancedLoopAgentConfig(LoopAgentConfig):
    """Enhanced configuration for loop agent execution."""
    model_config = ConfigDict(extra='forbid')
    
    agent_class: Literal['EnhancedLoopAgent'] = Field(
        default='EnhancedLoopAgent',
        description='Enhanced loop agent class identifier'
    )
    
    # Enhanced capabilities
    enhanced_config: EnhancedWorkflowConfig = Field(
        default_factory=lambda: EnhancedWorkflowConfig(
            execution_mode=WorkflowExecutionMode.LOOP
        ),
        description="Enhanced workflow configuration"
    )
    
    # Loop-specific settings from base LoopAgentConfig are inherited
    # Additional loop-specific enhancements
    convergence_threshold: Optional[float] = Field(
        default=None, description="Threshold for loop convergence detection"
    )
    enable_adaptive_iterations: bool = Field(
        default=False, description="Enable adaptive iteration count based on performance"
    )
    iteration_cooldown: float = Field(
        default=0.0, description="Cooldown period between iterations (seconds)"
    )
