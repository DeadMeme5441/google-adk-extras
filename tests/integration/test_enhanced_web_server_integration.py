"""Integration tests for EnhancedAdkWebServer with FastAPI.

These tests verify that EnhancedAdkWebServer properly integrates with FastAPI
and that all enhanced runner features work correctly in the web server context.
"""

import pytest
import tempfile
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from google.adk.agents.base_agent import BaseAgent
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.evaluation.local_eval_sets_manager import LocalEvalSetsManager
from google.adk.evaluation.local_eval_set_results_manager import LocalEvalSetResultsManager
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app
from google_adk_extras.enhanced_adk_web_server import EnhancedAdkWebServer
from google_adk_extras.runners.enhanced_runner import EnhancedRunner
from google_adk_extras.runners.config import EnhancedRunConfig
from google_adk_extras.runners.errors import YamlSystemContext
from google_adk_extras.runners.strategies import (
    ToolExecutionStrategyManager,
    DefaultToolExecutionStrategy
)


class TestEnhancedWebServerIntegration:
    """Integration tests for EnhancedAdkWebServer with FastAPI."""
    
    @pytest.fixture
    def mock_agent_loader(self):
        """Create mock agent loader."""
        loader = Mock()
        agent = Mock(spec=BaseAgent)
        agent.name = "test-agent"
        loader.load_agent.return_value = agent
        loader.list_agents.return_value = ["test-app"]
        return loader
    
    @pytest.fixture
    def enhanced_config(self):
        """Create enhanced configuration."""
        return EnhancedRunConfig.from_yaml_dict({
            'max_llm_calls': 200,
            'tool_timeouts': {
                'mcp_tools': 45.0,
                'openapi_tools': 90.0,
                'function_tools': 15.0
            },
            'retry_policies': {
                'default': {
                    'max_attempts': 3,
                    'base_delay': 1.0,
                    'strategy': 'exponential_backoff'
                }
            },
            'debug': {
                'enabled': True,
                'trace_tool_execution': True,
                'performance_profiling': True
            },
            'enable_circuit_breaker': True,
            'max_concurrent_tools': 10
        })
    
    @pytest.fixture
    def yaml_context(self):
        """Create YAML system context."""
        return YamlSystemContext(
            system_name="integration-test-system",
            config_path="/test/integration/config.yaml"
        )
    
    @pytest.fixture
    def tool_strategy_manager(self):
        """Create tool strategy manager."""
        manager = ToolExecutionStrategyManager()
        manager.set_default_strategy(DefaultToolExecutionStrategy(timeout=30.0))
        return manager
    
    @pytest.fixture
    def services(self):
        """Create service configuration for FastAPI."""
        return {
            'credential_service': InMemoryCredentialService(),
        }
    
    @pytest.fixture
    def direct_services(self):
        """Create service instances for direct server tests."""
        return {
            'session_service': InMemorySessionService(),
            'artifact_service': InMemoryArtifactService(),
            'memory_service': InMemoryMemoryService(),
            'credential_service': InMemoryCredentialService(),
            'eval_sets_manager': LocalEvalSetsManager("./test_evals"),
            'eval_set_results_manager': LocalEvalSetResultsManager("./test_eval_results")
        }
    
    def test_enhanced_fastapi_app_creation(
        self, mock_agent_loader, services, enhanced_config, yaml_context, tool_strategy_manager
    ):
        """Test that FastAPI app can be created with enhanced features."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('google_adk_extras.enhanced_fastapi.envs.load_dotenv_for_agent'):
                app = get_enhanced_fast_api_app(
                    agent_loader=mock_agent_loader,
                    agents_dir=temp_dir,
                    enhanced_config=enhanced_config,
                    yaml_context=yaml_context,
                    tool_strategy_manager=tool_strategy_manager,
                    **services
                )
                
                # Should be a FastAPI app
                assert isinstance(app, FastAPI)
                
                # Should have standard ADK routes
                route_paths = {route.path for route in app.routes}
                assert "/list-apps" in route_paths
                assert "/run" in route_paths
                assert "/run_sse" in route_paths
    
    def test_enhanced_runner_created_through_fastapi(
        self, mock_agent_loader, services, enhanced_config, yaml_context, tool_strategy_manager
    ):
        """Test that EnhancedRunner is created when accessing through FastAPI."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('google_adk_extras.enhanced_fastapi.envs.load_dotenv_for_agent'), \
                 patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
                
                # Create FastAPI app
                app = get_enhanced_fast_api_app(
                    agent_loader=mock_agent_loader,
                    agents_dir=temp_dir,
                    enhanced_config=enhanced_config,
                    yaml_context=yaml_context,
                    tool_strategy_manager=tool_strategy_manager,
                    **services
                )
                
                # Get the underlying ADK web server
                adk_server = app.state.adk_web_server
                assert isinstance(adk_server, EnhancedAdkWebServer)
                
                # Test runner creation (async operation)
                async def test_runner_creation():
                    runner = await adk_server.get_runner_async("test-app")
                    
                    # Should be EnhancedRunner
                    assert isinstance(runner, EnhancedRunner)
                    
                    # Should have enhanced configuration
                    assert runner.enhanced_config is enhanced_config
                    assert runner.enhanced_config.base_config.max_llm_calls == 200
                    assert runner.enhanced_config.tool_timeouts.mcp_tools == 45.0
                    assert runner.enhanced_config.enable_circuit_breaker is True
                    
                    # Should have YAML context
                    assert runner.yaml_context is not None
                    assert runner.yaml_context.system_name == "integration-test-system"
                    assert runner.yaml_context.current_agent == "test-app"
                    
                    # Should have tool strategy manager
                    assert runner.tool_strategy_manager is tool_strategy_manager
                    
                    # Should have performance metrics
                    assert hasattr(runner, 'performance_metrics')
                    metrics = runner.performance_metrics
                    assert isinstance(metrics, dict)
                    assert 'total_invocations' in metrics
                    assert 'error_rate' in metrics
                    
                    return runner
                
                # Run the async test
                runner = asyncio.run(test_runner_creation())
                assert runner is not None
    
    def test_fastapi_list_apps_endpoint(
        self, mock_agent_loader, services, enhanced_config
    ):
        """Test that list-apps endpoint works with enhanced server."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('google_adk_extras.enhanced_fastapi.envs.load_dotenv_for_agent'):
                app = get_enhanced_fast_api_app(
                    agent_loader=mock_agent_loader,
                    agents_dir=temp_dir,
                    enhanced_config=enhanced_config,
                    **services
                )
                
                client = TestClient(app)
                response = client.get("/list-apps")
                
                assert response.status_code == 200
                data = response.json()
                # The response is a list of apps directly
                assert "test-app" in data
    
    @pytest.mark.asyncio
    async def test_enhanced_config_propagation(
        self, mock_agent_loader, direct_services, enhanced_config, yaml_context, tool_strategy_manager
    ):
        """Test that enhanced configuration is properly propagated through the system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('google_adk_extras.enhanced_fastapi.envs.load_dotenv_for_agent'), \
                 patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
                
                # Create enhanced server directly
                server = EnhancedAdkWebServer(
                    agent_loader=mock_agent_loader,
                    agents_dir=temp_dir,
                    enhanced_config=enhanced_config,
                    yaml_context=yaml_context,
                    tool_strategy_manager=tool_strategy_manager,
                    **direct_services
                )
                
                # Create runner
                runner = await server.get_runner_async("test-app")
                
                # Verify enhanced config features
                config = runner.enhanced_config
                
                # Basic ADK config
                assert config.base_config.max_llm_calls == 200
                
                # Tool timeouts
                assert config.tool_timeouts.mcp_tools == 45.0
                assert config.tool_timeouts.openapi_tools == 90.0
                assert config.tool_timeouts.function_tools == 15.0
                
                # Test timeout retrieval methods
                assert config.get_tool_timeout("some_mcp_tool", "mcp") == 45.0
                assert config.get_tool_timeout("some_api_tool", "openapi") == 90.0
                assert config.get_tool_timeout("some_func", "function") == 15.0
                
                # Retry policies
                default_retry = config.get_retry_config("default")
                assert default_retry.max_attempts == 3
                assert default_retry.base_delay == 1.0
                
                # Debug config
                assert config.debug_config.enabled is True
                assert config.debug_config.trace_tool_execution is True
                assert config.debug_config.performance_profiling is True
                
                # Circuit breaker
                assert config.enable_circuit_breaker is True
                
                # Performance settings
                assert config.max_concurrent_tools == 10
    
    @pytest.mark.asyncio
    async def test_yaml_context_propagation(
        self, mock_agent_loader, direct_services, yaml_context
    ):
        """Test that YAML context is properly propagated and modified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
                
                server = EnhancedAdkWebServer(
                    agent_loader=mock_agent_loader,
                    agents_dir=temp_dir,
                    yaml_context=yaml_context,
                    **direct_services
                )
                
                # Create runners for different apps
                runner1 = await server.get_runner_async("app1")
                runner2 = await server.get_runner_async("app2")
                
                # Each should have its own context with correct agent
                assert runner1.yaml_context.system_name == "integration-test-system"
                assert runner1.yaml_context.current_agent == "app1"
                
                assert runner2.yaml_context.system_name == "integration-test-system"
                assert runner2.yaml_context.current_agent == "app2"
                
                # Contexts should be independent
                assert runner1.yaml_context is not runner2.yaml_context
    
    def test_backward_compatibility_with_standard_adk(
        self, mock_agent_loader, services
    ):
        """Test that enhanced server maintains backward compatibility."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('google_adk_extras.enhanced_fastapi.envs.load_dotenv_for_agent'):
                
                # Create app with minimal configuration (like standard ADK)
                app = get_enhanced_fast_api_app(
                    agent_loader=mock_agent_loader,
                    agents_dir=temp_dir,
                    **services
                    # No enhanced features provided
                )
                
                # Should still create a working FastAPI app
                assert isinstance(app, FastAPI)
                
                # Should have standard ADK routes
                route_paths = {route.path for route in app.routes}
                assert "/list-apps" in route_paths
                assert "/run" in route_paths
                
                # Should create enhanced server with defaults
                adk_server = app.state.adk_web_server
                assert isinstance(adk_server, EnhancedAdkWebServer)
                assert isinstance(adk_server.enhanced_config, EnhancedRunConfig)
    
    @pytest.mark.asyncio
    async def test_runner_caching_works_correctly(
        self, mock_agent_loader, direct_services, enhanced_config
    ):
        """Test that runner caching works correctly with enhanced features."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
                
                server = EnhancedAdkWebServer(
                    agent_loader=mock_agent_loader,
                    agents_dir=temp_dir,
                    enhanced_config=enhanced_config,
                    **direct_services
                )
                
                # First call should create runner
                runner1 = await server.get_runner_async("test-app")
                
                # Second call should return cached runner
                runner2 = await server.get_runner_async("test-app")
                
                # Should be the same instance
                assert runner1 is runner2
                
                # Should maintain enhanced features
                assert isinstance(runner1, EnhancedRunner)
                assert runner1.enhanced_config is enhanced_config
                
                # Agent loader should only be called once
                mock_agent_loader.load_agent.assert_called_once_with("test-app")
    
    def test_enhanced_fastapi_parameters_handling(
        self, mock_agent_loader, services, enhanced_config, yaml_context, tool_strategy_manager
    ):
        """Test that enhanced FastAPI parameters are handled correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('google_adk_extras.enhanced_fastapi.envs.load_dotenv_for_agent'):
                
                # Test with all enhanced parameters
                app = get_enhanced_fast_api_app(
                    agent_loader=mock_agent_loader,
                    agents_dir=temp_dir,
                    enhanced_config=enhanced_config,
                    yaml_context=yaml_context,
                    tool_strategy_manager=tool_strategy_manager,
                    **services
                )
                
                # Verify server has correct configuration
                server = app.state.adk_web_server
                assert server.enhanced_config is enhanced_config
                assert server.yaml_context is yaml_context
                assert server.tool_strategy_manager is tool_strategy_manager
                
                # Test with partial parameters
                app2 = get_enhanced_fast_api_app(
                    agent_loader=mock_agent_loader,
                    agents_dir=temp_dir,
                    enhanced_config=enhanced_config,  # Only enhanced config
                    **services
                )
                
                server2 = app2.state.adk_web_server
                assert server2.enhanced_config is enhanced_config
                assert server2.yaml_context is None  # Should be None
                assert server2.tool_strategy_manager is None  # Should be None


