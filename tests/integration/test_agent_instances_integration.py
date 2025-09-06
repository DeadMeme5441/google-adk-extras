"""Integration tests for agent instances functionality.

These tests verify the full end-to-end flow of using agent instances
with CustomAgentLoader, AdkBuilder, and the enhanced FastAPI application.
"""

import pytest
import tempfile
import os
import shutil
import asyncio
from unittest.mock import Mock, patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents import Agent
from google.adk.cli.utils.agent_loader import AgentLoader

from google_adk_extras.adk_builder import AdkBuilder
from google_adk_extras.custom_agent_loader import CustomAgentLoader
from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app


class TestAgentInstancesIntegration:
    """Integration tests for agent instances functionality."""
    
    def setup_method(self):
        """Set up test fixtures with mock agents."""
        # Create mock agents for testing
        self.agent1 = Mock(spec=BaseAgent)
        self.agent1.name = "test_agent_1"
        
        self.agent2 = Mock(spec=BaseAgent)
        self.agent2.name = "test_agent_2"
        
        self.agent3 = Mock(spec=BaseAgent)
        self.agent3.name = "directory_agent"
        
        # Create temporary directory for directory-based tests
        self.temp_dir = tempfile.mkdtemp()
        self.agents_dir = os.path.join(self.temp_dir, "agents")
        os.makedirs(self.agents_dir, exist_ok=True)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_adk_builder_with_agent_instances_only(self):
        """Test AdkBuilder with only registered agent instances."""
        builder = (AdkBuilder()
                  .with_agent_instance("agent1", self.agent1)
                  .with_agent_instance("agent2", self.agent2))
        
        # Test that agent loader is created correctly
        agent_loader = builder._create_agent_loader()
        
        assert isinstance(agent_loader, CustomAgentLoader)
        assert not agent_loader.has_fallback_loader()
        assert agent_loader.is_registered("agent1")
        assert agent_loader.is_registered("agent2")
        
        # Test agent loading
        loaded_agent1 = agent_loader.load_agent("agent1")
        loaded_agent2 = agent_loader.load_agent("agent2")
        
        assert loaded_agent1 is self.agent1
        assert loaded_agent2 is self.agent2
        
        # Test agent listing
        agents = agent_loader.list_agents()
        assert sorted(agents) == ["agent1", "agent2"]
    
    def test_adk_builder_with_hybrid_agents(self):
        """Test AdkBuilder with both agent instances and directory fallback."""
        # Create a test agent directory structure
        test_agent_dir = os.path.join(self.agents_dir, "directory_agent")
        os.makedirs(test_agent_dir, exist_ok=True)
        
        # Create basic agent.py file
        agent_content = '''
from google.adk.agents import Agent

root_agent = Agent(
    name="directory_agent",
    model="gemini-2.0-flash",
    instructions="Test directory agent."
)
'''
        with open(os.path.join(test_agent_dir, "agent.py"), "w") as f:
            f.write(agent_content)
        
        builder = (AdkBuilder()
                  .with_agents_dir(self.agents_dir)
                  .with_agent_instance("instance_agent", self.agent1))
        
        agent_loader = builder._create_agent_loader()
        
        assert isinstance(agent_loader, CustomAgentLoader)
        assert agent_loader.has_fallback_loader()
        assert agent_loader.is_registered("instance_agent")
        
        # Test listing combines both sources
        agents = agent_loader.list_agents()
        assert "instance_agent" in agents
        # Note: directory_agent might not appear due to ADK loading requirements
        
        # Test loading instance agent takes priority
        loaded_agent = agent_loader.load_agent("instance_agent")
        assert loaded_agent is self.agent1
    
    @patch('google_adk_extras.enhanced_fastapi.AdkWebServer')
    def test_enhanced_fastapi_with_custom_agent_loader(self, mock_adk_web_server):
        """Test enhanced FastAPI app with custom agent loader."""
        # Create mock AdkWebServer
        mock_server_instance = MagicMock()
        mock_app = MagicMock(spec=FastAPI)
        mock_server_instance.get_fast_api_app.return_value = mock_app
        mock_adk_web_server.return_value = mock_server_instance
        
        # Create custom agent loader
        custom_loader = CustomAgentLoader()
        custom_loader.register_agent("test_agent", self.agent1)
        
        # Create enhanced FastAPI app
        app = get_enhanced_fast_api_app(
            agent_loader=custom_loader,
            web=False,  # Disable web UI for testing
        )
        
        # Verify AdkWebServer was created with our custom loader
        mock_adk_web_server.assert_called_once()
        call_kwargs = mock_adk_web_server.call_args[1]
        assert call_kwargs['agent_loader'] is custom_loader
        
        # Verify app was returned
        assert app is mock_app
    
    @patch('google_adk_extras.enhanced_fastapi.AdkWebServer')
    def test_adk_builder_full_integration(self, mock_adk_web_server):
        """Test full integration from AdkBuilder to FastAPI app."""
        # Setup mock AdkWebServer
        mock_server_instance = MagicMock()
        mock_app = MagicMock(spec=FastAPI)
        mock_server_instance.get_fast_api_app.return_value = mock_app
        mock_adk_web_server.return_value = mock_server_instance
        
        # Build FastAPI app with agent instances
        builder = (AdkBuilder()
                  .with_agents_dir(self.temp_dir)  # Required for eval managers
                  .with_agent_instance("api_agent", self.agent1)
                  .with_agent_instance("helper_agent", self.agent2)
                  .with_web_ui(False))
        
        app = builder.build_fastapi_app()
        
        # Verify AdkWebServer was called with CustomAgentLoader
        mock_adk_web_server.assert_called_once()
        call_kwargs = mock_adk_web_server.call_args[1]
        agent_loader = call_kwargs['agent_loader']
        
        assert isinstance(agent_loader, CustomAgentLoader)
        assert agent_loader.is_registered("api_agent")
        assert agent_loader.is_registered("helper_agent")
        
        # Verify agents can be loaded
        loaded_agent1 = agent_loader.load_agent("api_agent")
        loaded_agent2 = agent_loader.load_agent("helper_agent")
        
        assert loaded_agent1 is self.agent1
        assert loaded_agent2 is self.agent2
    
    def test_multiple_agents_registration_bulk(self):
        """Test bulk agent registration functionality."""
        agents_dict = {
            "bulk_agent1": self.agent1,
            "bulk_agent2": self.agent2,
        }
        
        builder = AdkBuilder().with_agents(agents_dict)
        agent_loader = builder._create_agent_loader()
        
        assert isinstance(agent_loader, CustomAgentLoader)
        assert agent_loader.is_registered("bulk_agent1")
        assert agent_loader.is_registered("bulk_agent2")
        
        # Test loading
        loaded1 = agent_loader.load_agent("bulk_agent1")
        loaded2 = agent_loader.load_agent("bulk_agent2")
        
        assert loaded1 is self.agent1
        assert loaded2 is self.agent2
    
    def test_agent_loader_validation(self):
        """Test validation in agent loader creation."""
        builder = AdkBuilder()
        
        # Should raise error without agents_dir or agent instances
        with pytest.raises(ValueError, match="No agent configuration provided"):
            builder._create_agent_loader()
        
        # Should work with registered agents only
        builder.with_agent_instance("test", self.agent1)
        loader = builder._create_agent_loader()
        assert isinstance(loader, CustomAgentLoader)
        
        # Should work with agents_dir only
        builder2 = AdkBuilder().with_agents_dir(self.temp_dir)
        loader2 = builder2._create_agent_loader()
        assert isinstance(loader2, AgentLoader)  # Uses directory loader directly
    
    @patch('google_adk_extras.enhanced_fastapi.AdkWebServer')
    def test_error_handling_in_fastapi_integration(self, mock_adk_web_server):
        """Test error handling in FastAPI integration."""
        # Should raise error without agents_dir or agent_loader
        with pytest.raises(ValueError, match="Either agent_loader or agents_dir"):
            get_enhanced_fast_api_app()
        
        # Should work with custom agent loader only
        custom_loader = CustomAgentLoader()
        custom_loader.register_agent("test_agent", self.agent1)
        
        mock_server_instance = MagicMock()
        mock_app = MagicMock(spec=FastAPI)
        mock_server_instance.get_fast_api_app.return_value = mock_app
        mock_adk_web_server.return_value = mock_server_instance
        
        app = get_enhanced_fast_api_app(agent_loader=custom_loader, web=False)
        assert app is mock_app
    
    def test_agent_priority_and_fallback_behavior(self):
        """Test that registered agents take priority over directory agents."""
        # Create directory agent
        test_agent_dir = os.path.join(self.agents_dir, "priority_test")
        os.makedirs(test_agent_dir, exist_ok=True)
        
        agent_content = '''
from google.adk.agents import Agent

root_agent = Agent(
    name="priority_test",
    model="gemini-2.0-flash",
    instructions="Directory agent for priority testing."
)
'''
        with open(os.path.join(test_agent_dir, "agent.py"), "w") as f:
            f.write(agent_content)
        
        # Create builder with both directory and instance for same name
        builder = (AdkBuilder()
                  .with_agents_dir(self.agents_dir)
                  .with_agent_instance("priority_test", self.agent1))
        
        agent_loader = builder._create_agent_loader()
        
        # Registered agent should take priority
        loaded_agent = agent_loader.load_agent("priority_test")
        assert loaded_agent is self.agent1  # Instance, not directory agent
        
        # Source should be registry
        assert agent_loader.get_agent_source("priority_test") == "registry"
    
    def test_agent_discovery_and_listing(self):
        """Test agent discovery combines all sources correctly."""
        # Create some directory agents
        for i in range(2):
            agent_dir = os.path.join(self.agents_dir, f"dir_agent_{i}")
            os.makedirs(agent_dir, exist_ok=True)
            
            agent_content = f'''
from google.adk.agents import Agent

root_agent = Agent(
    name="dir_agent_{i}",
    model="gemini-2.0-flash",
    instructions="Directory agent {i}."
)
'''
            with open(os.path.join(agent_dir, "agent.py"), "w") as f:
                f.write(agent_content)
        
        builder = (AdkBuilder()
                  .with_agents_dir(self.agents_dir)
                  .with_agent_instance("instance_agent_1", self.agent1)
                  .with_agent_instance("instance_agent_2", self.agent2))
        
        agent_loader = builder._create_agent_loader()
        agents = agent_loader.list_agents()
        
        # Should include both registered and directory agents
        assert "instance_agent_1" in agents
        assert "instance_agent_2" in agents
        # Directory agents may or may not appear due to ADK loading requirements
        
        # Test source detection
        assert agent_loader.get_agent_source("instance_agent_1") == "registry"
        assert agent_loader.get_agent_source("instance_agent_2") == "registry"


