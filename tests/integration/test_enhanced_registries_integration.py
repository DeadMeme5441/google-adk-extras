"""Integration tests for enhanced registry infrastructure.

This module tests the registry system integration with the enhanced runner,
dynamic loading capabilities, and hot-swapping functionality in realistic scenarios.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from typing import Any, Dict, List

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService

from google_adk_extras.runners.enhanced_runner import EnhancedRunner
from google_adk_extras.runners.errors import YamlSystemContext
from google_adk_extras.runners.config import EnhancedRunConfig
from google_adk_extras.runners.registry import (
    EnhancedAgentRegistry,
    EnhancedToolRegistry,
    AgentRegistryConfig,
    ToolRegistryConfig,
    RegistryEvent,
    RegistryEventType,
)


class IntegrationTestAgent(BaseAgent):
    """Test agent for integration testing."""
    
    def __init__(self, name: str, behavior: str = "normal", **kwargs):
        super().__init__(name=name, **kwargs)
        self._behavior = behavior
        self._execution_count = 0
    
    @property
    def behavior(self) -> str:
        return self._behavior
    
    @property
    def execution_count(self) -> int:
        return self._execution_count
    
    async def _run_async_impl(self, ctx: InvocationContext) -> Any:
        self._execution_count += 1
        if self._behavior == "fail":
            raise RuntimeError(f"Agent {self.name} failed as requested")
        return f"Agent {self.name} executed (count: {self._execution_count})"
    
    def _run_live_impl(self, ctx: InvocationContext) -> Any:
        return f"Agent {self.name} live execution"


class TestEnhancedRegistriesIntegration:
    """Test registry integration with enhanced runner."""
    
    @pytest.fixture
    def services(self):
        """Create ADK services for testing."""
        return {
            'session_service': InMemorySessionService(),
            'artifact_service': InMemoryArtifactService(),
            'memory_service': InMemoryMemoryService()
        }
    
    @pytest.fixture
    def enhanced_config(self):
        """Create enhanced configuration with registries enabled."""
        return EnhancedRunConfig.from_yaml_dict({
            'enable_tool_registry': True,
            'enable_agent_registry': True,
            'debug': {'enabled': True}
        })
    
    @pytest.fixture
    def yaml_context(self):
        """Create YAML context for testing."""
        return YamlSystemContext(system_name="integration_test")
    
    def test_enhanced_runner_with_registries_creation(self, services, enhanced_config, yaml_context):
        """Test creating enhanced runner with registries."""
        root_agent = IntegrationTestAgent("root_agent")
        
        # Create runner with registry support
        runner = EnhancedRunner(
            app_name="test_app",
            agent=root_agent,
            session_service=services['session_service'],
            artifact_service=services['artifact_service'],
            memory_service=services['memory_service'],
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Verify registries are created
        assert runner.agent_registry is not None
        assert runner.tool_registry is not None
        assert runner.agent_registry.name == "test_app_agent_registry"
        assert runner.tool_registry.name == "test_app_tool_registry"
    
    def test_enhanced_runner_with_custom_registries(self, services, enhanced_config, yaml_context):
        """Test enhanced runner with custom registry configurations."""
        root_agent = IntegrationTestAgent("root_agent")
        
        # Create custom registry configs
        agent_config = AgentRegistryConfig(
            name="custom_agent_registry",
            max_agents=50,
            enable_hot_swapping=True
        )
        
        tool_config = ToolRegistryConfig(
            name="custom_tool_registry",
            max_tools=100,
            default_timeout=45.0
        )
        
        runner = EnhancedRunner(
            app_name="custom_app",
            agent=root_agent,
            session_service=services['session_service'],
            enhanced_config=enhanced_config,
            agent_registry_config=agent_config,
            tool_registry_config=tool_config,
            yaml_context=yaml_context
        )
        
        # Verify custom configurations
        assert runner.agent_registry.name == "custom_agent_registry"
        assert runner.tool_registry.name == "custom_tool_registry"
        assert runner.agent_registry.config.max_agents == 50
        assert runner.tool_registry.config.default_timeout == 45.0
    
    @pytest.mark.asyncio
    async def test_registry_lifecycle_with_runner(self, services, enhanced_config, yaml_context):
        """Test registry lifecycle management with runner."""
        root_agent = IntegrationTestAgent("root_agent")
        
        runner = EnhancedRunner(
            app_name="lifecycle_test",
            agent=root_agent,
            session_service=services['session_service'],
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Test registry startup
        await runner.startup_registries()
        
        assert runner.agent_registry._is_started is True
        assert runner.tool_registry._is_started is True
        
        # Test registry shutdown
        await runner.shutdown_registries()
        
        assert runner.agent_registry._is_shutdown is True
        assert runner.tool_registry._is_shutdown is True
    
    def test_agent_hot_swapping_integration(self, services, enhanced_config, yaml_context):
        """Test agent hot-swapping in integrated environment."""
        root_agent = IntegrationTestAgent("root_agent")
        
        runner = EnhancedRunner(
            app_name="hotswap_test",
            agent=root_agent,
            session_service=services['session_service'],
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Register initial agent
        original_agent = IntegrationTestAgent("swappable", "normal")
        runner.agent_registry.register_agent("swappable", original_agent)
        
        # Verify original agent
        loaded_agent = runner.agent_registry.load_agent("swappable")
        assert loaded_agent is original_agent
        assert loaded_agent.behavior == "normal"
        
        # Hot-swap with new agent
        new_agent = IntegrationTestAgent("swappable", "enhanced")
        runner.agent_registry.register_agent("swappable", new_agent)
        
        # Verify new agent is loaded
        loaded_agent = runner.agent_registry.load_agent("swappable")
        assert loaded_agent is new_agent
        assert loaded_agent.behavior == "enhanced"
        
        # Check metadata reflects hot-swap
        metadata = runner.agent_registry.get_agent_metadata("swappable")
        assert metadata["hot_swapped"] is True
    
    def test_agent_registry_event_system_integration(self, services, enhanced_config, yaml_context):
        """Test registry event system in integrated environment."""
        root_agent = IntegrationTestAgent("root_agent")
        
        runner = EnhancedRunner(
            app_name="events_test", 
            agent=root_agent,
            session_service=services['session_service'],
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Track events
        received_events = []
        
        def event_handler(event: RegistryEvent):
            received_events.append(event)
        
        runner.agent_registry.add_event_listener(event_handler)
        
        # Register agent
        test_agent = IntegrationTestAgent("event_test")
        runner.agent_registry.register_agent("event_test", test_agent)
        
        # Verify registration events (registration + health change)
        assert len(received_events) >= 1
        # Find the registration event
        reg_events = [e for e in received_events if e.event_type == RegistryEventType.REGISTERED]
        assert len(reg_events) == 1
        assert reg_events[0].item_name == "event_test"
        
        # Hot-swap agent
        new_agent = IntegrationTestAgent("event_test", "updated")
        runner.agent_registry.register_agent("event_test", new_agent)
        
        # Verify update events
        update_events = [e for e in received_events if e.event_type == RegistryEventType.UPDATED]
        assert len(update_events) == 1
        
        # Unregister agent
        runner.agent_registry.unregister_agent("event_test")
        
        # Verify unregistration events
        unreg_events = [e for e in received_events if e.event_type == RegistryEventType.UNREGISTERED]
        assert len(unreg_events) == 1
    
    def test_multi_agent_registration_and_discovery(self, services, enhanced_config, yaml_context):
        """Test registering and discovering multiple agents."""
        root_agent = IntegrationTestAgent("root_agent")
        
        runner = EnhancedRunner(
            app_name="multi_agent_test",
            agent=root_agent,
            session_service=services['session_service'],
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Register multiple agents
        agents = [
            ("agent_1", IntegrationTestAgent("agent_1", "normal")),
            ("agent_2", IntegrationTestAgent("agent_2", "enhanced")),
            ("agent_3", IntegrationTestAgent("agent_3", "debug"))
        ]
        
        for name, agent in agents:
            runner.agent_registry.register_agent(name, agent)
        
        # Test discovery by type
        integration_agents = runner.agent_registry.find_agents_by_type("IntegrationTestAgent")
        assert len(integration_agents) == 3
        assert sorted(integration_agents) == ["agent_1", "agent_2", "agent_3"]
        
        # Test discovery by metadata
        normal_agents = runner.agent_registry.find_agents_by_metadata(agent_type="IntegrationTestAgent")
        assert len(normal_agents) == 3
    
    @pytest.mark.asyncio
    async def test_registry_health_monitoring_integration(self, services, enhanced_config, yaml_context):
        """Test registry health monitoring in integrated environment."""
        root_agent = IntegrationTestAgent("root_agent")
        
        runner = EnhancedRunner(
            app_name="health_test",
            agent=root_agent,
            session_service=services['session_service'],
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Register agents with different behaviors
        good_agent = IntegrationTestAgent("good_agent", "normal")
        bad_agent = IntegrationTestAgent("bad_agent", "fail")
        
        runner.agent_registry.register_agent("good_agent", good_agent)
        runner.agent_registry.register_agent("bad_agent", bad_agent)
        
        # Start health monitoring
        await runner.startup_registries()
        
        # Get health information
        good_health = runner.agent_registry.get_health_info("good_agent")
        bad_health = runner.agent_registry.get_health_info("bad_agent")
        
        assert good_health is not None
        assert bad_health is not None
        
        # Get all health info
        all_health = runner.agent_registry.get_all_health_info()
        assert len(all_health) == 2
        assert "good_agent" in all_health
        assert "bad_agent" in all_health
        
        await runner.shutdown_registries()
    
    def test_registry_stats_integration(self, services, enhanced_config, yaml_context):
        """Test registry statistics in integrated environment."""
        root_agent = IntegrationTestAgent("root_agent")
        
        runner = EnhancedRunner(
            app_name="stats_test",
            agent=root_agent,
            session_service=services['session_service'],
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Register multiple agents
        for i in range(3):
            agent = IntegrationTestAgent(f"agent_{i}")
            runner.agent_registry.register_agent(f"agent_{i}", agent)
        
        # Get registry stats
        agent_stats = runner.agent_registry.get_registry_stats()
        tool_stats = runner.tool_registry.get_registry_stats()
        
        # Verify agent stats
        assert agent_stats["name"] == "stats_test_agent_registry"
        assert agent_stats["total_agents"] == 3
        assert agent_stats["hot_swapping_enabled"] is True
        assert "agent_type_distribution" in agent_stats
        assert agent_stats["agent_type_distribution"]["IntegrationTestAgent"] == 3
        
        # Verify tool stats
        assert tool_stats["name"] == "stats_test_tool_registry"
        assert "dynamic_loading_enabled" in tool_stats
    
    def test_registry_configuration_inheritance(self, services, yaml_context):
        """Test that registry configurations are properly inherited."""
        root_agent = IntegrationTestAgent("root_agent")
        
        # Test with registries disabled
        config_disabled = EnhancedRunConfig.from_yaml_dict({
            'enable_tool_registry': False,
            'enable_agent_registry': False
        })
        
        runner_disabled = EnhancedRunner(
            app_name="disabled_test",
            agent=root_agent,
            session_service=services['session_service'],
            enhanced_config=config_disabled,
            yaml_context=yaml_context
        )
        
        assert runner_disabled.agent_registry is None
        assert runner_disabled.tool_registry is None
        
        # Test with registries enabled (default)
        config_enabled = EnhancedRunConfig.from_yaml_dict({
            'enable_tool_registry': True,
            'enable_agent_registry': True
        })
        
        runner_enabled = EnhancedRunner(
            app_name="enabled_test",
            agent=root_agent,
            session_service=services['session_service'],
            enhanced_config=config_enabled,
            yaml_context=yaml_context
        )
        
        assert runner_enabled.agent_registry is not None
        assert runner_enabled.tool_registry is not None
    
    def test_registry_debug_info_integration(self, services, enhanced_config, yaml_context):
        """Test registry debug information in integrated environment."""
        root_agent = IntegrationTestAgent("root_agent")
        
        runner = EnhancedRunner(
            app_name="debug_test",
            agent=root_agent,
            session_service=services['session_service'],
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Get debug info
        debug_info = runner.get_debug_info()
        
        # Verify registry information is included
        assert "registries" in debug_info
        assert debug_info["registries"]["tool_registry"] is True
        assert debug_info["registries"]["agent_registry"] is True
        
        # Verify enhanced config info
        assert "enhanced_config" in debug_info
        assert debug_info["enhanced_config"]["tool_registry_enabled"] is True
        assert debug_info["enhanced_config"]["agent_registry_enabled"] is True


@pytest.mark.asyncio
class TestDynamicLoadingIntegration:
    """Test dynamic loading capabilities."""
    
    @pytest.fixture
    def services(self):
        """Create ADK services for testing."""
        return {
            'session_service': InMemorySessionService(),
            'artifact_service': InMemoryArtifactService(),
            'memory_service': InMemoryMemoryService()
        }
    
    @pytest.fixture
    def enhanced_config(self):
        """Create enhanced configuration with dynamic loading enabled."""
        return EnhancedRunConfig.from_yaml_dict({
            'enable_tool_registry': True,
            'enable_agent_registry': True,
            'debug': {'enabled': True}
        })
    
    async def test_dynamic_agent_loading_lifecycle(self, services, enhanced_config):
        """Test complete dynamic agent loading lifecycle."""
        root_agent = IntegrationTestAgent("root_agent")
        yaml_context = YamlSystemContext(system_name="dynamic_test")
        
        runner = EnhancedRunner(
            app_name="dynamic_test",
            agent=root_agent,
            session_service=services['session_service'],
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        # Start registries
        await runner.startup_registries()
        
        # Dynamically load agents
        dynamic_agents = []
        for i in range(5):
            agent_name = f"dynamic_agent_{i}"
            agent = IntegrationTestAgent(agent_name, behavior=f"dynamic_{i}")
            
            # Register agent
            runner.agent_registry.register_agent(agent_name, agent)
            dynamic_agents.append((agent_name, agent))
            
            # Verify agent is registered
            assert runner.agent_registry.is_registered(agent_name)
            loaded_agent = runner.agent_registry.load_agent(agent_name)
            assert loaded_agent is agent
        
        # Test bulk operations
        all_agents = runner.agent_registry.list_agents()
        assert len(all_agents) == 5
        
        # Test hot-swapping multiple agents
        for agent_name, _ in dynamic_agents[:3]:  # Hot-swap first 3
            new_agent = IntegrationTestAgent(agent_name, behavior="hot_swapped")
            runner.agent_registry.register_agent(agent_name, new_agent)
            
            # Verify hot-swap
            loaded_agent = runner.agent_registry.load_agent(agent_name)
            assert loaded_agent.behavior == "hot_swapped"
            
            metadata = runner.agent_registry.get_agent_metadata(agent_name)
            assert metadata["hot_swapped"] is True
        
        # Test selective unloading
        for agent_name, _ in dynamic_agents[3:]:  # Unload last 2
            success = runner.agent_registry.unregister_agent(agent_name)
            assert success is True
            assert not runner.agent_registry.is_registered(agent_name)
        
        # Verify final state
        remaining_agents = runner.agent_registry.list_agents()
        assert len(remaining_agents) == 3
        
        await runner.shutdown_registries()
    
    async def test_concurrent_dynamic_operations(self, services, enhanced_config):
        """Test concurrent dynamic loading and hot-swapping."""
        root_agent = IntegrationTestAgent("root_agent")
        yaml_context = YamlSystemContext(system_name="concurrent_test")
        
        runner = EnhancedRunner(
            app_name="concurrent_test",
            agent=root_agent,
            session_service=services['session_service'],
            enhanced_config=enhanced_config,
            yaml_context=yaml_context
        )
        
        await runner.startup_registries()
        
        # Define concurrent operations
        async def register_agent(name: str, delay: float):
            await asyncio.sleep(delay)
            agent = IntegrationTestAgent(name, behavior="concurrent")
            runner.agent_registry.register_agent(name, agent)
            return name
        
        async def hot_swap_agent(name: str, delay: float):
            await asyncio.sleep(delay)
            if runner.agent_registry.is_registered(name):
                new_agent = IntegrationTestAgent(name, behavior="swapped")
                runner.agent_registry.register_agent(name, new_agent)
            return name
        
        # Execute concurrent operations
        registration_tasks = [
            register_agent(f"concurrent_{i}", i * 0.1) 
            for i in range(10)
        ]
        
        # Wait for all registrations
        registered = await asyncio.gather(*registration_tasks)
        assert len(registered) == 10
        
        # Now do concurrent hot-swaps
        swap_tasks = [
            hot_swap_agent(f"concurrent_{i}", i * 0.05) 
            for i in range(5)  # Hot-swap first 5
        ]
        
        swapped = await asyncio.gather(*swap_tasks)
        assert len(swapped) == 5
        
        # Verify final state
        all_agents = runner.agent_registry.list_agents()
        assert len(all_agents) == 10
        
        # Verify hot-swapped agents
        for i in range(5):
            agent_name = f"concurrent_{i}"
            loaded_agent = runner.agent_registry.load_agent(agent_name)
            assert loaded_agent.behavior == "swapped"
        
        await runner.shutdown_registries()
    
    async def test_dynamic_loading_with_validation(self, services, enhanced_config):
        """Test dynamic loading with custom validation."""
        root_agent = IntegrationTestAgent("root_agent")
        yaml_context = YamlSystemContext(system_name="validation_test")
        
        # Create config with validation enabled
        config_with_validation = AgentRegistryConfig(
            name="validation_registry",
            validate_agents_on_registration=True,
            allowed_agent_types=["IntegrationTestAgent"]
        )
        
        runner = EnhancedRunner(
            app_name="validation_test",
            agent=root_agent,
            session_service=services['session_service'],
            enhanced_config=enhanced_config,
            agent_registry_config=config_with_validation,
            yaml_context=yaml_context
        )
        
        # Add custom validator
        def behavior_validator(name: str, agent: BaseAgent) -> bool:
            """Only allow agents with 'approved' behavior."""
            return hasattr(agent, 'behavior') and agent.behavior.startswith('approved')
        
        runner.agent_registry.add_agent_validator(behavior_validator)
        
        # Test valid agent
        valid_agent = IntegrationTestAgent("valid_agent", "approved_behavior")
        runner.agent_registry.register_agent("valid_agent", valid_agent)
        assert runner.agent_registry.is_registered("valid_agent")
        
        # Test invalid agent
        invalid_agent = IntegrationTestAgent("invalid_agent", "rejected_behavior")
        
        with pytest.raises(Exception):  # Should fail validation
            runner.agent_registry.register_agent("invalid_agent", invalid_agent)
        
        assert not runner.agent_registry.is_registered("invalid_agent")
        
        # Test validation with hot-swapping
        approved_replacement = IntegrationTestAgent("valid_agent", "approved_updated")
        runner.agent_registry.register_agent("valid_agent", approved_replacement)  # Should succeed
        
        loaded_agent = runner.agent_registry.load_agent("valid_agent")
        assert loaded_agent.behavior == "approved_updated"


if __name__ == "__main__":
    pytest.main([__file__])