class TestEnhancedWebServerErrorHandling:
    """Test error handling in enhanced web server integration."""
    
    @pytest.fixture
    def mock_agent_loader(self):
        """Create mock agent loader that can simulate errors."""
        loader = Mock()
        agent = Mock(spec=BaseAgent)
        agent.name = "test-agent"
        loader.load_agent.return_value = agent
        loader.list_agents.return_value = ["test-app"]
        return loader
    
    @pytest.fixture
    def services(self):
        """Create services."""
        return {
            'credential_service': InMemoryCredentialService(),
        }
    
    @pytest.fixture
    def direct_services(self):
        """Create service instances for direct server tests."""
        return {
            'session_service': InMemorySessionService(),
            'artifact_service': InMemoryArtifactService(),
            'memory_service': InMemoryMemoryService(),
            'credential_service': InMemoryCredentialService(),
            'eval_sets_manager': LocalEvalSetsManager("./test_evals"),
            'eval_set_results_manager': LocalEvalSetResultsManager("./test_eval_results")
        }
    
    @pytest.mark.asyncio
    async def test_agent_loading_error_handling(self, mock_agent_loader, direct_services):
        """Test error handling when agent loading fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
                
                # Make agent loader raise exception
                mock_agent_loader.load_agent.side_effect = Exception("Agent not found")
                
                server = EnhancedAdkWebServer(
                    agent_loader=mock_agent_loader,
                    agents_dir=temp_dir,
                    **direct_services
                )
                
                # Should raise the original exception
                with pytest.raises(Exception, match="Agent not found"):
                    await server.get_runner_async("missing-app")
    
    def test_invalid_enhanced_config_handling(self, mock_agent_loader, services):
        """Test handling of invalid enhanced configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('google_adk_extras.enhanced_fastapi.envs.load_dotenv_for_agent'):
                
                # Test with invalid config data
                with pytest.raises(Exception):  # Should raise validation error
                    EnhancedRunConfig.from_yaml_dict({
                        'max_llm_calls': "invalid",  # Should be int
                        'tool_timeouts': "invalid"   # Should be dict
                    })