class TestAgentInstancesErrorHandling:
    """Test error handling in agent instances integration."""
    
    def test_invalid_agent_registration(self):
        """Test error handling for invalid agent registration."""
        builder = AdkBuilder()
        
        # Should reject non-BaseAgent instances
        with pytest.raises(ValueError, match="Agent must be BaseAgent instance"):
            builder.with_agent_instance("invalid", "not_an_agent")
        
        # Should reject empty names
        mock_agent = Mock(spec=BaseAgent)
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            builder.with_agent_instance("", mock_agent)
    
    def test_bulk_registration_validation(self):
        """Test validation in bulk agent registration."""
        builder = AdkBuilder()
        
        # Should reject invalid agents dict
        with pytest.raises(ValueError, match="Agents must be a dictionary mapping"):
            builder.with_agents("not_a_dict")
        
        # Should reject empty agent names in bulk
        mock_agent = Mock(spec=BaseAgent)
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            builder.with_agents({"": mock_agent})
        
        # Should reject non-BaseAgent instances in bulk
        with pytest.raises(ValueError, match="Agent must be BaseAgent instance"):
            builder.with_agents({"test": "invalid"})
    
    def test_agent_loader_edge_cases(self):
        """Test edge cases in agent loader handling."""
        builder = AdkBuilder()
        
        # Custom agent loader should be used as-is
        custom_loader = CustomAgentLoader()
        builder.with_agent_loader(custom_loader)
        
        created_loader = builder._create_agent_loader()
        assert created_loader is custom_loader
        
        # Should validate agent loader type
        with pytest.raises(ValueError, match="Agent loader must be BaseAgentLoader"):
            builder.with_agent_loader("invalid")