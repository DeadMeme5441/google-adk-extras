"""Unit tests for EnhancedAdkWebServer (slim scope)."""

import pytest
import tempfile
from unittest.mock import Mock, patch

from google.adk.agents.base_agent import BaseAgent
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from google_adk_extras.enhanced_adk_web_server import EnhancedAdkWebServer
from google_adk_extras.enhanced_runner import EnhancedRunner


class TestEnhancedAdkWebServer:
    """Basic tests for EnhancedAdkWebServer class."""
    
    @pytest.fixture
    def mock_agent_loader(self):
        """Mock agent loader for testing."""
        loader = Mock()
        loader.load_agent.return_value = Mock(spec=BaseAgent)
        loader.list_agents.return_value = ["test-app"]
        return loader
    
    @pytest.fixture
    def services(self):
        """Create minimal service instances for testing."""
        return {
            'session_service': InMemorySessionService(),
            'artifact_service': InMemoryArtifactService(),
            'memory_service': InMemoryMemoryService(),
            # credential_service intentionally omitted to test defaulting
            'eval_sets_manager': Mock(),
            'eval_set_results_manager': Mock(),
        }
    
    def test_initialization_basic(self, mock_agent_loader, services):
        """Test basic initialization (credential service defaults)."""
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
            # Should have defaulted credential service
            assert isinstance(server.credential_service, InMemoryCredentialService)
    
    
    @pytest.mark.asyncio
    async def test_get_runner_async_creates_enhanced_runner(
        self, mock_agent_loader, services
    ):
        """Test get_runner_async creates EnhancedRunner instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = EnhancedAdkWebServer(
                agent_loader=mock_agent_loader,
                agents_dir=temp_dir,
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
            # EnhancedRunner is a thin wrapper; no extra attrs asserted
    
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
    async def test_multiple_apps_different_runners(self, mock_agent_loader, services):
        """Test that different apps get different runners and cached."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = EnhancedAdkWebServer(
                agent_loader=mock_agent_loader,
                agents_dir=temp_dir,
                **services
            )
            with patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
                r1 = await server.get_runner_async("app1")
                r2 = await server.get_runner_async("app2")
                assert r1 is not r2
                assert "app1" in server.runner_dict and "app2" in server.runner_dict
    
    
    
    
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
    @pytest.mark.asyncio
    async def test_fastapi_app_creation(self):
        agent_loader = Mock()
        agent_loader.load_agent.return_value = Mock(spec=BaseAgent)
        agent_loader.list_agents.return_value = ["test-app"]
        with tempfile.TemporaryDirectory() as temp_dir:
            server = EnhancedAdkWebServer(
                agent_loader=agent_loader,
                agents_dir=temp_dir,
                session_service=InMemorySessionService(),
                artifact_service=InMemoryArtifactService(),
                memory_service=InMemoryMemoryService(),
                # no credential service provided
                eval_sets_manager=Mock(),
                eval_set_results_manager=Mock(),
            )
            with patch('google_adk_extras.enhanced_adk_web_server.envs.load_dotenv_for_agent'):
                app = server.get_fast_api_app()
                assert app is not None
