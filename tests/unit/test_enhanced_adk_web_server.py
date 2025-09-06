"""Unit tests for EnhancedAdkWebServer."""

import pytest
import tempfile
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pathlib import Path

from google.adk.agents.base_agent import BaseAgent
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.evaluation.local_eval_sets_manager import LocalEvalSetsManager
from google.adk.evaluation.local_eval_set_results_manager import LocalEvalSetResultsManager
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from google_adk_extras.enhanced_adk_web_server import EnhancedAdkWebServer
from google_adk_extras.runners.enhanced_runner import EnhancedRunner
from google_adk_extras.runners.config import EnhancedRunConfig
from google_adk_extras.runners.errors import YamlSystemContext
from google_adk_extras.runners.strategies import (
    ToolExecutionStrategyManager,
    DefaultToolExecutionStrategy
)


class TestEnhancedAdkWebServer:
    """Test cases for EnhancedAdkWebServer class."""
    
    @pytest.fixture
    def mock_agent_loader(self):
        """Mock agent loader for testing."""
        loader = Mock()
        loader.load_agent.return_value = Mock(spec=BaseAgent)
        loader.list_agents.return_value = ["test-app"]
        return loader
    
    @pytest.fixture
    def services(self):
        """Create service instances for testing."""
        return {
            'session_service': InMemorySessionService(),
            'artifact_service': InMemoryArtifactService(),
            'memory_service': InMemoryMemoryService(),
            'credential_service': InMemoryCredentialService(),
            'eval_sets_manager': LocalEvalSetsManager("./test_evals"),
            'eval_set_results_manager': LocalEvalSetResultsManager("./test_eval_results")
        }
    
    @pytest.fixture
    def enhanced_config(self):
        """Create enhanced configuration for testing."""
        return EnhancedRunConfig.from_yaml_dict({
            'max_llm_calls': 150,
            'tool_timeouts': {'mcp_tools': 45.0},
            'debug': {'enabled': True, 'trace_tool_execution': True}
        })
    
    @pytest.fixture
    def yaml_context(self):
        """Create YAML system context for testing."""
        return YamlSystemContext(
            system_name="test-system",
            config_path="/test/config.yaml"
        )
    
    @pytest.fixture
    def tool_strategy_manager(self):
        """Create tool strategy manager for testing."""
        manager = ToolExecutionStrategyManager()
        manager.set_default_strategy(DefaultToolExecutionStrategy())
        return manager
    
    def test_initialization_basic(self, mock_agent_loader, services):
        """Test basic initialization without enhanced features."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = EnhancedAdkWebServer(
                agent_loader=mock_agent_loader,
                agents_dir=temp_dir,
                **services
            )
            
            # Should inherit all parent attributes
            assert server.agent_loader is mock_agent_loader
            assert server.agents_dir == temp_dir
            assert server.session_service is services['session_service']
            assert server.artifact_service is services['artifact_service']
            assert server.memory_service is services['memory_service']
            assert server.credential_service is services['credential_service']
            
            # Should have default enhanced features
            assert server.enhanced_config is not None
            assert isinstance(server.enhanced_config, EnhancedRunConfig)
            assert server.yaml_context is None  # Optional
            assert server.tool_strategy_manager is None  # Optional
    
    def test_initialization_with_enhanced_features(
        self, mock_agent_loader, services, enhanced_config, yaml_context, tool_strategy_manager
    ):
        """Test initialization with all enhanced features."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = EnhancedAdkWebServer(
                agent_loader=mock_agent_loader,
                agents_dir=temp_dir,
                enhanced_config=enhanced_config,
                yaml_context=yaml_context,
                tool_strategy_manager=tool_strategy_manager,
                **services
            )
            
            # Should store enhanced features
            assert server.enhanced_config is enhanced_config
            assert server.yaml_context is yaml_context
            assert server.tool_strategy_manager is tool_strategy_manager
    
    @pytest.mark.asyncio
    async def test_get_runner_async_creates_enhanced_runner(
        self, mock_agent_loader, services, enhanced_config, yaml_context, tool_strategy_manager
    ):
        """Test that get_runner_async creates EnhancedRunner instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = EnhancedAdkWebServer(
                agent_loader=mock_agent_loader,
                agents_dir=temp_dir,
                enhanced_config=enhanced_config,
                yaml_context=yaml_context,
                tool_strategy_manager=tool_strategy_manager,
                **services
            )
            
            # Mock environment loading
            with patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
                runner = await server.get_runner_async("test-app")
            
            # Should return EnhancedRunner
            assert isinstance(runner, EnhancedRunner)
            
            # Should have correct app_name and agent
            assert runner.app_name == "test-app"
            assert runner.agent is mock_agent_loader.load_agent.return_value
            
            # Should have enhanced features configured
            assert runner.enhanced_config is enhanced_config
            assert runner.yaml_context is not None
            assert runner.yaml_context.current_agent == "test-app"
            assert runner.tool_strategy_manager is tool_strategy_manager
    
    @pytest.mark.asyncio
    async def test_get_runner_async_caching(self, mock_agent_loader, services):
        """Test that runners are cached properly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = EnhancedAdkWebServer(
                agent_loader=mock_agent_loader,
                agents_dir=temp_dir,
                **services
            )
            
            with patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
                # First call should create runner
                runner1 = await server.get_runner_async("test-app")
                
                # Second call should return cached runner
                runner2 = await server.get_runner_async("test-app")
                
                # Should be the same instance
                assert runner1 is runner2
                
                # Agent loader should only be called once
                mock_agent_loader.load_agent.assert_called_once_with("test-app")
    
    @pytest.mark.asyncio
    async def test_get_runner_async_cleanup_handling(self, mock_agent_loader, services):
        """Test runner cleanup handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = EnhancedAdkWebServer(
                agent_loader=mock_agent_loader,
                agents_dir=temp_dir,
                **services
            )
            
            with patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'), \
                 patch('google_adk_extras.enhanced_adk_web_server.cleanup.close_runners') as mock_cleanup:
                
                # Create initial runner
                runner1 = await server.get_runner_async("test-app")
                
                # Mark for cleanup
                server.runners_to_clean.add("test-app")
                
                # Get runner again - should cleanup old one and create new
                runner2 = await server.get_runner_async("test-app")
                
                # Should be different instances
                assert runner1 is not runner2
                
                # Should have called cleanup
                mock_cleanup.assert_called_once_with([runner1])
                
                # runners_to_clean should be empty
                assert "test-app" not in server.runners_to_clean
    
    @pytest.mark.asyncio
    async def test_get_runner_async_yaml_context_creation(self, mock_agent_loader, services):
        """Test YAML context creation when not provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = EnhancedAdkWebServer(
                agent_loader=mock_agent_loader,
                agents_dir=temp_dir,
                **services
            )
            
            with patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
                runner = await server.get_runner_async("test-app")
            
            # Should create default YAML context
            assert runner.yaml_context is not None
            assert runner.yaml_context.system_name == "test-app"
            assert runner.yaml_context.current_agent == "test-app"
    
    @pytest.mark.asyncio 
    async def test_get_runner_async_yaml_context_with_agent(
        self, mock_agent_loader, services, yaml_context
    ):
        """Test YAML context enhancement with agent info."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = EnhancedAdkWebServer(
                agent_loader=mock_agent_loader,
                agents_dir=temp_dir,
                yaml_context=yaml_context,
                **services
            )
            
            with patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
                runner = await server.get_runner_async("test-app")
            
            # Should have enhanced YAML context with agent info
            assert runner.yaml_context is not None
            assert runner.yaml_context.system_name == "test-system"  # Original
            assert runner.yaml_context.current_agent == "test-app"     # Added
    
    @pytest.mark.asyncio
    async def test_multiple_apps_different_runners(self, mock_agent_loader, services):
        """Test that different apps get different runners."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = EnhancedAdkWebServer(
                agent_loader=mock_agent_loader,
                agents_dir=temp_dir,
                **services
            )
            
            with patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
                runner1 = await server.get_runner_async("app1")
                runner2 = await server.get_runner_async("app2")
                
                # Should be different instances
                assert runner1 is not runner2
                assert runner1.app_name == "app1"
                assert runner2.app_name == "app2"
                
                # Should both be cached
                assert "app1" in server.runner_dict
                assert "app2" in server.runner_dict
    
    def test_inheritance_from_adk_web_server(self, mock_agent_loader, services):
        """Test that EnhancedAdkWebServer properly inherits from AdkWebServer."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = EnhancedAdkWebServer(
                agent_loader=mock_agent_loader,
                agents_dir=temp_dir,
                **services
            )
            
            # Should inherit parent attributes and methods
            assert hasattr(server, 'runners_to_clean')
            assert hasattr(server, 'current_app_name_ref') 
            assert hasattr(server, 'runner_dict')
            assert hasattr(server, 'get_fast_api_app')
            
            # Should be instance of parent class
            from google.adk.cli.adk_web_server import AdkWebServer
            assert isinstance(server, AdkWebServer)


class TestEnhancedAdkWebServerIntegration:
    """Integration test cases for EnhancedAdkWebServer."""
    
    @pytest.fixture
    def complete_server(self):
        """Create fully configured EnhancedAdkWebServer."""
        agent_loader = Mock()
        agent_loader.load_agent.return_value = Mock(spec=BaseAgent)
        agent_loader.list_agents.return_value = ["test-app"]
        
        enhanced_config = EnhancedRunConfig.from_yaml_dict({
            'max_llm_calls': 100,
            'tool_timeouts': {'mcp_tools': 30.0}
        })
        
        yaml_context = YamlSystemContext(system_name="integration-test")
        
        tool_strategy_manager = ToolExecutionStrategyManager()
        tool_strategy_manager.set_default_strategy(DefaultToolExecutionStrategy())
        
        with tempfile.TemporaryDirectory() as temp_dir:
            server = EnhancedAdkWebServer(
                agent_loader=agent_loader,
                agents_dir=temp_dir,
                session_service=InMemorySessionService(),
                artifact_service=InMemoryArtifactService(),
                memory_service=InMemoryMemoryService(),
                credential_service=InMemoryCredentialService(),
                eval_sets_manager=LocalEvalSetsManager("./test_evals"),
                eval_set_results_manager=LocalEvalSetResultsManager("./test_eval_results"),
                enhanced_config=enhanced_config,
                yaml_context=yaml_context,
                tool_strategy_manager=tool_strategy_manager
            )
            yield server
    
    @pytest.mark.asyncio
    async def test_fastapi_app_creation(self, complete_server):
        """Test that FastAPI app can be created successfully."""
        with patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
            # Should be able to create FastAPI app
            app = complete_server.get_fast_api_app()
            
            assert app is not None
            # Should have all the standard ADK routes
            route_paths = {route.path for route in app.routes}
            assert "/list-apps" in route_paths
            assert "/run" in route_paths
            assert "/run_sse" in route_paths
    
    @pytest.mark.asyncio
    async def test_enhanced_runner_features_work(self, complete_server):
        """Test that enhanced runner features are accessible."""
        with patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
            runner = await complete_server.get_runner_async("test-app")
            
            # Should have performance metrics
            assert hasattr(runner, 'performance_metrics')
            
            # Should have tool strategy manager
            assert runner.tool_strategy_manager is not None
            
            # Should have enhanced config
            assert runner.enhanced_config.base_config.max_llm_calls == 100
            assert runner.enhanced_config.tool_timeouts.mcp_tools == 30.0
            
            # Should have YAML context
            assert runner.yaml_context.system_name == "integration-test"
            assert runner.yaml_context.current_agent == "test-app"