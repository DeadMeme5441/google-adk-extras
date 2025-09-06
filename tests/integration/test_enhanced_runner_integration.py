"""Integration tests for enhanced composition agents with existing EnhancedRunner.

This test verifies that the new enhanced composition agents (Phase 1) work
properly with the existing EnhancedRunner infrastructure, including:
- Performance monitoring and metrics
- YAML system context and error handling  
- Tool execution strategies
- Enhanced configuration systems
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from typing import AsyncGenerator

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event, EventActions
from google.adk.sessions.base_session_service import BaseSessionService
from google.genai import types

from google_adk_extras.runners.enhanced_runner import EnhancedRunner
from google_adk_extras.runners.config import EnhancedRunConfig
from google_adk_extras.runners.errors import YamlSystemContext
from google_adk_extras.runners.composition import (
    EnhancedSequentialAgent,
    EnhancedParallelAgent, 
    EnhancedLoopAgent,
    WorkflowComposer,
    EnhancedWorkflowConfig,
    WorkflowExecutionMode,
    FailureHandlingMode,
)


class TestIntegrationAgent(BaseAgent):
    """Test agent for integration testing with EnhancedRunner."""
    
    def __init__(self, name: str, message_content: str = None, should_fail: bool = False, **kwargs):
        super().__init__(name=name, **kwargs)
        self._message_content = message_content or f"Response from {name}"
        self._should_fail = should_fail
        self._execution_count = 0
    
    @property
    def execution_count(self) -> int:
        return self._execution_count
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Test implementation that generates events."""
        self._execution_count += 1
        
        if self._should_fail:
            raise RuntimeError(f"Test agent {self.name} intentionally failed")
        
        # Generate test event
        actions = EventActions()
        event = Event(message=self._message_content, actions=actions)
        yield event
    
    async def _run_live_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Live implementation delegates to async."""
        async for event in self._run_async_impl(ctx):
            yield event


@pytest.fixture
def mock_session_service():
    """Create mock session service for testing."""
    mock_service = Mock(spec=BaseSessionService)
    mock_service.initialize = AsyncMock()
    return mock_service


@pytest.fixture  
def yaml_context():
    """Create test YAML context."""
    return YamlSystemContext(
        system_name="integration-test-system",
        config_path="test_config.yaml"
    )


@pytest.fixture
def enhanced_config():
    """Create test enhanced configuration.""" 
    return EnhancedRunConfig.from_yaml_dict({
        'max_llm_calls': 50,
        'debug': {'enabled': True},
        'tool_timeouts': {
            'mcp_tools': 15.0,
            'function_tools': 5.0
        }
    })


class TestEnhancedRunnerWithCompositionAgents:
    """Test enhanced composition agents with EnhancedRunner."""
    
    @pytest.mark.asyncio
    async def test_enhanced_sequential_agent_with_runner(
        self, mock_session_service, yaml_context, enhanced_config
    ):
        """Test EnhancedSequentialAgent works with EnhancedRunner."""
        # Create sub-agents
        agent1 = TestIntegrationAgent("agent1", "Message from agent 1")
        agent2 = TestIntegrationAgent("agent2", "Message from agent 2")
        
        # Create enhanced sequential agent
        sequential_agent = EnhancedSequentialAgent(
            name="test_sequential_agent",
            sub_agents=[agent1, agent2],
            yaml_context=yaml_context
        )
        
        # Create enhanced runner with the sequential agent
        runner = EnhancedRunner(
            app_name="integration-test",
            agent=sequential_agent,
            session_service=mock_session_service,
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Verify runner is properly configured
        assert runner.app_name == "integration-test"
        assert runner.agent == sequential_agent
        assert runner.enhanced_config == enhanced_config
        assert runner.yaml_context.system_name == "integration-test-system"
        assert runner.tool_strategy_manager is not None
        
        # Verify performance metrics are initialized
        metrics = runner.get_performance_metrics()
        assert metrics['total_invocations'] == 0
        assert metrics['error_count'] == 0
        assert metrics['success_rate'] == 0.0
    
    @pytest.mark.asyncio
    async def test_enhanced_parallel_agent_with_runner(
        self, mock_session_service, yaml_context, enhanced_config
    ):
        """Test EnhancedParallelAgent works with EnhancedRunner."""
        # Create sub-agents
        agent1 = TestIntegrationAgent("parallel_agent1", "Parallel message 1")
        agent2 = TestIntegrationAgent("parallel_agent2", "Parallel message 2")
        
        # Create enhanced parallel agent
        parallel_agent = EnhancedParallelAgent(
            name="test_parallel_agent",
            sub_agents=[agent1, agent2],
            yaml_context=yaml_context
        )
        
        # Create enhanced runner
        runner = EnhancedRunner(
            app_name="parallel-test",
            agent=parallel_agent,
            session_service=mock_session_service,
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Verify integration
        assert runner.agent == parallel_agent
        assert isinstance(runner.agent, EnhancedParallelAgent)
        assert runner.agent.enhanced_config.execution_mode == WorkflowExecutionMode.PARALLEL
        
        # Verify the agent's monitoring systems are configured
        assert parallel_agent.performance_monitor is not None
        assert parallel_agent.circuit_breaker is not None
    
    @pytest.mark.asyncio
    async def test_enhanced_loop_agent_with_runner(
        self, mock_session_service, yaml_context, enhanced_config  
    ):
        """Test EnhancedLoopAgent works with EnhancedRunner."""
        # Create sub-agent
        loop_agent_sub = TestIntegrationAgent("loop_sub_agent", "Loop iteration message")
        
        # Create enhanced loop agent
        loop_agent = EnhancedLoopAgent(
            name="test_loop_agent",
            sub_agents=[loop_agent_sub],
            max_iterations=3,
            yaml_context=yaml_context
        )
        
        # Create enhanced runner
        runner = EnhancedRunner(
            app_name="loop-test", 
            agent=loop_agent,
            session_service=mock_session_service,
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Verify integration
        assert runner.agent == loop_agent
        assert isinstance(runner.agent, EnhancedLoopAgent)
        assert runner.agent.max_iterations == 3
        assert runner.agent.enhanced_config.execution_mode == WorkflowExecutionMode.LOOP
    
    @pytest.mark.asyncio
    async def test_workflow_composer_agents_with_runner(
        self, mock_session_service, yaml_context, enhanced_config
    ):
        """Test WorkflowComposer-created agents work with EnhancedRunner."""
        # Create composer and build a complex workflow
        composer = WorkflowComposer()
        
        # Build sequential workflow with composer
        workflow_agent = (composer
                         .sequential("complex_workflow")
                         .add_agent(TestIntegrationAgent("step1", "Step 1 complete"))
                         .add_agent(TestIntegrationAgent("step2", "Step 2 complete"))
                         .with_failure_handling(FailureHandlingMode.CONTINUE_ON_FAILURE)
                         .with_yaml_context(yaml_context)
                         .build())
        
        # Create enhanced runner with composed workflow
        runner = EnhancedRunner(
            app_name="workflow-test",
            agent=workflow_agent,
            session_service=mock_session_service, 
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Verify integration
        assert isinstance(runner.agent, EnhancedSequentialAgent)
        assert runner.agent.name == "complex_workflow"
        assert len(runner.agent.sub_agents) == 2
        assert runner.agent.enhanced_config.failure_handling == FailureHandlingMode.CONTINUE_ON_FAILURE
    
    @pytest.mark.asyncio
    async def test_runner_debug_info_with_enhanced_agents(
        self, mock_session_service, yaml_context, enhanced_config
    ):
        """Test EnhancedRunner debug info includes enhanced agent details."""
        # Create enhanced agent
        agent = EnhancedSequentialAgent(
            name="debug_test_agent",
            sub_agents=[TestIntegrationAgent("debug_sub", "Debug message")],
            yaml_context=yaml_context
        )
        
        # Create runner
        runner = EnhancedRunner(
            app_name="debug-test",
            agent=agent,
            session_service=mock_session_service,
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Get debug info
        debug_info = runner.get_debug_info()
        
        # Verify debug info includes enhanced runner details
        assert debug_info['runner_type'] == 'EnhancedRunner'
        assert debug_info['app_name'] == 'debug-test'
        assert debug_info['yaml_context']['system_name'] == 'integration-test-system'
        assert debug_info['enhanced_config']['debug_enabled'] is True
        assert 'performance_metrics' in debug_info
        assert 'tool_strategies' in debug_info
        
        # Verify tool strategies are configured
        assert 'mcp' in debug_info['tool_strategies']
        assert 'openapi' in debug_info['tool_strategies']
        assert 'function' in debug_info['tool_strategies']
    
    def test_runner_repr_with_enhanced_agents(
        self, mock_session_service, yaml_context, enhanced_config
    ):
        """Test EnhancedRunner string representation with enhanced agents."""
        agent = EnhancedParallelAgent(
            name="repr_test_agent",
            sub_agents=[TestIntegrationAgent("repr_sub", "Repr message")],
            yaml_context=yaml_context
        )
        
        runner = EnhancedRunner(
            app_name="repr-test",
            agent=agent,
            session_service=mock_session_service,
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        repr_str = repr(runner)
        
        # Verify representation includes key information
        assert "EnhancedRunner" in repr_str
        assert "repr-test" in repr_str
        assert "integration-test-system" in repr_str
        assert "repr_test_agent" in repr_str
        assert "invocations=0" in repr_str
    
    @pytest.mark.asyncio
    async def test_enhanced_config_updates_with_composed_agents(
        self, mock_session_service, yaml_context
    ):
        """Test enhanced config updates work with composed agents."""
        # Create agent 
        agent = EnhancedSequentialAgent(
            name="config_update_agent",
            sub_agents=[TestIntegrationAgent("config_sub", "Config message")],
            yaml_context=yaml_context
        )
        
        # Create runner with initial config
        initial_config = EnhancedRunConfig.from_yaml_dict({
            'max_llm_calls': 10,
            'tool_timeouts': {'mcp_tools': 5.0}
        })
        
        runner = EnhancedRunner(
            app_name="config-update-test",
            agent=agent,
            session_service=mock_session_service,
            enhanced_config=initial_config,
            yaml_context=yaml_context
        )
        
        # Verify initial state
        assert runner.enhanced_config.base_config.max_llm_calls == 10
        
        # Update config
        updated_config = EnhancedRunConfig.from_yaml_dict({
            'max_llm_calls': 20,
            'tool_timeouts': {'mcp_tools': 10.0}
        })
        
        runner.update_enhanced_config(updated_config)
        
        # Verify config was updated
        assert runner.enhanced_config.base_config.max_llm_calls == 20
        assert runner.tool_strategy_manager is not None  # Should be recreated
    
    @pytest.mark.asyncio  
    async def test_yaml_config_merge_with_enhanced_agents(
        self, mock_session_service, yaml_context, enhanced_config
    ):
        """Test YAML config merging works with enhanced agents."""
        agent = EnhancedLoopAgent(
            name="yaml_merge_agent",
            sub_agents=[TestIntegrationAgent("yaml_sub", "YAML message")],
            max_iterations=2,
            yaml_context=yaml_context
        )
        
        runner = EnhancedRunner(
            app_name="yaml-merge-test",
            agent=agent,
            session_service=mock_session_service,
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Merge additional YAML config
        yaml_config = {
            'max_llm_calls': 100,
            'debug': {'enabled': False},
            'tool_timeouts': {'function_tools': 15.0}
        }
        
        runner.merge_config_from_yaml(yaml_config)
        
        # Verify config was merged
        assert runner.enhanced_config.base_config.max_llm_calls == 100
        assert runner.enhanced_config.debug_config.enabled is False


class TestEnhancedAgentErrorHandling:
    """Test error handling integration between enhanced agents and runner."""
    
    @pytest.mark.asyncio
    async def test_enhanced_agent_failure_with_runner_error_handling(
        self, mock_session_service, yaml_context, enhanced_config
    ):
        """Test that enhanced agent failures are properly handled by runner."""
        # Create failing agent
        failing_agent = TestIntegrationAgent("failing_agent", should_fail=True)
        
        # Create enhanced sequential agent with failing sub-agent
        sequential_agent = EnhancedSequentialAgent(
            name="error_test_sequential",
            sub_agents=[failing_agent],
            enhanced_config=EnhancedWorkflowConfig(
                execution_mode=WorkflowExecutionMode.SEQUENTIAL,
                failure_handling=FailureHandlingMode.FAIL_FAST
            ),
            yaml_context=yaml_context
        )
        
        # Create runner
        runner = EnhancedRunner(
            app_name="error-test",
            agent=sequential_agent, 
            session_service=mock_session_service,
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Verify runner and agent are properly connected
        assert runner.agent == sequential_agent
        assert runner.yaml_context.system_name == "integration-test-system"
        
        # The error handling will be tested more thoroughly in execution tests
        # For now, verify the setup is correct
        assert sequential_agent.enhanced_config.failure_handling == FailureHandlingMode.FAIL_FAST


if __name__ == "__main__":
    # Run basic smoke test
    async def smoke_test():
        print("Running integration smoke test...")
        
        # Create test components
        mock_session = Mock(spec=BaseSessionService)
        mock_session.initialize = AsyncMock()
        
        context = YamlSystemContext(system_name="smoke-test")
        config = EnhancedRunConfig()
        
        # Create enhanced agent
        agent = EnhancedSequentialAgent(
            name="smoke_agent", 
            sub_agents=[TestIntegrationAgent("smoke_sub")]
        )
        
        # Create runner
        runner = EnhancedRunner(
            app_name="smoke-test",
            agent=agent,
            session_service=mock_session,
            enhanced_config=config,
            yaml_context=context
        )
        
        print(f"Created runner: {runner}")
        print(f"Performance metrics: {runner.get_performance_metrics()}")
        print("Smoke test passed!")
    
    asyncio.run(smoke_test())