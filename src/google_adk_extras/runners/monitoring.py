"""Monitoring and circuit breaker utilities for enhanced agent execution.

This module provides performance monitoring, circuit breaker patterns,
and resilience utilities for enhanced ADK agent workflows.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from google.adk.events.event import Event

from .composition.enhanced_configs import (
    CircuitBreakerConfig,
    PerformanceMonitoringConfig
)

logger = logging.getLogger(__name__)


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Circuit is open, blocking requests
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class PerformanceMetrics:
    """Container for performance metrics data."""
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration: float = 0.0
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None
    avg_duration: float = 0.0
    event_counts: Dict[str, int] = field(default_factory=dict)
    error_types: Dict[str, int] = field(default_factory=dict)
    timestamps: List[float] = field(default_factory=list)
    
    def add_execution(self, duration: float, success: bool = True, error_type: Optional[str] = None):
        """Add execution metrics.
        
        Args:
            duration: Execution duration in seconds
            success: Whether execution was successful
            error_type: Type of error if failed
        """
        self.execution_count += 1
        self.total_duration += duration
        self.timestamps.append(time.time())
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            if error_type:
                self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
        
        # Update duration stats
        if self.min_duration is None or duration < self.min_duration:
            self.min_duration = duration
        if self.max_duration is None or duration > self.max_duration:
            self.max_duration = duration
        
        self.avg_duration = self.total_duration / self.execution_count
    
    def add_event(self, event_type: str):
        """Add event count.
        
        Args:
            event_type: Type of event
        """
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage.
        
        Returns:
            float: Success rate (0.0-1.0)
        """
        if self.execution_count == 0:
            return 1.0
        return self.success_count / self.execution_count
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as percentage.
        
        Returns:
            float: Failure rate (0.0-1.0)
        """
        return 1.0 - self.success_rate


class CircuitBreaker:
    """Circuit breaker implementation for enhanced agent resilience.
    
    Implements the circuit breaker pattern to prevent cascading failures
    by monitoring failure rates and temporarily blocking requests when
    failure thresholds are exceeded.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        """Initialize circuit breaker.
        
        Args:
            name: Unique name for the circuit breaker
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self._lock = asyncio.Lock()
        
        logger.debug(f"Initialized CircuitBreaker '{name}' with failure_threshold: {config.failure_threshold}")
    
    def can_execute(self) -> bool:
        """Check if execution can proceed.
        
        Returns:
            bool: True if execution should proceed, False if circuit is open
        """
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (
                self.last_failure_time and
                time.time() - self.last_failure_time >= self.config.recovery_timeout
            ):
                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def record_success(self):
        """Record successful execution."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1
            # If we've had successful calls in half-open, close the circuit
            if self.half_open_calls >= self.config.half_open_max_calls:
                logger.info(f"Circuit breaker '{self.name}' transitioning to CLOSED (recovery successful)")
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.last_failure_time = None
        
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.warning(f"Circuit breaker '{self.name}' transitioning to OPEN (half-open failure)")
            self.state = CircuitBreakerState.OPEN
        
        elif self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                logger.warning(
                    f"Circuit breaker '{self.name}' transitioning to OPEN "
                    f"(failure threshold {self.config.failure_threshold} exceeded)"
                )
                self.state = CircuitBreakerState.OPEN
    
    def reset(self):
        """Reset circuit breaker to closed state."""
        logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
    
    @property
    def status(self) -> Dict[str, Any]:
        """Get current circuit breaker status.
        
        Returns:
            Dict[str, Any]: Status information
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.config.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "recovery_timeout": self.config.recovery_timeout,
            "half_open_calls": self.half_open_calls,
            "max_half_open_calls": self.config.half_open_max_calls
        }


class PerformanceMonitor:
    """Performance monitoring utility for enhanced agent execution.
    
    Provides comprehensive performance metrics collection, timing,
    and monitoring capabilities for agent workflows.
    """
    
    def __init__(self, agent_name: str, config: PerformanceMonitoringConfig):
        """Initialize performance monitor.
        
        Args:
            agent_name: Name of the agent being monitored
            config: Performance monitoring configuration
        """
        self.agent_name = agent_name
        self.config = config
        self.metrics = PerformanceMetrics()
        self.active_executions: Set[str] = set()
        self.start_times: Dict[str, float] = {}
        
        logger.debug(f"Initialized PerformanceMonitor for agent '{agent_name}'")
    
    @contextmanager
    def measure_execution(self, execution_id: Optional[str] = None):
        """Context manager for measuring execution time.
        
        Args:
            execution_id: Optional unique identifier for this execution
            
        Yields:
            str: Execution identifier
        """
        if execution_id is None:
            execution_id = f"exec_{len(self.active_executions)}_{time.time()}"
        
        if not self.config.enable_timing:
            yield execution_id
            return
        
        start_time = time.time()
        self.active_executions.add(execution_id)
        self.start_times[execution_id] = start_time
        
        logger.debug(f"Started monitoring execution '{execution_id}' for agent '{self.agent_name}'")
        
        try:
            yield execution_id
            # Successful completion
            duration = time.time() - start_time
            self.metrics.add_execution(duration, success=True)
            logger.debug(
                f"Execution '{execution_id}' completed successfully in {duration:.3f}s"
            )
        
        except Exception as e:
            # Failed execution
            duration = time.time() - start_time
            error_type = type(e).__name__
            self.metrics.add_execution(duration, success=False, error_type=error_type)
            logger.error(
                f"Execution '{execution_id}' failed after {duration:.3f}s: {error_type}"
            )
            raise
        
        finally:
            # Cleanup
            self.active_executions.discard(execution_id)
            self.start_times.pop(execution_id, None)
    
    def record_event(self, event: Event):
        """Record event metrics.
        
        Args:
            event: Event to record metrics for
        """
        if not self.config.enable_event_metrics:
            return
        
        event_type = type(event).__name__
        self.metrics.add_event(event_type)
        
        # Record additional event-specific metrics
        if hasattr(event, 'actions'):
            if event.actions.escalate:
                self.metrics.add_event("escalate_action")
        
        logger.debug(f"Recorded event: {event_type} for agent '{self.agent_name}'")
    
    def record_step_completion(
        self, step_number: int, duration: float, success: bool
    ):
        """Record step completion metrics.
        
        Args:
            step_number: Step number in workflow
            duration: Step execution duration
            success: Whether step completed successfully
        """
        step_type = f"step_{step_number}"
        self.metrics.add_event(step_type)
        
        if success:
            self.metrics.add_event(f"{step_type}_success")
        else:
            self.metrics.add_event(f"{step_type}_failure")
        
        logger.debug(
            f"Recorded step {step_number} completion: success={success}, duration={duration:.3f}s"
        )
    
    def record_error(self, error: Exception):
        """Record error occurrence.
        
        Args:
            error: Exception that occurred
        """
        error_type = type(error).__name__
        self.metrics.error_types[error_type] = self.metrics.error_types.get(error_type, 0) + 1
        
        logger.warning(f"Recorded error for agent '{self.agent_name}': {error_type}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary.
        
        Returns:
            Dict[str, Any]: Performance metrics summary
        """
        return {
            "agent_name": self.agent_name,
            "execution_count": self.metrics.execution_count,
            "success_count": self.metrics.success_count,
            "failure_count": self.metrics.failure_count,
            "success_rate": self.metrics.success_rate,
            "failure_rate": self.metrics.failure_rate,
            "total_duration": self.metrics.total_duration,
            "avg_duration": self.metrics.avg_duration,
            "min_duration": self.metrics.min_duration,
            "max_duration": self.metrics.max_duration,
            "event_counts": dict(self.metrics.event_counts),
            "error_types": dict(self.metrics.error_types),
            "active_executions": len(self.active_executions),
            "config": {
                "timing_enabled": self.config.enable_timing,
                "memory_tracking_enabled": self.config.enable_memory_tracking,
                "event_metrics_enabled": self.config.enable_event_metrics,
                "metrics_interval": self.config.metrics_interval
            }
        }
    
    def reset_metrics(self):
        """Reset all metrics to initial state."""
        logger.info(f"Resetting metrics for agent '{self.agent_name}'")
        self.metrics = PerformanceMetrics()
        self.active_executions.clear()
        self.start_times.clear()
    
    def check_alert_thresholds(self) -> List[str]:
        """Check if any alert thresholds have been exceeded.
        
        Returns:
            List[str]: List of alert messages for exceeded thresholds
        """
        alerts = []
        
        for threshold_name, threshold_value in self.config.alert_thresholds.items():
            if threshold_name == "max_failure_rate":
                if self.metrics.failure_rate > threshold_value:
                    alerts.append(
                        f"Failure rate {self.metrics.failure_rate:.2%} exceeds threshold {threshold_value:.2%}"
                    )
            
            elif threshold_name == "max_avg_duration":
                if self.metrics.avg_duration > threshold_value:
                    alerts.append(
                        f"Average duration {self.metrics.avg_duration:.2f}s exceeds threshold {threshold_value}s"
                    )
            
            elif threshold_name == "max_concurrent_executions":
                if len(self.active_executions) > threshold_value:
                    alerts.append(
                        f"Active executions {len(self.active_executions)} exceeds threshold {int(threshold_value)}"
                    )
        
        return alerts
