"""Unit tests for CustomAgentLoader."""

import pytest
import threading
import time
from unittest.mock import Mock

from google.adk.agents.base_agent import BaseAgent

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

    def test_initialization_basic(self):
        """Test CustomAgentLoader basic initialization."""
        loader = CustomAgentLoader()
        
        assert loader is not None
        assert len(loader.get_registered_agents()) == 0
        assert repr(loader) == "CustomAgentLoader(registered=0)"

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

    def test_load_agent_not_found(self):
        """Test loading non-existent agent."""
        loader = CustomAgentLoader()
        
        with pytest.raises(ValueError, match="Agent 'nonexistent' not found"):
            loader.load_agent("nonexistent")

    def test_load_agent_with_available_agents_info(self):
        """Test that error message includes available agents."""
        loader = CustomAgentLoader()
        loader.register_agent("agent1", self.mock_agent1)
        loader.register_agent("agent2", self.mock_agent2)
        
        with pytest.raises(ValueError, match="Available agents: \\['agent1', 'agent2'\\]"):
            loader.load_agent("nonexistent")

    def test_list_agents_registry_only(self):
        """Test listing agents from registry only."""
        loader = CustomAgentLoader()
        loader.register_agent("agent1", self.mock_agent1)
        loader.register_agent("agent2", self.mock_agent2)
        
        agents = loader.list_agents()
        
        assert sorted(agents) == ["agent1", "agent2"]

    def test_list_agents_empty(self):
        """Test listing agents when registry is empty."""
        loader = CustomAgentLoader()
        
        agents = loader.list_agents()
        
        assert agents == []

    def test_get_registered_agents_copy(self):
        """Test that get_registered_agents returns a copy."""
        loader = CustomAgentLoader()
        loader.register_agent("test_agent", self.mock_agent1)
        
        # Get the agents dict and try to modify it
        agents_dict = loader.get_registered_agents()
        agents_dict["new_agent"] = self.mock_agent2
        
        # Original registry should not be affected
        assert len(loader.get_registered_agents()) == 1
        assert "new_agent" not in loader.get_registered_agents()

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