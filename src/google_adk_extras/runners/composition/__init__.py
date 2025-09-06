"""Enhanced Agent Composition Engine.

This module provides enhanced agent composition capabilities that properly
extend Google ADK's BaseAgent classes with advanced features including:
- Circuit breaker patterns for resilience
- Performance monitoring and metrics collection
- Advanced retry policies and error handling
- Enhanced workflow configuration and orchestration
- YAML system integration and error reporting

Key Components:
- EnhancedSequentialAgent: Sequential execution with monitoring (extends ADK BaseAgent)
- EnhancedParallelAgent: Parallel execution with load balancing (extends ADK BaseAgent)
- EnhancedLoopAgent: Loop execution with adaptive features (extends ADK BaseAgent)
- WorkflowComposer: Fluent API for building complex workflows
- Enhanced configuration classes that extend ADK config classes
- Performance monitoring and circuit breaker utilities
"""

from .enhanced_agents import (
    EnhancedSequentialAgent,
    EnhancedParallelAgent,
    EnhancedLoopAgent,
)
from .enhanced_configs import (
    EnhancedWorkflowConfig,
    EnhancedSequentialAgentConfig,
    EnhancedParallelAgentConfig,
    EnhancedLoopAgentConfig,
    WorkflowExecutionMode,
    FailureHandlingMode,
    CircuitBreakerConfig,
    RetryPolicyConfig,
    PerformanceMonitoringConfig,
    TimeoutConfig,
)
from .composer import (
    WorkflowComposer,
    WorkflowBuilder,
)
from ..monitoring import (
    PerformanceMonitor,
    CircuitBreaker,
    CircuitBreakerState,
    PerformanceMetrics,
)

__all__ = [
    # Enhanced ADK Agent Classes
    'EnhancedSequentialAgent',
    'EnhancedParallelAgent',
    'EnhancedLoopAgent',
    
    # Enhanced Configuration Classes
    'EnhancedWorkflowConfig',
    'EnhancedSequentialAgentConfig',
    'EnhancedParallelAgentConfig',
    'EnhancedLoopAgentConfig',
    'WorkflowExecutionMode',
    'FailureHandlingMode',
    'CircuitBreakerConfig',
    'RetryPolicyConfig',
    'PerformanceMonitoringConfig',
    'TimeoutConfig',
    
    # Composition API
    'WorkflowComposer',
    'WorkflowBuilder',
    
    # Monitoring and Utilities
    'PerformanceMonitor',
    'CircuitBreaker',
    'CircuitBreakerState',
    'PerformanceMetrics',
]