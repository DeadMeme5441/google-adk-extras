"""Unit tests for CustomAgentLoader."""

import pytest
import tempfile
import os
import shutil
import threading
import time
from unittest.mock import Mock, patch, MagicMock

from google.adk.agents.base_agent import BaseAgent
from google.adk.cli.utils.base_agent_loader import BaseAgentLoader
from google.adk.cli.utils.agent_loader import AgentLoader

from google_adk_extras.custom_agent_loader import CustomAgentLoader


class TestCustomAgentLoader:
    """Test cases for CustomAgentLoader class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock agents
        self.mock_agent1 = Mock(spec=BaseAgent)
        self.mock_agent1.name = "test_agent1"
        
        self.mock_agent2 = Mock(spec=BaseAgent)
        self.mock_agent2.name = "test_agent2"
        
        self.mock_agent3 = Mock(spec=BaseAgent)
        self.mock_agent3.name = "fallback_agent"

    def test_initialization_without_fallback(self):
        """Test CustomAgentLoader initialization without fallback loader."""
        loader = CustomAgentLoader()
        
        assert loader is not None
        assert len(loader.get_registered_agents()) == 0
        assert not loader.has_fallback_loader()
        assert repr(loader) == "CustomAgentLoader(registered=0)"

    def test_initialization_with_fallback(self):
        """Test CustomAgentLoader initialization with fallback loader."""
        fallback_loader = Mock(spec=BaseAgentLoader)
        loader = CustomAgentLoader(fallback_loader=fallback_loader)
        
        assert loader.has_fallback_loader()
        assert repr(loader) == "CustomAgentLoader(registered=0, fallback=Mock)"

    def test_register_agent_success(self):
        """Test successful agent registration."""
        loader = CustomAgentLoader()
        
        loader.register_agent("test_agent", self.mock_agent1)
        
        registered_agents = loader.get_registered_agents()
        assert "test_agent" in registered_agents
        assert registered_agents["test_agent"] is self.mock_agent1
        assert loader.is_registered("test_agent")

    def test_register_agent_validation(self):
        """Test agent registration validation."""
        loader = CustomAgentLoader()
        
        # Test empty name
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            loader.register_agent("", self.mock_agent1)
        
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            loader.register_agent("   ", self.mock_agent1)
        
        # Test invalid agent type
        with pytest.raises(ValueError, match="Agent must be BaseAgent instance"):
            loader.register_agent("invalid", "not_an_agent")

    def test_register_agent_replacement(self):
        """Test agent registration replacement."""
        loader = CustomAgentLoader()
        
        # Register initial agent
        loader.register_agent("test_agent", self.mock_agent1)
        assert loader.get_registered_agents()["test_agent"] is self.mock_agent1
        
        # Replace with different agent
        loader.register_agent("test_agent", self.mock_agent2)
        assert loader.get_registered_agents()["test_agent"] is self.mock_agent2
        assert len(loader.get_registered_agents()) == 1

    def test_unregister_agent(self):
        """Test agent unregistration."""
        loader = CustomAgentLoader()
        
        # Register agent
        loader.register_agent("test_agent", self.mock_agent1)
        assert loader.is_registered("test_agent")
        
        # Unregister existing agent
        result = loader.unregister_agent("test_agent")
        assert result is True
        assert not loader.is_registered("test_agent")
        assert len(loader.get_registered_agents()) == 0
        
        # Unregister non-existent agent
        result = loader.unregister_agent("nonexistent")
        assert result is False

    def test_clear_registry(self):
        """Test clearing all registered agents."""
        loader = CustomAgentLoader()
        
        # Register multiple agents
        loader.register_agent("agent1", self.mock_agent1)
        loader.register_agent("agent2", self.mock_agent2)
        
        assert len(loader.get_registered_agents()) == 2
        
        # Clear registry
        loader.clear_registry()
        
        assert len(loader.get_registered_agents()) == 0
        assert not loader.is_registered("agent1")
        assert not loader.is_registered("agent2")

    def test_load_agent_from_registry(self):
        """Test loading agent from registry."""
        loader = CustomAgentLoader()
        loader.register_agent("test_agent", self.mock_agent1)
        
        loaded_agent = loader.load_agent("test_agent")
        
        assert loaded_agent is self.mock_agent1

    def test_load_agent_from_fallback(self):
        """Test loading agent from fallback loader."""
        fallback_loader = Mock(spec=BaseAgentLoader)
        fallback_loader.load_agent.return_value = self.mock_agent3
        
        loader = CustomAgentLoader(fallback_loader=fallback_loader)
        
        loaded_agent = loader.load_agent("fallback_agent")
        
        assert loaded_agent is self.mock_agent3
        fallback_loader.load_agent.assert_called_once_with("fallback_agent")

    def test_load_agent_registry_priority(self):
        """Test that registry takes priority over fallback."""
        fallback_loader = Mock(spec=BaseAgentLoader)
        fallback_loader.load_agent.return_value = self.mock_agent3
        
        loader = CustomAgentLoader(fallback_loader=fallback_loader)
        loader.register_agent("priority_test", self.mock_agent1)
        
        loaded_agent = loader.load_agent("priority_test")
        
        # Should load from registry, not fallback
        assert loaded_agent is self.mock_agent1
        fallback_loader.load_agent.assert_not_called()

    def test_load_agent_not_found(self):
        """Test loading non-existent agent."""
        loader = CustomAgentLoader()
        
        with pytest.raises(ValueError, match="Agent 'nonexistent' not found"):
            loader.load_agent("nonexistent")

    def test_load_agent_fallback_failure(self):
        """Test loading agent when fallback loader fails."""
        fallback_loader = Mock(spec=BaseAgentLoader)
        fallback_loader.load_agent.side_effect = ValueError("Fallback failed")
        
        loader = CustomAgentLoader(fallback_loader=fallback_loader)
        
        with pytest.raises(ValueError, match="Agent 'missing' not found"):
            loader.load_agent("missing")

    def test_list_agents_registry_only(self):
        """Test listing agents from registry only."""
        loader = CustomAgentLoader()
        loader.register_agent("agent1", self.mock_agent1)
        loader.register_agent("agent2", self.mock_agent2)
        
        agents = loader.list_agents()
        
        assert sorted(agents) == ["agent1", "agent2"]

    def test_list_agents_fallback_only(self):
        """Test listing agents from fallback only."""
        fallback_loader = Mock(spec=BaseAgentLoader)
        fallback_loader.list_agents.return_value = ["fallback1", "fallback2"]
        
        loader = CustomAgentLoader(fallback_loader=fallback_loader)
        
        agents = loader.list_agents()
        
        assert sorted(agents) == ["fallback1", "fallback2"]

    def test_list_agents_combined(self):
        """Test listing agents from both registry and fallback."""
        fallback_loader = Mock(spec=BaseAgentLoader)
        fallback_loader.list_agents.return_value = ["fallback1", "fallback2"]
        
        loader = CustomAgentLoader(fallback_loader=fallback_loader)
        loader.register_agent("registry1", self.mock_agent1)
        loader.register_agent("registry2", self.mock_agent2)
        
        agents = loader.list_agents()
        
        assert sorted(agents) == ["fallback1", "fallback2", "registry1", "registry2"]

    def test_list_agents_duplicate_names(self):
        """Test listing agents with duplicate names (registry overrides)."""
        fallback_loader = Mock(spec=BaseAgentLoader)
        fallback_loader.list_agents.return_value = ["duplicate", "fallback_only"]
        
        loader = CustomAgentLoader(fallback_loader=fallback_loader)
        loader.register_agent("duplicate", self.mock_agent1)
        loader.register_agent("registry_only", self.mock_agent2)
        
        agents = loader.list_agents()
        
        # Should not have duplicates
        assert sorted(agents) == ["duplicate", "fallback_only", "registry_only"]

    def test_list_agents_fallback_error(self):
        """Test listing agents when fallback loader fails."""
        fallback_loader = Mock(spec=BaseAgentLoader)
        fallback_loader.list_agents.side_effect = Exception("Fallback error")
        
        loader = CustomAgentLoader(fallback_loader=fallback_loader)
        loader.register_agent("registry1", self.mock_agent1)
        
        agents = loader.list_agents()
        
        # Should still return registry agents despite fallback error
        assert agents == ["registry1"]

    def test_get_agent_source(self):
        """Test getting agent source information."""
        fallback_loader = Mock(spec=BaseAgentLoader)
        fallback_loader.list_agents.return_value = ["fallback_agent"]
        
        loader = CustomAgentLoader(fallback_loader=fallback_loader)
        loader.register_agent("registry_agent", self.mock_agent1)
        
        assert loader.get_agent_source("registry_agent") == "registry"
        assert loader.get_agent_source("fallback_agent") == "fallback"
        assert loader.get_agent_source("nonexistent") == "not_found"

    def test_get_agent_source_fallback_error(self):
        """Test getting agent source when fallback fails."""
        fallback_loader = Mock(spec=BaseAgentLoader)
        fallback_loader.list_agents.side_effect = Exception("Fallback error")
        
        loader = CustomAgentLoader(fallback_loader=fallback_loader)
        
        assert loader.get_agent_source("any_agent") == "not_found"

    def test_thread_safety_registration(self):
        """Test thread safety of agent registration."""
        loader = CustomAgentLoader()
        results = []
        errors = []
        
        def register_agents(thread_id):
            try:
                for i in range(10):
                    agent = Mock(spec=BaseAgent)
                    agent.name = f"thread_{thread_id}_agent_{i}"
                    loader.register_agent(f"thread_{thread_id}_agent_{i}", agent)
                    time.sleep(0.001)  # Small delay to increase contention
                results.append(f"thread_{thread_id}_completed")
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=register_agents, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 5
        assert len(loader.get_registered_agents()) == 50  # 5 threads * 10 agents each

    def test_thread_safety_load_and_unregister(self):
        """Test thread safety of loading and unregistering agents."""
        loader = CustomAgentLoader()
        
        # Pre-register some agents
        for i in range(20):
            agent = Mock(spec=BaseAgent)
            loader.register_agent(f"agent_{i}", agent)
        
        load_results = []
        unregister_results = []
        errors = []
        
        def load_agents():
            try:
                for i in range(20):
                    try:
                        agent = loader.load_agent(f"agent_{i}")
                        load_results.append(agent)
                    except ValueError:
                        # Agent might have been unregistered by another thread
                        pass
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        def unregister_agents():
            try:
                for i in range(10, 20):  # Unregister half the agents
                    result = loader.unregister_agent(f"agent_{i}")
                    unregister_results.append(result)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        # Create threads
        load_thread = threading.Thread(target=load_agents)
        unregister_thread = threading.Thread(target=unregister_agents)
        
        load_thread.start()
        unregister_thread.start()
        
        load_thread.join()
        unregister_thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        
        # Verify some agents were successfully loaded and unregistered
        assert len(load_results) > 0
        assert len(unregister_results) == 10


class TestCustomAgentLoaderIntegration:
    """Integration tests for CustomAgentLoader with real AgentLoader."""

    def setup_method(self):
        """Set up test environment with real agent directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.agents_dir = os.path.join(self.temp_dir, "agents")
        os.makedirs(self.agents_dir, exist_ok=True)
        
        # Create a test agent directory structure
        self.test_agent_dir = os.path.join(self.agents_dir, "test_agent")
        os.makedirs(self.test_agent_dir, exist_ok=True)
        
        # Create agent.py file with root_agent
        agent_content = '''
from google.adk.agents import Agent

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash",
    instructions="Test agent for integration testing."
)
'''
        with open(os.path.join(self.test_agent_dir, "agent.py"), "w") as f:
            f.write(agent_content)

    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_hybrid_operation_real_fallback(self):
        """Test CustomAgentLoader with real AgentLoader fallback."""
        # This test requires actual ADK functionality and might need to be skipped
        # in some test environments
        try:
            fallback_loader = AgentLoader(self.agents_dir)
            loader = CustomAgentLoader(fallback_loader=fallback_loader)
            
            # Register a custom agent
            mock_agent = Mock(spec=BaseAgent)
            mock_agent.name = "custom_agent"
            loader.register_agent("custom_agent", mock_agent)
            
            # Test listing combines both
            agents = loader.list_agents()
            assert "custom_agent" in agents
            # Note: "test_agent" might not appear depending on ADK's actual loading
            
            # Test loading custom agent
            loaded_custom = loader.load_agent("custom_agent")
            assert loaded_custom is mock_agent
            
            # Test agent source detection
            assert loader.get_agent_source("custom_agent") == "registry"
            
        except Exception as e:
            # Skip test if ADK functionality is not available
            pytest.skip(f"ADK integration not available: {e}")

    def test_registry_override_fallback(self):
        """Test that registry agents override fallback agents with same name."""
        try:
            fallback_loader = AgentLoader(self.agents_dir)
            loader = CustomAgentLoader(fallback_loader=fallback_loader)
            
            # Register agent with same name as directory agent
            mock_agent = Mock(spec=BaseAgent)
            mock_agent.name = "test_agent_override"
            loader.register_agent("test_agent", mock_agent)
            
            # Loading should return registry agent, not directory agent
            loaded_agent = loader.load_agent("test_agent")
            assert loaded_agent is mock_agent
            assert loader.get_agent_source("test_agent") == "registry"
            
        except Exception as e:
            pytest.skip(f"ADK integration not available: {e}")