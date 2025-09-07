"""Integration tests for Enhanced Tool Registry with all ADK tool types.

Tests the complete tool registry system with real-world scenarios,
including lifecycle management, hot-swapping, and multi-tool interactions.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from google_adk_extras.runners.registry.tool_registry import (
    EnhancedToolRegistry,
    ToolType,
    ToolHealthStatus,
    ToolRegistrationEvent,
    ToolInfo
)
from google_adk_extras.runners.registry.config import ToolRegistryConfig
from google_adk_extras.runners.errors import YamlSystemContext
from google_adk_extras.runners.registry.base import RegistryEventType


class TestEnhancedToolRegistryIntegration:
    """Integration test suite for Enhanced Tool Registry."""

    @pytest.fixture
    def registry_config(self):
        """Create comprehensive registry configuration for testing."""
        return ToolRegistryConfig(
            name="integration_test_registry",
            validate_tools_on_registration=True,
            enable_dynamic_loading=True,
            max_tools=100,
            max_concurrent_executions=10,
            allowed_tool_types=["function", "mcp", "openapi", "agent", "google", "google_api", "toolset"]
        )

    @pytest.fixture
    def registry(self, registry_config):
        """Create enhanced tool registry for integration testing."""
        yaml_context = YamlSystemContext(system_name="IntegrationTest")
        return EnhancedToolRegistry(
            config=registry_config,
            yaml_context=yaml_context
        )

    @pytest.fixture
    def event_collector(self):
        """Create event collector for testing registry events."""
        events = []
        
        def collect_event(event):
            events.append(event)
        
        return events, collect_event

    # Comprehensive Multi-Tool Type Registration Tests

    @pytest.mark.asyncio
    async def test_multi_tool_type_registration(self, registry, event_collector):
        """Test registering multiple tool types simultaneously."""
        events, collector = event_collector
        registry.add_event_listener(collector)
        
        # Register FunctionTool
        def sample_function(message: str) -> str:
            """Sample function for testing."""
            return f"Hello, {message}!"
        
        with patch('google_adk_extras.runners.registry.tool_registry.FunctionTool') as mock_ft:
            mock_function_tool = Mock()
            mock_function_tool.name = "sample_function"
            mock_function_tool.description = "Sample function for testing."
            mock_ft.return_value = mock_function_tool
            
            func_result = await registry.register_function_tool(
                "sample_function", sample_function
            )
        
        # Register MCP Tool
        mock_mcp_tool = Mock()
        mock_mcp_tool.name = "mcp_tool"
        mock_mcp_tool.description = "MCP tool for testing"
        mock_mcp_tool._mcp_session_manager = AsyncMock()
        mock_mcp_tool._mcp_session_manager.create_session.return_value = Mock()
        
        mcp_result = await registry.register_mcp_tool(
            "mcp_tool", mock_mcp_tool, test_connection=False
        )
        
        # Register OpenAPI Tool
        mock_rest_tool = Mock()
        mock_rest_tool.name = "api_tool"
        mock_rest_tool.description = "REST API tool"
        mock_declaration = Mock()
        mock_declaration.parameters = Mock()
        mock_rest_tool._get_declaration.return_value = mock_declaration
        
        api_result = await registry.register_openapi_tool(
            "api_tool", mock_rest_tool, validate_schema=False
        )
        
        # Register Agent Tool
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_agent.description = "Test agent"
        mock_agent_tool = Mock()
        mock_agent_tool.name = "agent_tool"
        mock_agent_tool.agent = mock_agent
        
        agent_result = await registry.register_agent_tool(
            "agent_tool", mock_agent_tool, validate_agent=False
        )
        
        # Register Google Tool
        mock_google_tool = Mock()
        mock_google_tool.name = "google_tool"
        mock_google_tool.__class__.__name__ = "GoogleTool"
        mock_google_tool._credentials_manager = Mock()
        
        # Mock metadata extraction
        with patch.object(registry, '_extract_google_tool_metadata', return_value={"has_credentials": True}):
            google_result = await registry.register_google_tool(
                "google_tool", mock_google_tool, validate_credentials=False
            )
        
        # Verify all registrations succeeded
        assert func_result is True
        assert mcp_result is True
        assert api_result is True
        assert agent_result is True
        assert google_result is True
        
        # Verify tool types are tracked
        tool_types = registry.get_tool_types()
        assert tool_types[ToolType.FUNCTION] == 1
        assert tool_types[ToolType.MCP] == 1
        assert tool_types[ToolType.OPENAPI] == 1
        assert tool_types[ToolType.AGENT] == 1
        assert tool_types[ToolType.GOOGLE] == 1
        
        # Verify events were emitted (registration + health events)
        assert len(events) >= 5  # At least one for each registration
        registration_events = [e for e in events if isinstance(e, ToolRegistrationEvent)]
        assert len(registration_events) == 5  # One registration event per tool
        for event in registration_events:
            assert event.event_type == RegistryEventType.REGISTERED

    @pytest.mark.asyncio
    async def test_toolset_registration_and_auto_discovery(self, registry):
        """Test toolset registration with automatic tool discovery."""
        # Create mock toolset with multiple tools
        mock_toolset = AsyncMock()
        
        # Mock tools returned by toolset
        mock_tool1 = Mock()
        mock_tool1.name = "toolset_tool1"
        mock_tool2 = Mock()
        mock_tool2.name = "toolset_tool2"
        mock_tool3 = Mock()
        mock_tool3.name = "toolset_tool3"
        
        mock_toolset.get_tools.return_value = [mock_tool1, mock_tool2, mock_tool3]
        
        # Mock tool type detection
        with patch.object(registry, 'detect_tool_type', return_value=ToolType.FUNCTION):
            result = await registry.register_toolset(
                "test_toolset",
                mock_toolset,
                auto_register_tools=True,
                metadata={"source": "integration_test"}
            )
        
        assert result is True
        assert "test_toolset" in registry._toolsets
        
        # Verify individual tools were registered
        assert "test_toolset.toolset_tool1" in registry._registered_tools
        assert "test_toolset.toolset_tool2" in registry._registered_tools
        assert "test_toolset.toolset_tool3" in registry._registered_tools
        
        # Verify toolset metadata was propagated
        for i in range(1, 4):
            tool_name = f"test_toolset.toolset_tool{i}"
            tool_info = registry._registered_tools[tool_name]
            assert tool_info.metadata.get("parent_toolset") == "test_toolset"
            assert tool_info.metadata.get("source") == "integration_test"
        
        # Test getting tools by toolset
        toolset_tools = registry.get_toolset_tools("test_toolset")
        expected_tools = ["test_toolset.toolset_tool1", "test_toolset.toolset_tool2", "test_toolset.toolset_tool3"]
        assert set(toolset_tools) == set(expected_tools)

    # Tool Lifecycle Management Tests

    @pytest.mark.asyncio
    async def test_tool_lifecycle_management(self, registry, event_collector):
        """Test complete tool lifecycle: register, use, update, unregister."""
        events, collector = event_collector
        registry.add_event_listener(collector)
        
        # 1. Register tool
        def lifecycle_test_func(input_data: str) -> str:
            """Function for lifecycle testing."""
            return input_data.upper()
        
        with patch('google_adk_extras.runners.registry.tool_registry.FunctionTool') as mock_ft:
            mock_function_tool = Mock()
            mock_function_tool.name = "lifecycle_tool"
            mock_function_tool.description = "Function for lifecycle testing."
            mock_ft.return_value = mock_function_tool
            
            register_result = await registry.register_function_tool(
                "lifecycle_tool", lifecycle_test_func
            )
        
        assert register_result is True
        assert "lifecycle_tool" in registry._registered_tools
        
        # 2. Simulate tool usage
        tool_info = registry._registered_tools["lifecycle_tool"]
        assert tool_info.usage_count == 0
        
        # Simulate multiple usages
        for i in range(5):
            tool_info.mark_used()
        
        assert tool_info.usage_count == 5
        assert tool_info.last_used is not None
        
        # 3. Update tool (re-register with same name)
        def updated_lifecycle_func(input_data: str, prefix: str = "UPDATED") -> str:
            """Updated function for lifecycle testing."""
            return f"{prefix}: {input_data.upper()}"
        
        with patch('google_adk_extras.runners.registry.tool_registry.FunctionTool') as mock_ft:
            mock_updated_tool = Mock()
            mock_updated_tool.name = "lifecycle_tool"
            mock_updated_tool.description = "Updated function for lifecycle testing."
            mock_ft.return_value = mock_updated_tool
            
            update_result = await registry.register_function_tool(
                "lifecycle_tool", updated_lifecycle_func
            )
        
        assert update_result is True
        # Usage stats should be preserved in a real implementation
        # but reset in this mock scenario
        
        # 4. Unregister tool
        unregister_result = registry.unregister_tool("lifecycle_tool")
        assert unregister_result is True
        assert "lifecycle_tool" not in registry._registered_tools
        
        # Verify tool type counter was decremented
        tool_types = registry.get_tool_types()
        assert tool_types[ToolType.FUNCTION] == 0
        
        # Verify events
        registration_events = [e for e in events if e.event_type in [RegistryEventType.REGISTERED, RegistryEventType.UPDATED]]
        unregistration_events = [e for e in events if e.event_type == RegistryEventType.UNREGISTERED]
        
        assert len(registration_events) == 2  # Initial + update
        assert len(unregistration_events) == 1

    @pytest.mark.asyncio
    async def test_hot_swapping_tools(self, registry):
        """Test hot-swapping tools without service interruption."""
        # Register initial tool
        def original_tool(data: str) -> str:
            """Original tool implementation."""
            return f"ORIGINAL: {data}"
        
        with patch('google_adk_extras.runners.registry.tool_registry.FunctionTool') as mock_ft:
            mock_tool_v1 = Mock()
            mock_tool_v1.name = "swappable_tool"
            mock_tool_v1.description = "Original tool implementation."
            mock_ft.return_value = mock_tool_v1
            
            result1 = await registry.register_function_tool(
                "swappable_tool", original_tool
            )
        
        assert result1 is True
        original_tool_info = registry._registered_tools["swappable_tool"]
        
        # Simulate some usage
        original_tool_info.mark_used()
        original_tool_info.mark_used()
        original_usage = original_tool_info.usage_count
        
        # Hot-swap with new implementation
        def updated_tool(data: str, version: str = "2.0") -> str:
            """Updated tool implementation."""
            return f"UPDATED_V{version}: {data}"
        
        with patch('google_adk_extras.runners.registry.tool_registry.FunctionTool') as mock_ft:
            mock_tool_v2 = Mock()
            mock_tool_v2.name = "swappable_tool"
            mock_tool_v2.description = "Updated tool implementation."
            mock_ft.return_value = mock_tool_v2
            
            result2 = await registry.register_function_tool(
                "swappable_tool", updated_tool
            )
        
        assert result2 is True
        
        # Verify tool was updated, not duplicated
        assert len([name for name in registry._registered_tools.keys() if "swappable_tool" in name]) == 1
        
        # Verify new tool info
        updated_tool_info = registry._registered_tools["swappable_tool"]
        assert updated_tool_info.tool != original_tool_info.tool

    # Health Monitoring Integration Tests

    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self, registry):
        """Test health monitoring across different tool types."""
        # Register tools with different health statuses
        tools_data = [
            ("healthy_function", ToolType.FUNCTION, ToolHealthStatus.HEALTHY),
            ("degraded_mcp", ToolType.MCP, ToolHealthStatus.DEGRADED),
            ("unhealthy_api", ToolType.OPENAPI, ToolHealthStatus.UNHEALTHY),
            ("connection_error_tool", ToolType.MCP, ToolHealthStatus.CONNECTION_ERROR),
        ]
        
        for tool_name, tool_type, health_status in tools_data:
            mock_tool = Mock()
            mock_tool.name = tool_name
            tool_info = ToolInfo(tool_name, mock_tool, tool_type)
            tool_info.health_status = health_status
            registry._registered_tools[tool_name] = tool_info
        
        # Test health status queries
        assert registry.get_tool_health("healthy_function") == ToolHealthStatus.HEALTHY
        assert registry.get_tool_health("degraded_mcp") == ToolHealthStatus.DEGRADED
        assert registry.get_tool_health("unhealthy_api") == ToolHealthStatus.UNHEALTHY
        assert registry.get_tool_health("connection_error_tool") == ToolHealthStatus.CONNECTION_ERROR
        
        # Test health filtering
        healthy_tools = [
            name for name in registry._registered_tools.keys()
            if registry.get_tool_health(name) == ToolHealthStatus.HEALTHY
        ]
        assert len(healthy_tools) == 1
        assert "healthy_function" in healthy_tools
        
        unhealthy_tools = [
            name for name in registry._registered_tools.keys()
            if registry.get_tool_health(name) in [ToolHealthStatus.UNHEALTHY, ToolHealthStatus.CONNECTION_ERROR]
        ]
        assert len(unhealthy_tools) == 2

    # Error Handling and Recovery Tests

    @pytest.mark.asyncio
    async def test_registration_error_handling(self, registry):
        """Test error handling during tool registration."""
        # Test registration with validation errors
        non_callable = "not a function"
        
        result = await registry.register_function_tool(
            "invalid_function",
            non_callable,
            validate_signature=True
        )
        
        assert result is False
        assert "invalid_function" not in registry._registered_tools
        
        # Test MCP tool with connection failure
        mock_mcp_tool = Mock()
        mock_mcp_tool.name = "failing_mcp"
        mock_mcp_tool.description = "MCP tool that fails connection"
        
        mock_session_manager = AsyncMock()
        mock_session_manager.create_session.side_effect = Exception("Connection failed")
        mock_mcp_tool._mcp_session_manager = mock_session_manager
        
        # Should succeed registration but log warning
        result = await registry.register_mcp_tool(
            "failing_mcp",
            mock_mcp_tool,
            test_connection=True
        )
        
        assert result is True  # Registration succeeds despite connection failure
        assert "failing_mcp" in registry._registered_tools

    @pytest.mark.asyncio
    async def test_toolset_partial_failure_recovery(self, registry):
        """Test toolset registration with partial failures."""
        mock_toolset = AsyncMock()
        
        # Mock tools where one will fail registration
        mock_tool1 = Mock()
        mock_tool1.name = "good_tool"
        
        mock_tool2 = Mock()
        mock_tool2.name = "bad_tool"
        
        mock_toolset.get_tools.return_value = [mock_tool1, mock_tool2]
        
        # Mock registration to fail for the second tool
        original_register = registry.register_tool
        
        def failing_register(name, tool, tool_type=None, metadata=None):
            if "bad_tool" in name:
                raise Exception("Registration failed")
            return original_register(name, tool, tool_type, metadata=metadata)
        
        registry.register_tool = failing_register
        
        # This should fail and clean up
        result = await registry.register_toolset(
            "partial_failure_toolset",
            mock_toolset,
            auto_register_tools=True
        )
        
        assert result is False
        assert "partial_failure_toolset" not in registry._toolsets
        assert "partial_failure_toolset.good_tool" not in registry._registered_tools
        assert "partial_failure_toolset.bad_tool" not in registry._registered_tools

    # Performance and Concurrency Tests

    @pytest.mark.asyncio
    async def test_concurrent_tool_operations(self, registry):
        """Test concurrent tool registration and operations."""
        async def register_function_tool_async(name: str, index: int):
            def test_func(data: str) -> str:
                return f"Tool {index}: {data}"
            
            with patch('google_adk_extras.runners.registry.tool_registry.FunctionTool') as mock_ft:
                mock_tool = Mock()
                mock_tool.name = name
                mock_tool.description = f"Test function {index}"
                mock_ft.return_value = mock_tool
                
                return await registry.register_function_tool(name, test_func)
        
        # Register multiple tools concurrently
        tasks = [
            register_function_tool_async(f"concurrent_tool_{i}", i)
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All registrations should succeed
        assert all(results)
        
        # Verify all tools are registered
        for i in range(10):
            assert f"concurrent_tool_{i}" in registry._registered_tools
        
        # Verify tool type counter
        tool_types = registry.get_tool_types()
        assert tool_types[ToolType.FUNCTION] == 10

    @pytest.mark.asyncio
    async def test_registry_statistics_comprehensive(self, registry):
        """Test comprehensive registry statistics."""
        # Register various tool types
        tool_configs = [
            ("func1", ToolType.FUNCTION),
            ("func2", ToolType.FUNCTION),
            ("mcp1", ToolType.MCP),
            ("api1", ToolType.OPENAPI),
            ("agent1", ToolType.AGENT),
            ("google1", ToolType.GOOGLE),
        ]
        
        for name, tool_type in tool_configs:
            mock_tool = Mock()
            mock_tool.name = name
            tool_info = ToolInfo(name, mock_tool, tool_type)
            
            # Simulate some usage and errors
            if name == "func1":
                tool_info.usage_count = 10
                tool_info.error_count = 1
            elif name == "mcp1":
                tool_info.usage_count = 5
                tool_info.error_count = 2
            # Others default to usage_count=0, error_count=0
            
            registry._registered_tools[name] = tool_info
        
        # Test registry statistics
        stats = registry.get_registry_stats()
        
        assert stats['total_tools'] == 6
        assert stats['tool_type_distribution'][ToolType.FUNCTION] == 2
        assert stats['tool_type_distribution'][ToolType.MCP] == 1
        assert stats['tool_type_distribution'][ToolType.OPENAPI] == 1
        assert stats['tool_type_distribution'][ToolType.AGENT] == 1
        assert stats['tool_type_distribution'][ToolType.GOOGLE] == 1
        
        assert stats['total_tool_usage'] == 15  # 10 + 5 + 0 + 0 + 0 + 0
        assert stats['total_tool_errors'] == 3   # 1 + 2 + 0 + 0 + 0 + 0
        assert stats['overall_error_rate'] == 0.2  # 3/15

    # Advanced Feature Tests

    @pytest.mark.asyncio
    async def test_tool_metadata_comprehensive_extraction(self, registry):
        """Test comprehensive metadata extraction for all tool types."""
        # Test FunctionTool metadata
        def complex_function(
            required_param: str,
            optional_param: int = 42,
            *args,
            **kwargs
        ) -> Dict[str, Any]:
            """Complex function with various parameter types."""
            return {"result": f"{required_param}-{optional_param}"}
        
        mock_function_tool = Mock()
        mock_function_tool._get_mandatory_args.return_value = ["required_param"]
        mock_function_tool._ignore_params = ["tool_context"]
        
        mock_declaration = Mock()
        mock_declaration.name = "complex_function"
        mock_declaration.description = "Complex function with various parameter types."
        mock_declaration.parameters = Mock()
        mock_function_tool._get_declaration.return_value = mock_declaration
        
        func_metadata = await registry._extract_function_tool_metadata(
            mock_function_tool, complex_function
        )
        
        assert func_metadata['tool_type'] == 'function'
        assert func_metadata['function_name'] == 'complex_function'
        assert func_metadata['is_coroutine'] is False
        assert 'signature' in func_metadata
        assert 'parameters' in func_metadata
        assert func_metadata['mandatory_args'] == ["required_param"]
        
        # Test MCP tool metadata with comprehensive setup
        mock_mcp_tool = Mock()
        mock_base_tool = Mock()
        mock_base_tool.name = "comprehensive_mcp"
        mock_base_tool.description = "Comprehensive MCP tool"
        mock_base_tool.inputSchema = {
            "type": "object",
            "properties": {
                "input": {"type": "string"},
                "options": {"type": "object"}
            },
            "required": ["input"]
        }
        mock_mcp_tool._mcp_tool = mock_base_tool
        
        mock_session_manager = Mock()
        mock_session_manager.__class__.__name__ = "MCPSessionManager"
        mock_mcp_tool._mcp_session_manager = mock_session_manager
        
        mcp_metadata = await registry._extract_mcp_tool_metadata(mock_mcp_tool)
        
        assert mcp_metadata['tool_type'] == 'mcp'
        assert mcp_metadata['mcp_name'] == 'comprehensive_mcp'
        assert mcp_metadata['input_schema']['type'] == 'object'
        assert 'input' in mcp_metadata['input_schema']['properties']
        assert mcp_metadata['session_manager_type'] == 'MCPSessionManager'

    @pytest.mark.asyncio
    async def test_event_system_comprehensive(self, registry, event_collector):
        """Test comprehensive event system functionality."""
        events, collector = event_collector
        registry.add_event_listener(collector)
        
        # Test various events
        def test_func():
            """Test function."""
            pass
        
        with patch('google_adk_extras.runners.registry.tool_registry.FunctionTool') as mock_ft:
            mock_tool = Mock()
            mock_tool.name = "event_test_tool"
            mock_ft.return_value = mock_tool
            
            # Registration event
            await registry.register_function_tool("event_test_tool", test_func)
            
            # Update event (re-register)
            await registry.register_function_tool("event_test_tool", test_func)
            
            # Unregistration event
            registry.unregister_tool("event_test_tool")
        
        # Verify events - filter to ToolRegistrationEvent only
        tool_events = [e for e in events if isinstance(e, ToolRegistrationEvent)]
        assert len(tool_events) >= 3
        
        registration_events = [e for e in tool_events if e.event_type == RegistryEventType.REGISTERED]
        update_events = [e for e in tool_events if e.event_type == RegistryEventType.UPDATED]
        unregistration_events = [e for e in tool_events if e.event_type == RegistryEventType.UNREGISTERED]
        
        assert len(registration_events) >= 1
        assert len(update_events) >= 1
        assert len(unregistration_events) >= 1
        
        # Verify event data
        for event in tool_events:
            assert isinstance(event, ToolRegistrationEvent)
            assert event.registry_name == "integration_test_registry"
            assert event.item_name == "event_test_tool"

    @pytest.mark.asyncio
    async def test_registry_limits_and_validation(self, registry):
        """Test registry limits and validation enforcement."""
        # Test max tools limit
        original_max = registry.config.max_tools
        registry.config.max_tools = 3
        
        # Register up to limit
        for i in range(3):
            def test_func():
                return f"result {i}"
            
            with patch('google_adk_extras.runners.registry.tool_registry.FunctionTool') as mock_ft:
                mock_tool = Mock()
                mock_tool.name = f"limited_tool_{i}"
                mock_ft.return_value = mock_tool
                
                result = await registry.register_function_tool(f"limited_tool_{i}", test_func)
                assert result is True
        
        # Try to exceed limit
        def excess_func():
            return "excess"
        
        with patch('google_adk_extras.runners.registry.tool_registry.FunctionTool') as mock_ft:
            mock_tool = Mock()
            mock_tool.name = "excess_tool"
            mock_ft.return_value = mock_tool
            
            result = await registry.register_function_tool("excess_tool", excess_func)
            assert result is False  # Should fail due to limit
        
        # Restore original limit
        registry.config.max_tools = original_max

    # Cleanup and Resource Management Tests

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_unregistration(self, registry):
        """Test proper resource cleanup when tools are unregistered."""
        # Register tool with mock resources
        mock_mcp_tool = Mock()
        mock_mcp_tool.name = "resource_tool"
        mock_mcp_tool.description = "Tool with resources"
        
        # Mock session manager with close method
        mock_session_manager = Mock()
        mock_session_manager.close = AsyncMock()
        mock_mcp_tool._mcp_session_manager = mock_session_manager
        
        tool_name = "resource_tool"
        registry.register_tool(tool_name, mock_mcp_tool, ToolType.MCP)
        
        assert tool_name in registry._registered_tools
        
        # Unregister and verify cleanup
        result = registry.unregister_tool(tool_name)
        assert result is True
        assert tool_name not in registry._registered_tools
        
        # Verify cache cleanup
        if registry._enable_caching:
            cached_tool = registry._get_from_cache(tool_name)
            assert cached_tool is None


@pytest.mark.integration
class TestRealWorldScenarios:
    """Real-world integration test scenarios."""

    @pytest.fixture
    def production_like_registry(self):
        """Create production-like registry configuration."""
        config = ToolRegistryConfig(
            name="production_registry",
            validate_tools_on_registration=True,
            enable_dynamic_loading=True,
            max_tools=1000,
            max_concurrent_executions=50,
            allowed_tool_types=None  # Allow all types
        )
        yaml_context = YamlSystemContext(system_name="ProductionTest")
        return EnhancedToolRegistry(config=config, yaml_context=yaml_context)

    @pytest.mark.asyncio
    async def test_enterprise_scale_tool_management(self, production_like_registry):
        """Test enterprise-scale tool management scenario."""
        registry = production_like_registry
        
        # Simulate registering tools from multiple sources
        tool_sources = [
            ("internal_functions", ToolType.FUNCTION, 50),
            ("mcp_integrations", ToolType.MCP, 20),
            ("api_endpoints", ToolType.OPENAPI, 30),
            ("agent_tools", ToolType.AGENT, 15),
            ("google_services", ToolType.GOOGLE_API, 10),
        ]
        
        total_registered = 0
        
        for source_name, tool_type, count in tool_sources:
            for i in range(count):
                tool_name = f"{source_name}_{i}"
                mock_tool = Mock()
                mock_tool.name = tool_name
                
                registry.register_tool(
                    tool_name,
                    mock_tool,
                    tool_type,
                    metadata={"source": source_name, "index": i}
                )
                total_registered += 1
        
        # Verify scale
        assert len(registry._registered_tools) == total_registered
        
        # Test bulk operations
        function_tools = registry.get_tools_by_type(ToolType.FUNCTION)
        assert len(function_tools) == 50
        
        mcp_tools = registry.get_tools_by_type(ToolType.MCP)
        assert len(mcp_tools) == 20
        
        # Test statistics at scale
        stats = registry.get_registry_stats()
        assert stats['total_tools'] == total_registered
        
        # Test performance of lookups
        start_time = time.time()
        for i in range(100):
            tool_name = f"internal_functions_{i % 50}"
            tool_info = registry._registered_tools.get(tool_name)
            assert tool_info is not None
        lookup_time = time.time() - start_time
        
        # Should complete 100 lookups quickly (< 1 second)
        assert lookup_time < 1.0

    @pytest.mark.asyncio
    async def test_microservices_tool_ecosystem(self, production_like_registry):
        """Test microservices-like tool ecosystem scenario."""
        registry = production_like_registry
        
        # Simulate multiple microservices each providing toolsets
        microservices = [
            {
                "name": "user_service",
                "tools": ["create_user", "get_user", "update_user", "delete_user"],
                "type": ToolType.OPENAPI
            },
            {
                "name": "notification_service", 
                "tools": ["send_email", "send_sms", "push_notification"],
                "type": ToolType.MCP
            },
            {
                "name": "analytics_service",
                "tools": ["track_event", "generate_report", "get_metrics"],
                "type": ToolType.FUNCTION
            },
            {
                "name": "ai_service",
                "tools": ["text_analysis", "image_recognition", "recommendation"],
                "type": ToolType.AGENT
            }
        ]
        
        # Register all microservice toolsets
        for service in microservices:
            mock_toolset = AsyncMock()
            mock_tools = []
            
            for tool_name in service["tools"]:
                mock_tool = Mock()
                mock_tool.name = tool_name
                mock_tools.append(mock_tool)
            
            mock_toolset.get_tools.return_value = mock_tools
            
            with patch.object(registry, 'detect_tool_type', return_value=service["type"]):
                result = await registry.register_toolset(
                    service["name"],
                    mock_toolset,
                    auto_register_tools=True,
                    metadata={"service_type": "microservice", "version": "1.0"}
                )
                
                assert result is True
        
        # Verify ecosystem
        assert len(registry._toolsets) == 4
        
        # Verify cross-service tool access
        user_tools = registry.get_toolset_tools("user_service")
        assert len(user_tools) == 4
        assert "user_service.create_user" in user_tools
        
        # Test service discovery
        all_service_tools = []
        for service_name in registry.get_registered_toolsets():
            service_tools = registry.get_toolset_tools(service_name)
            all_service_tools.extend(service_tools)
        
        expected_total = sum(len(service["tools"]) for service in microservices)
        assert len(all_service_tools) == expected_total
        
        # Test tool type distribution
        tool_types = registry.get_tool_types()
        assert tool_types[ToolType.OPENAPI] == 4  # user_service
        assert tool_types[ToolType.MCP] == 3      # notification_service
        assert tool_types[ToolType.FUNCTION] == 3 # analytics_service
        assert tool_types[ToolType.AGENT] == 3    # ai_service


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])