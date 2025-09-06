"""Comprehensive unit tests for enhanced composition agents.

These tests verify that the enhanced agents properly inherit from ADK BaseAgent
and work correctly with the ADK framework while providing enhanced capabilities.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from typing import AsyncGenerator

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event, EventActions
from google.adk.agents.llm_agent import LlmAgent

from google_adk_extras.runners.composition import (
    EnhancedSequentialAgent,
    EnhancedParallelAgent,
    EnhancedLoopAgent,
    EnhancedWorkflowConfig,
    WorkflowExecutionMode,
    FailureHandlingMode,
    WorkflowComposer,
)
from google_adk_extras.runners.errors import YamlSystemContext


class TestAgent(BaseAgent):
    """Test agent that properly extends ADK BaseAgent for testing."""
    
    def __init__(self, name: str, should_escalate: bool = False, should_fail: bool = False, **kwargs):
        super().__init__(name=name, **kwargs)
        # Use private attributes to avoid Pydantic validation issues
        self._should_escalate = should_escalate
        self._should_fail = should_fail
        self._execution_count = 0
    
    @property
    def should_escalate(self) -> bool:
        return self._should_escalate
    
    @property
    def should_fail(self) -> bool:
        return self._should_fail
    
    @property
    def execution_count(self) -> int:
        return self._execution_count
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Simple test implementation."""
        self._execution_count += 1
        
        if self._should_fail:
            raise RuntimeError(f"Test agent {self.name} intentionally failed")
        
        # Create a test event
        actions = EventActions(escalate=self._should_escalate)
        event = Event(message=f"Test event from {self.name}", actions=actions)
        yield event
    
    async def _run_live_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Live implementation delegates to async."""
        async for event in self._run_async_impl(ctx):
            yield event


@pytest.fixture
def invocation_context():
    """Create test invocation context."""
    from unittest.mock import Mock
    
    # Create mock objects for required fields
    mock_session_service = Mock()
    mock_agent = Mock()
    mock_session = Mock()
    
    return InvocationContext(
        session_service=mock_session_service,
        invocation_id="test_invocation_123",
        agent=mock_agent,
        session=mock_session
    )


@pytest.fixture
def yaml_context():
    """Create test YAML context."""
    return YamlSystemContext(system_name="TestSystem")


class TestEnhancedSequentialAgent:
    """Test EnhancedSequentialAgent functionality."""
    
    def test_initialization(self, yaml_context):
        """Test that EnhancedSequentialAgent can be initialized properly."""
        sub_agents = [
            TestAgent("agent1"),
            TestAgent("agent2")
        ]
        
        agent = EnhancedSequentialAgent(
            name="test_sequential",
            sub_agents=sub_agents,
            yaml_context=yaml_context
        )
        
        # Verify proper initialization
        assert agent.name == "test_sequential"
        assert len(agent.sub_agents) == 2
        assert agent.enhanced_config.execution_mode == WorkflowExecutionMode.SEQUENTIAL
        assert agent.performance_monitor is not None
        assert agent.circuit_breaker is not None
    
    def test_config_type(self):
        """Test that config_type is properly set."""
        from google_adk_extras.runners.composition.enhanced_configs import EnhancedSequentialAgentConfig
        
        assert EnhancedSequentialAgent.config_type == EnhancedSequentialAgentConfig
    
    def test_basic_functionality_without_execution(self, yaml_context):
        """Test basic functionality without requiring full execution context."""
        # Create test agents
        agent1 = TestAgent("agent1")
        agent2 = TestAgent("agent2") 
        
        sequential_agent = EnhancedSequentialAgent(
            name="test_sequential",
            sub_agents=[agent1, agent2],
            yaml_context=yaml_context
        )
        
        # Verify basic setup
        assert len(sequential_agent.sub_agents) == 2
        assert sequential_agent.enhanced_config.execution_mode == WorkflowExecutionMode.SEQUENTIAL
        assert sequential_agent.performance_monitor is not None
        assert sequential_agent.circuit_breaker is not None
    
    def test_configuration_modes(self, yaml_context):
        """Test different configuration modes."""
        # Test fail-fast configuration
        config_fail_fast = EnhancedWorkflowConfig(
            execution_mode=WorkflowExecutionMode.SEQUENTIAL,
            failure_handling=FailureHandlingMode.FAIL_FAST
        )
        
        agent = EnhancedSequentialAgent(
            name="test_fail_fast",
            sub_agents=[TestAgent("agent1")],
            enhanced_config=config_fail_fast,
            yaml_context=yaml_context
        )
        
        assert agent.enhanced_config.failure_handling == FailureHandlingMode.FAIL_FAST
        
        # Test continue-on-failure configuration
        config_continue = EnhancedWorkflowConfig(
            execution_mode=WorkflowExecutionMode.SEQUENTIAL,
            failure_handling=FailureHandlingMode.CONTINUE_ON_FAILURE
        )
        
        agent2 = EnhancedSequentialAgent(
            name="test_continue",
            sub_agents=[TestAgent("agent1")],
            enhanced_config=config_continue,
            yaml_context=yaml_context
        )
        
        assert agent2.enhanced_config.failure_handling == FailureHandlingMode.CONTINUE_ON_FAILURE
    
    def test_circuit_breaker_configuration(self, yaml_context):
        """Test circuit breaker configuration."""
        config = EnhancedWorkflowConfig(
            execution_mode=WorkflowExecutionMode.SEQUENTIAL
        )
        config.circuit_breaker.failure_threshold = 5
        config.circuit_breaker.recovery_timeout = 30.0
        
        agent = EnhancedSequentialAgent(
            name="test_circuit_breaker",
            sub_agents=[TestAgent("agent1")],
            enhanced_config=config,
            yaml_context=yaml_context
        )
        
        # Test circuit breaker configuration
        assert agent.circuit_breaker.config.failure_threshold == 5
        assert agent.circuit_breaker.config.recovery_timeout == 30.0
    
    def test_performance_monitoring_configuration(self, yaml_context):
        """Test performance monitoring configuration."""
        config = EnhancedWorkflowConfig(
            execution_mode=WorkflowExecutionMode.SEQUENTIAL
        )
        config.performance_monitoring.enable_timing = True
        config.performance_monitoring.enable_event_metrics = True
        
        agent = EnhancedSequentialAgent(
            name="test_monitoring",
            sub_agents=[TestAgent("agent1")],
            enhanced_config=config,
            yaml_context=yaml_context
        )
        
        # Test performance monitor configuration
        assert agent.performance_monitor.config.enable_timing is True
        assert agent.performance_monitor.config.enable_event_metrics is True
        assert agent.performance_monitor.agent_name == "test_monitoring"


class TestEnhancedParallelAgent:
    """Test EnhancedParallelAgent functionality."""
    
    def test_initialization(self, yaml_context):
        """Test that EnhancedParallelAgent can be initialized properly."""
        sub_agents = [
            TestAgent("agent1"),
            TestAgent("agent2")
        ]
        
        agent = EnhancedParallelAgent(
            name="test_parallel",
            sub_agents=sub_agents,
            yaml_context=yaml_context
        )
        
        # Verify proper initialization
        assert agent.name == "test_parallel"
        assert len(agent.sub_agents) == 2
        assert agent.enhanced_config.execution_mode == WorkflowExecutionMode.PARALLEL
        assert agent.performance_monitor is not None
    
    def test_parallel_configuration(self, yaml_context):
        """Test parallel agent configuration."""
        # Create test agents
        agent1 = TestAgent("agent1")
        agent2 = TestAgent("agent2")
        
        parallel_agent = EnhancedParallelAgent(
            name="test_parallel",
            sub_agents=[agent1, agent2],
            yaml_context=yaml_context
        )
        
        # Verify configuration
        assert parallel_agent.enhanced_config.execution_mode == WorkflowExecutionMode.PARALLEL
        assert parallel_agent.performance_monitor is not None
        assert len(parallel_agent.sub_agents) == 2
    
    def test_empty_sub_agents(self, yaml_context):
        """Test parallel agent with no sub-agents."""
        parallel_agent = EnhancedParallelAgent(
            name="test_parallel",
            sub_agents=[],
            yaml_context=yaml_context
        )
        
        # Should handle empty sub-agents gracefully
        assert len(parallel_agent.sub_agents) == 0
        assert parallel_agent.enhanced_config.execution_mode == WorkflowExecutionMode.PARALLEL


class TestEnhancedLoopAgent:
    """Test EnhancedLoopAgent functionality."""
    
    def test_initialization(self, yaml_context):
        """Test that EnhancedLoopAgent can be initialized properly."""
        sub_agents = [TestAgent("agent1")]
        
        agent = EnhancedLoopAgent(
            name="test_loop",
            sub_agents=sub_agents,
            max_iterations=3,
            yaml_context=yaml_context
        )
        
        # Verify proper initialization
        assert agent.name == "test_loop"
        assert len(agent.sub_agents) == 1
        assert agent.max_iterations == 3
        assert agent.enhanced_config.execution_mode == WorkflowExecutionMode.LOOP
        assert agent.performance_monitor is not None
    
    def test_loop_configuration(self, yaml_context):
        """Test loop execution configuration."""
        agent1 = TestAgent("agent1")
        
        loop_agent = EnhancedLoopAgent(
            name="test_loop",
            sub_agents=[agent1],
            max_iterations=2,
            yaml_context=yaml_context
        )
        
        # Verify configuration
        assert loop_agent.max_iterations == 2
        assert loop_agent.enhanced_config.execution_mode == WorkflowExecutionMode.LOOP
        assert loop_agent.enhanced_config.max_loop_iterations == 2
        assert loop_agent.performance_monitor is not None
    
    def test_max_iterations_setting(self, yaml_context):
        """Test maximum iterations configuration."""
        # Agent with max iterations
        agent1 = TestAgent("agent1")
        
        loop_agent = EnhancedLoopAgent(
            name="test_loop", 
            sub_agents=[agent1],
            max_iterations=5,
            yaml_context=yaml_context
        )
        
        # Verify max iterations setting
        assert loop_agent.max_iterations == 5
        assert loop_agent.enhanced_config.max_loop_iterations == 5


class TestWorkflowComposer:
    """Test WorkflowComposer functionality."""
    
    def test_composer_initialization(self):
        """Test WorkflowComposer initialization."""
        composer = WorkflowComposer()
        assert composer is not None
    
    def test_sequential_builder(self, yaml_context):
        """Test creating sequential workflow with builder."""
        composer = WorkflowComposer()
        
        # Create workflow with builder
        agent = (composer
                .sequential("test_workflow")
                .add_agent(TestAgent("agent1"))
                .add_agent(TestAgent("agent2"))
                .with_failure_handling(FailureHandlingMode.CONTINUE_ON_FAILURE)
                .with_yaml_context(yaml_context)
                .build())
        
        # Verify correct type and configuration
        assert isinstance(agent, EnhancedSequentialAgent)
        assert agent.name == "test_workflow"
        assert len(agent.sub_agents) == 2
        assert agent.enhanced_config.failure_handling == FailureHandlingMode.CONTINUE_ON_FAILURE
    
    def test_parallel_builder(self, yaml_context):
        """Test creating parallel workflow with builder."""
        composer = WorkflowComposer()
        
        agent = (composer
                .parallel("test_parallel")
                .add_agents([TestAgent("agent1"), TestAgent("agent2")])
                .with_circuit_breaker(failure_threshold=5, recovery_timeout=30.0)
                .build())
        
        assert isinstance(agent, EnhancedParallelAgent)
        assert agent.name == "test_parallel"
        assert len(agent.sub_agents) == 2
        assert agent.enhanced_config.circuit_breaker.failure_threshold == 5
        assert agent.enhanced_config.circuit_breaker.recovery_timeout == 30.0
    
    def test_loop_builder(self, yaml_context):
        """Test creating loop workflow with builder."""
        composer = WorkflowComposer()
        
        agent = (composer
                .loop("test_loop")
                .add_agent(TestAgent("agent1"))
                .with_max_iterations(3)
                .with_timeout(step_timeout=10.0, total_timeout=60.0)
                .build())
        
        assert isinstance(agent, EnhancedLoopAgent)
        assert agent.name == "test_loop"
        assert agent.max_iterations == 3
        assert agent.enhanced_config.timeouts.step_timeout == 10.0
        assert agent.enhanced_config.timeouts.total_timeout == 60.0
    
    def test_simple_workflow_creation(self):
        """Test simple workflow creation methods."""
        composer = WorkflowComposer()
        
        # Create separate agents for each workflow (ADK prevents reuse)
        sequential_agents = [TestAgent("agent1"), TestAgent("agent2")]
        parallel_agents = [TestAgent("agent3"), TestAgent("agent4")] 
        loop_agents = [TestAgent("agent5"), TestAgent("agent6")]
        
        # Test simple sequential
        sequential = composer.create_simple_sequential("seq_test", sequential_agents)
        assert isinstance(sequential, EnhancedSequentialAgent)
        assert len(sequential.sub_agents) == 2
        
        # Test simple parallel
        parallel = composer.create_simple_parallel("par_test", parallel_agents)
        assert isinstance(parallel, EnhancedParallelAgent)
        assert len(parallel.sub_agents) == 2
        
        # Test simple loop
        loop = composer.create_simple_loop("loop_test", loop_agents, max_iterations=2)
        assert isinstance(loop, EnhancedLoopAgent)
        assert loop.max_iterations == 2
    
    def test_pipeline_creation(self):
        """Test pipeline workflow creation."""
        composer = WorkflowComposer()
        
        # Create pipeline with multiple stages
        stages = [
            [TestAgent("stage1_agent1")],  # Single agent stage
            [TestAgent("stage2_agent1"), TestAgent("stage2_agent2")],  # Parallel stage
            [TestAgent("stage3_agent1")]  # Single agent stage
        ]
        
        pipeline = composer.create_pipeline("test_pipeline", stages)
        assert isinstance(pipeline, EnhancedSequentialAgent)
        assert len(pipeline.sub_agents) == 3  # 3 stages
        
        # Second stage should be parallel agent
        stage2 = pipeline.sub_agents[1]
        assert isinstance(stage2, EnhancedParallelAgent)
        assert len(stage2.sub_agents) == 2


class TestIntegrationWithADKComponents:
    """Integration tests with real ADK components."""
    
    def test_enhanced_agents_inheritance(self):
        """Test that enhanced agents properly inherit from ADK BaseAgent."""
        from google.adk.agents.base_agent import BaseAgent
        
        # Test enhanced sequential agent inheritance
        agent = EnhancedSequentialAgent(
            name="integration_test",
            sub_agents=[TestAgent("test_agent")]
        )
        
        # Should inherit from BaseAgent
        assert isinstance(agent, BaseAgent)
        assert hasattr(agent, '_run_async_impl')
        assert hasattr(agent, '_run_live_impl')
        assert hasattr(agent, 'config_type')
    
    def test_config_type_inheritance(self):
        """Test that config_type properly inherits from ADK config classes."""
        from google.adk.agents.base_agent_config import BaseAgentConfig
        from google_adk_extras.runners.composition.enhanced_configs import (
            EnhancedSequentialAgentConfig,
            EnhancedParallelAgentConfig,
            EnhancedLoopAgentConfig
        )
        
        # All enhanced configs should inherit from BaseAgentConfig
        assert issubclass(EnhancedSequentialAgentConfig, BaseAgentConfig)
        assert issubclass(EnhancedParallelAgentConfig, BaseAgentConfig)
        assert issubclass(EnhancedLoopAgentConfig, BaseAgentConfig)
        
        # And should be properly set on enhanced agents
        assert EnhancedSequentialAgent.config_type == EnhancedSequentialAgentConfig
        assert EnhancedParallelAgent.config_type == EnhancedParallelAgentConfig
        assert EnhancedLoopAgent.config_type == EnhancedLoopAgentConfig


if __name__ == "__main__":
    # Run basic smoke test
    import asyncio
    
    async def smoke_test():
        """Basic smoke test to verify imports and basic functionality."""
        print("Running smoke test...")
        
        # Test imports
        from google_adk_extras.runners.composition import (
            EnhancedSequentialAgent,
            WorkflowComposer
        )
        
        # Test basic functionality
        composer = WorkflowComposer()
        agent = composer.create_simple_sequential(
            "smoke_test",
            [TestAgent("test")]
        )
        
        print(f"Created agent: {agent.name}")
        print("Smoke test passed!")
    
    asyncio.run(smoke_test())