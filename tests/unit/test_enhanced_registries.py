"""Unit tests for enhanced registry infrastructure.

This module tests the core registry functionality including:
- EnhancedRegistryBase abstract functionality
- EnhancedAgentRegistry with hot-swapping
- EnhancedToolRegistry with strategy integration 
- Registry configuration classes
- Event system and health monitoring
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext

from google_adk_extras.runners.errors import YamlSystemContext, YamlSystemError
from google_adk_extras.runners.registry import (
    EnhancedRegistryBase,
    EnhancedAgentRegistry,
    EnhancedToolRegistry,
    RegistryEvent,
    RegistryEventType,
    RegistryHealth,
    RegistryHealthStatus,
    AgentRegistryConfig,
    ToolRegistryConfig,
    RegistryConfig,
)
from google_adk_extras.runners.strategies import ToolExecutionStrategy


class TestRegistryConfig:
    """Test registry configuration classes."""
    
    def test_registry_config_creation(self):
        """Test basic registry config creation."""
        config = RegistryConfig(name="test_registry")
        assert config.name == "test_registry"
        assert config.auto_startup is True
        assert config.caching.enabled is True
        assert config.health_monitoring.enabled is True
        assert config.events.enabled is True
    
    def test_registry_config_validation(self):
        """Test registry config validation."""
        # Test empty name validation
        with pytest.raises(ValueError, match="Registry name cannot be empty"):
            RegistryConfig(name="")
        
        # Test negative timeout validation
        with pytest.raises(ValueError, match="Shutdown timeout must be positive"):
            RegistryConfig(name="test", graceful_shutdown_timeout=-1.0)
    
    def test_agent_registry_config_creation(self):
        """Test agent registry config creation."""
        config = AgentRegistryConfig(
            name="agent_registry",
            enable_hot_swapping=True,
            max_agents=100,
            allowed_agent_types=["MockTestAgent", "MockAgent"]
        )
        
        assert config.name == "agent_registry"
        assert config.enable_hot_swapping is True
        assert config.max_agents == 100
        assert config.allowed_agent_types == ["MockTestAgent", "MockAgent"]
        assert config.validate_agents_on_registration is True
    
    def test_agent_registry_config_validation(self):
        """Test agent registry config validation."""
        # Test max_agents validation
        with pytest.raises(ValueError, match="max_agents must be positive"):
            AgentRegistryConfig(name="test", max_agents=0)
        
        # Test allowed_agent_types validation
        with pytest.raises(Exception, match="Input should be a valid list"):
            AgentRegistryConfig(name="test", allowed_agent_types="invalid")
        
        with pytest.raises(ValueError, match="All agent types must be non-empty strings"):
            AgentRegistryConfig(name="test", allowed_agent_types=["valid", ""])
    
    def test_tool_registry_config_creation(self):
        """Test tool registry config creation."""
        config = ToolRegistryConfig(
            name="tool_registry",
            max_tools=50,
            default_timeout=30.0,
            max_concurrent_executions=5
        )
        
        assert config.name == "tool_registry"
        assert config.max_tools == 50
        assert config.default_timeout == 30.0
        assert config.max_concurrent_executions == 5
        assert config.enable_dynamic_loading is True
    
    def test_tool_registry_config_validation(self):
        """Test tool registry config validation."""
        # Test max_tools validation
        with pytest.raises(ValueError, match="max_tools must be positive"):
            ToolRegistryConfig(name="test", max_tools=-1)
        
        # Test timeout validation  
        with pytest.raises(ValueError, match="Default timeout must be positive"):
            ToolRegistryConfig(name="test", default_timeout=0)
        
        # Test concurrent executions validation
        with pytest.raises(ValueError, match="max_concurrent_executions must be positive"):
            ToolRegistryConfig(name="test", max_concurrent_executions=0)
    
    def test_config_to_dict_conversion(self):
        """Test config to dictionary conversion."""
        config = AgentRegistryConfig(
            name="test_registry",
            max_agents=10
        )
        
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["name"] == "test_registry"
        assert config_dict["max_agents"] == 10
    
    def test_config_from_dict_creation(self):
        """Test config creation from dictionary."""
        config_dict = {
            "name": "test_registry",
            "max_agents": 20,
            "enable_hot_swapping": False
        }
        
        config = AgentRegistryConfig.from_dict(config_dict)
        assert config.name == "test_registry"
        assert config.max_agents == 20
        assert config.enable_hot_swapping is False


class MockTestAgent(BaseAgent):
    """Mock agent for testing."""
    
    def __init__(self, name: str = "test_agent", **kwargs):
        super().__init__(name=name, **kwargs)
        # Use private attributes to avoid Pydantic validation issues
        self._version = "1.0.0"
    
    @property
    def version(self) -> str:
        return self._version
    
    async def _run_async_impl(self, ctx: InvocationContext) -> Any:
        return f"Agent {self.name} executed"
    
    def _run_live_impl(self, ctx: InvocationContext) -> Any:
        return f"Agent {self.name} live"


class TestEnhancedAgentRegistry:
    """Test enhanced agent registry functionality."""
    
    @pytest.fixture
    def yaml_context(self):
        """Create test YAML context."""
        return YamlSystemContext(system_name="test_system")
    
    @pytest.fixture
    def agent_config(self):
        """Create test agent registry config."""
        return AgentRegistryConfig(name="test_agent_registry")
    
    @pytest.fixture
    def registry(self, agent_config, yaml_context):
        """Create test agent registry."""
        return EnhancedAgentRegistry(config=agent_config, yaml_context=yaml_context)
    
    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert registry.name == "test_agent_registry"
        assert len(registry.list_agents()) == 0
        assert registry.config.enable_hot_swapping is True
    
    def test_agent_registration(self, registry):
        """Test basic agent registration."""
        agent = MockTestAgent("test_agent")
        
        registry.register_agent("test_agent", agent)
        
        assert registry.is_registered("test_agent")
        assert "test_agent" in registry.list_agents()
        
        loaded_agent = registry.load_agent("test_agent")
        assert loaded_agent is agent
    
    def test_agent_registration_with_metadata(self, registry):
        """Test agent registration with metadata."""
        agent = MockTestAgent("meta_agent")
        metadata = {"description": "Test agent with metadata", "version": "2.0.0"}
        
        registry.register_agent("meta_agent", agent, metadata)
        
        agent_metadata = registry.get_agent_metadata("meta_agent")
        assert agent_metadata is not None
        assert agent_metadata["description"] == "Test agent with metadata"
        assert agent_metadata["agent_type"] == "MockTestAgent"
        assert agent_metadata["hot_swapped"] is False
    
    def test_hot_swapping(self, registry):
        """Test hot-swapping of agents."""
        agent1 = MockTestAgent("swappable_agent")
        agent2 = MockTestAgent("swappable_agent")  # Same name, different instance
        
        # Register first agent
        registry.register_agent("swap_test", agent1)
        assert registry.load_agent("swap_test") is agent1
        
        # Hot-swap with second agent
        registry.register_agent("swap_test", agent2)
        assert registry.load_agent("swap_test") is agent2
        
        metadata = registry.get_agent_metadata("swap_test")
        assert metadata["hot_swapped"] is True
    
    def test_hot_swapping_disabled(self, yaml_context):
        """Test hot-swapping when disabled."""
        config = AgentRegistryConfig(
            name="no_swap_registry",
            enable_hot_swapping=False
        )
        registry = EnhancedAgentRegistry(config=config, yaml_context=yaml_context)
        
        agent1 = MockTestAgent("original")
        agent2 = MockTestAgent("replacement")
        
        registry.register_agent("test_agent", agent1)
        
        # Should fail when hot-swapping is disabled
        with pytest.raises(YamlSystemError, match="already registered and hot-swapping is disabled"):
            registry.register_agent("test_agent", agent2)
    
    def test_agent_validation_failure(self, registry):
        """Test agent validation failure."""
        # Try to register non-agent object
        with pytest.raises(YamlSystemError, match="Agent must be BaseAgent instance"):
            registry.register_agent("invalid_agent", "not_an_agent")
    
    def test_max_agents_limit(self, yaml_context):
        """Test maximum agents limit enforcement."""
        config = AgentRegistryConfig(name="limited_registry", max_agents=2)
        registry = EnhancedAgentRegistry(config=config, yaml_context=yaml_context)
        
        # Register up to limit
        registry.register_agent("agent1", MockTestAgent("agent1"))
        registry.register_agent("agent2", MockTestAgent("agent2"))
        
        # Should fail when limit exceeded
        with pytest.raises(YamlSystemError, match="Maximum agents limit.*reached"):
            registry.register_agent("agent3", MockTestAgent("agent3"))
    
    def test_allowed_agent_types(self, yaml_context):
        """Test allowed agent types restriction."""
        config = AgentRegistryConfig(
            name="restricted_registry",
            allowed_agent_types=["MockTestAgent"]
        )
        registry = EnhancedAgentRegistry(config=config, yaml_context=yaml_context)
        
        # Should allow MockTestAgent
        registry.register_agent("allowed", MockTestAgent("allowed"))
        
        # Should reject other types
        class OtherAgent(BaseAgent):
            async def _run_async_impl(self, ctx: InvocationContext) -> Any:
                return "other"
        
        with pytest.raises(YamlSystemError, match="Agent type.*not in allowed types"):
            registry.register_agent("disallowed", OtherAgent())
    
    def test_agent_unregistration(self, registry):
        """Test agent unregistration."""
        agent = MockTestAgent("temp_agent")
        registry.register_agent("temp_agent", agent)
        
        assert registry.is_registered("temp_agent")
        
        success = registry.unregister_agent("temp_agent")
        assert success is True
        assert not registry.is_registered("temp_agent")
        
        # Unregistering non-existent agent should return False
        success = registry.unregister_agent("nonexistent")
        assert success is False
    
    def test_agent_not_found_error(self, registry):
        """Test error when loading non-existent agent."""
        with pytest.raises(YamlSystemError, match="Agent.*not found in registry"):
            registry.load_agent("nonexistent_agent")
    
    def test_find_agents_by_type(self, registry):
        """Test finding agents by type."""
        registry.register_agent("test1", MockTestAgent("test1"))
        registry.register_agent("test2", MockTestAgent("test2"))
        
        class OtherAgent(BaseAgent):
            async def _run_async_impl(self, ctx: InvocationContext) -> Any:
                return "other"
        
        # Disable type restriction for this test
        registry.config.allowed_agent_types = None
        registry.register_agent("other", OtherAgent())
        
        test_agents = registry.find_agents_by_type("MockTestAgent")
        assert sorted(test_agents) == ["test1", "test2"]
        
        other_agents = registry.find_agents_by_type("OtherAgent")
        assert other_agents == ["other"]
    
    def test_find_agents_by_metadata(self, registry):
        """Test finding agents by metadata."""
        registry.register_agent("v1_agent", MockTestAgent("v1"), {"version": "1.0"})
        registry.register_agent("v2_agent", MockTestAgent("v2"), {"version": "2.0"})
        registry.register_agent("prod_agent", MockTestAgent("prod"), {"env": "production", "version": "1.0"})
        
        # Find by version
        v1_agents = registry.find_agents_by_metadata(version="1.0")
        assert sorted(v1_agents) == ["prod_agent", "v1_agent"]
        
        # Find by multiple criteria
        prod_agents = registry.find_agents_by_metadata(env="production", version="1.0")
        assert prod_agents == ["prod_agent"]
    
    def test_agent_validation(self, registry):
        """Test agent validation functionality."""
        agent = MockTestAgent("validatable_agent")
        
        # Add custom validator
        def custom_validator(name: str, agent: BaseAgent) -> bool:
            return hasattr(agent, 'name') and agent.name.startswith('valid')
        
        registry.add_agent_validator(custom_validator)
        
        # Should pass validation
        registry.register_agent("validatable_agent", agent)
        
        # Should fail validation
        bad_agent = MockTestAgent("invalid_agent")
        with pytest.raises(YamlSystemError, match="Agent validation failed"):
            registry.register_agent("invalid_agent", bad_agent)
        
        # Test validator removal
        assert registry.remove_agent_validator(custom_validator) is True
        assert registry.remove_agent_validator(custom_validator) is False  # Already removed
    
    def test_validate_all_agents(self, registry):
        """Test validation of all registered agents."""
        registry.register_agent("good_agent", MockTestAgent("good"))
        registry.register_agent("another_agent", MockTestAgent("another"))
        
        # All should be valid initially
        results = registry.validate_all_agents()
        assert results["good_agent"] is True
        assert results["another_agent"] is True
        
        # Add failing validator
        def failing_validator(name: str, agent: BaseAgent) -> bool:
            return name != "good_agent"  # Fail only for good_agent
        
        registry.add_agent_validator(failing_validator)
        
        results = registry.validate_all_agents()
        assert results["good_agent"] is False
        assert results["another_agent"] is True
    
    @pytest.mark.asyncio
    async def test_registry_lifecycle(self, registry):
        """Test registry startup and shutdown."""
        # Test startup
        await registry.startup()
        assert registry._is_started is True
        
        # Test shutdown
        await registry.shutdown()
        assert registry._is_shutdown is True
        assert registry._is_started is False
    
    def test_registry_stats(self, registry):
        """Test registry statistics."""
        # Add some agents
        registry.register_agent("agent1", MockTestAgent("agent1"))
        registry.register_agent("agent2", MockTestAgent("agent2"))
        
        stats = registry.get_registry_stats()
        
        assert stats["name"] == "test_agent_registry"
        assert stats["total_agents"] == 2
        assert stats["hot_swapping_enabled"] is True
        assert stats["validation_enabled"] is True
        assert "agent_type_distribution" in stats
        assert stats["agent_type_distribution"]["MockTestAgent"] == 2


class MockToolExecutionStrategy(ToolExecutionStrategy):
    """Mock tool execution strategy for testing."""
    
    def __init__(self, name: str = "mock_strategy"):
        super().__init__()
        self.name = name
    
    async def execute_tool_async(self, tool, context, tool_context, tool_config=None):
        """Mock async tool execution."""
        return f"Mock result from {self.name}"
    
    def execute_tool_sync(self, tool, context, tool_context, tool_config=None):
        """Mock sync tool execution."""
        return f"Mock sync result from {self.name}"


class TestEnhancedToolRegistry:
    """Test enhanced tool registry functionality."""
    
    @pytest.fixture
    def yaml_context(self):
        """Create test YAML context."""
        return YamlSystemContext(system_name="test_system")
    
    @pytest.fixture
    def tool_config(self):
        """Create test tool registry config."""
        return ToolRegistryConfig(name="test_tool_registry")
    
    @pytest.fixture
    def registry(self, tool_config, yaml_context):
        """Create test tool registry."""
        return EnhancedToolRegistry(config=tool_config, yaml_context=yaml_context)
    
    def test_registry_initialization(self, registry):
        """Test tool registry initialization."""
        assert registry.name == "test_tool_registry"
        assert registry.config.enable_dynamic_loading is True
    
    def test_strategy_registration(self, registry):
        """Test strategy registration."""
        strategy = MockToolExecutionStrategy("test_strategy")
        
        registry.register_strategy("test", strategy)
        
        assert "test" in registry.strategies
        assert registry.strategies["test"] is strategy
    
    def test_tool_registration_and_execution(self, registry):
        """Test tool registration and execution."""
        # Register a strategy first
        strategy = MockToolExecutionStrategy("tool_strategy")
        registry.register_strategy("tool", strategy)
        registry.set_default_strategy(strategy)
        
        # Mock tool function
        def mock_tool(arg1: str) -> str:
            return f"Tool result: {arg1}"
        
        registry.register_tool("mock_tool", mock_tool, strategy_name="tool")
        
        assert registry.is_tool_registered("mock_tool")
        
        # Test tool metadata
        metadata = registry.get_tool_metadata("mock_tool")
        assert metadata is not None
        assert metadata["strategy_name"] == "tool"
    
    @pytest.mark.asyncio
    async def test_tool_execution_async(self, registry):
        """Test async tool execution."""
        strategy = MockToolExecutionStrategy("async_strategy")
        registry.register_strategy("async", strategy)
        
        def sample_tool():
            return "sample result"
        
        registry.register_tool("sample_tool", sample_tool, strategy_name="async")
        
        # Mock invocation context
        context = Mock(spec=InvocationContext)
        yaml_context = YamlSystemContext(system_name="test")
        
        result = await registry.execute_tool("sample_tool", context, yaml_context)
        assert result == "Mock result from async_strategy"
    
    def test_max_tools_limit(self, yaml_context):
        """Test maximum tools limit enforcement."""
        config = ToolRegistryConfig(name="limited_registry", max_tools=2)
        registry = EnhancedToolRegistry(config=config, yaml_context=yaml_context)
        
        strategy = MockToolExecutionStrategy()
        registry.set_default_strategy(strategy)
        
        # Register up to limit
        registry.register_tool("tool1", lambda: "result1")
        registry.register_tool("tool2", lambda: "result2")
        
        # Should fail when limit exceeded
        with pytest.raises(YamlSystemError, match="Maximum tools limit.*reached"):
            registry.register_tool("tool3", lambda: "result3")
    
    def test_tool_unregistration(self, registry):
        """Test tool unregistration."""
        strategy = MockToolExecutionStrategy()
        registry.set_default_strategy(strategy)
        
        registry.register_tool("temp_tool", lambda: "temp")
        
        assert registry.is_tool_registered("temp_tool")
        
        success = registry.unregister_tool("temp_tool")
        assert success is True
        assert not registry.is_tool_registered("temp_tool")
        
        # Unregistering non-existent tool should return False
        success = registry.unregister_tool("nonexistent")
        assert success is False
    
    def test_find_tools_by_strategy(self, registry):
        """Test finding tools by strategy."""
        strategy1 = MockToolExecutionStrategy("strategy1")
        strategy2 = MockToolExecutionStrategy("strategy2")
        
        registry.register_strategy("s1", strategy1)
        registry.register_strategy("s2", strategy2)
        
        registry.register_tool("tool1", lambda: "1", strategy_name="s1")
        registry.register_tool("tool2", lambda: "2", strategy_name="s1")
        registry.register_tool("tool3", lambda: "3", strategy_name="s2")
        
        s1_tools = registry.find_tools_by_strategy("s1")
        assert sorted(s1_tools) == ["tool1", "tool2"]
        
        s2_tools = registry.find_tools_by_strategy("s2")
        assert s2_tools == ["tool3"]
    
    @pytest.mark.asyncio
    async def test_registry_lifecycle(self, registry):
        """Test tool registry lifecycle."""
        await registry.startup()
        assert registry._is_started is True
        
        await registry.shutdown()
        assert registry._is_shutdown is True
        assert registry._is_started is False
    
    def test_registry_stats(self, registry):
        """Test tool registry statistics."""
        strategy = MockToolExecutionStrategy()
        registry.register_strategy("test", strategy)
        registry.register_tool("tool1", lambda: "1", strategy_name="test")
        registry.register_tool("tool2", lambda: "2", strategy_name="test")
        
        stats = registry.get_registry_stats()
        
        assert stats["name"] == "test_tool_registry"
        assert stats["dynamic_loading_enabled"] is True
        assert "total_strategies" in stats
        assert "total_tools" in stats


@pytest.mark.asyncio
class TestRegistryEvents:
    """Test registry event system."""
    
    @pytest.fixture
    def registry(self):
        """Create registry with events enabled."""
        config = AgentRegistryConfig(name="event_test_registry")
        yaml_context = YamlSystemContext(system_name="test")
        return EnhancedAgentRegistry(config=config, yaml_context=yaml_context)
    
    def test_event_listener_management(self, registry):
        """Test adding and removing event listeners."""
        events_received = []
        
        def event_listener(event: RegistryEvent):
            events_received.append(event)
        
        # Add listener
        registry.add_event_listener(event_listener)
        
        # Register agent to trigger event
        agent = MockTestAgent("event_agent")
        registry.register_agent("event_agent", agent)
        
        # Should have received registration event
        assert len(events_received) == 1
        assert events_received[0].event_type == RegistryEventType.REGISTERED
        assert events_received[0].item_name == "event_agent"
        
        # Remove listener
        registry.remove_event_listener(event_listener)
        
        # Unregister agent - should not receive event
        registry.unregister_agent("event_agent")
        assert len(events_received) == 1  # No new events
    
    def test_hot_swap_events(self, registry):
        """Test events during hot-swapping."""
        events_received = []
        
        def event_listener(event: RegistryEvent):
            events_received.append(event)
        
        registry.add_event_listener(event_listener)
        
        # Register initial agent
        agent1 = MockTestAgent("swap_agent")
        registry.register_agent("swap_agent", agent1)
        
        # Hot-swap with new agent
        agent2 = MockTestAgent("swap_agent")
        registry.register_agent("swap_agent", agent2)
        
        # Should have received both registration and update events
        assert len(events_received) == 2
        assert events_received[0].event_type == RegistryEventType.REGISTERED
        assert events_received[1].event_type == RegistryEventType.UPDATED
        
        # Check update event has previous agent info
        update_event = events_received[1]
        assert hasattr(update_event, 'replaced_agent')


@pytest.mark.asyncio
class TestRegistryHealthMonitoring:
    """Test registry health monitoring functionality."""
    
    @pytest.fixture
    def registry(self):
        """Create registry with health monitoring."""
        config = AgentRegistryConfig(name="health_test_registry")
        yaml_context = YamlSystemContext(system_name="test")
        return EnhancedAgentRegistry(config=config, yaml_context=yaml_context)
    
    async def test_health_status_updates(self, registry):
        """Test health status updates."""
        agent = MockTestAgent("healthy_agent")
        registry.register_agent("healthy_agent", agent)
        
        # Check initial health status
        health = registry.get_health_info("healthy_agent")
        assert health is not None
        assert health.status == RegistryHealthStatus.HEALTHY
        
        # Update health status
        registry.update_health_status(
            "healthy_agent", 
            RegistryHealthStatus.DEGRADED,
            {"reason": "test degradation"}
        )
        
        health = registry.get_health_info("healthy_agent")
        assert health.status == RegistryHealthStatus.DEGRADED
        assert health.details["reason"] == "test degradation"
    
    async def test_health_check_lifecycle(self, registry):
        """Test health check lifecycle."""
        agent = MockTestAgent("lifecycle_agent")
        registry.register_agent("lifecycle_agent", agent)
        
        # Start registry to enable health monitoring
        await registry.startup()
        
        # Health info should exist
        health = registry.get_health_info("lifecycle_agent")
        assert health is not None
        
        # Shutdown should cleanup
        await registry.shutdown()
    
    def test_get_all_health_info(self, registry):
        """Test getting all health information."""
        registry.register_agent("agent1", MockTestAgent("agent1"))
        registry.register_agent("agent2", MockTestAgent("agent2"))
        
        # Update different health statuses
        registry.update_health_status("agent1", RegistryHealthStatus.HEALTHY)
        registry.update_health_status("agent2", RegistryHealthStatus.DEGRADED)
        
        all_health = registry.get_all_health_info()
        assert len(all_health) == 2
        assert all_health["agent1"].status == RegistryHealthStatus.HEALTHY
        assert all_health["agent2"].status == RegistryHealthStatus.DEGRADED


if __name__ == "__main__":
    pytest.main([__file__])