"""Unit tests for Enhanced Tool Registry Wrappers.

Tests all ADK tool type wrappers with comprehensive validation,
metadata extraction, and lifecycle management.
"""

import pytest
import asyncio
import inspect
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

from google_adk_extras.runners.registry.tool_registry import (
    EnhancedToolRegistry,
    ToolType,
    ToolHealthStatus,
    ToolInfo,
    ToolRegistrationEvent
)
from google_adk_extras.runners.registry.config import ToolRegistryConfig
from google_adk_extras.runners.errors import YamlSystemContext, YamlSystemError


class TestEnhancedToolRegistryWrappers:
    """Test suite for Enhanced Tool Registry Wrappers."""

    @pytest.fixture
    def registry_config(self):
        """Create test registry configuration."""
        return ToolRegistryConfig(
            name="test_enhanced_tool_registry",
            validate_tools_on_registration=True,
            enable_dynamic_loading=True,
            max_concurrent_executions=5
        )

    @pytest.fixture
    def yaml_context(self):
        """Create test YAML context."""
        return YamlSystemContext(system_name="TestRegistry")

    @pytest.fixture
    def registry(self, registry_config, yaml_context):
        """Create test enhanced tool registry."""
        return EnhancedToolRegistry(
            config=registry_config,
            yaml_context=yaml_context
        )

    # FunctionTool Wrapper Tests

    def test_detect_tool_type_function_tool(self, registry):
        """Test detection of FunctionTool type via class name."""
        # Create mock tool with FunctionTool class name
        mock_function_tool = Mock()
        mock_function_tool.__class__.__name__ = "FunctionTool"
        
        tool_type = registry.detect_tool_type(mock_function_tool)
        assert tool_type == ToolType.FUNCTION

    def test_detect_tool_type_by_class_name(self, registry):
        """Test tool type detection by class name fallback."""
        mock_tool = Mock()
        mock_tool.__class__.__name__ = "CustomFunctionTool"
        
        tool_type = registry.detect_tool_type(mock_tool)
        assert tool_type == ToolType.FUNCTION

    def test_detect_tool_type_unknown(self, registry):
        """Test unknown tool type detection."""
        mock_tool = Mock()
        mock_tool.__class__.__name__ = "UnknownTool"
        
        tool_type = registry.detect_tool_type(mock_tool)
        assert tool_type == ToolType.UNKNOWN

    @pytest.mark.asyncio
    async def test_register_function_tool_success(self, registry):
        """Test successful FunctionTool registration."""
        def test_function(param1: str, param2: int = 10) -> str:
            """Test function for tool registration."""
            return f"Hello {param1}, number {param2}"
        
        # Mock FunctionTool and the metadata extraction method
        with patch('google_adk_extras.runners.registry.tool_registry.FunctionTool') as mock_ft_class:
            mock_function_tool = Mock()
            mock_function_tool.name = "test_function"
            mock_function_tool.description = "Test function for tool registration."
            mock_ft_class.return_value = mock_function_tool
            
            # Mock the metadata extraction method
            with patch.object(registry, '_extract_function_tool_metadata', return_value={"description": "Test function"}):
                result = await registry.register_function_tool(
                    name="test_function",
                    function=test_function,
                    validate_signature=True,
                    validate_docstring=True
                )
                
                assert result is True
                assert "test_function" in registry._registered_tools
                tool_info = registry._registered_tools["test_function"]
                assert tool_info.tool_type == ToolType.FUNCTION
                assert tool_info.tool == mock_function_tool
                # FunctionTool is created properly
                mock_ft_class.assert_called_once_with(test_function)

    @pytest.mark.asyncio
    async def test_register_function_tool_validation_failure(self, registry):
        """Test FunctionTool registration with validation failure."""
        non_callable = "not a function"
        
        result = await registry.register_function_tool(
            name="bad_function",
            function=non_callable,
            validate_signature=True
        )
        
        assert result is False
        assert "bad_function" not in registry._registered_tools

    @pytest.mark.asyncio
    async def test_register_function_tool_no_docstring_warning(self, registry):
        """Test FunctionTool registration with missing docstring warning."""
        def function_no_docs(param: str):
            return param.upper()
        
        with patch('google_adk_extras.runners.registry.tool_registry.FunctionTool') as mock_ft_class:
            mock_function_tool = Mock()
            mock_function_tool.name = "function_no_docs"
            mock_function_tool.description = ""
            mock_ft_class.return_value = mock_function_tool
            
            with patch.object(registry, '_extract_function_tool_metadata', return_value={"description": ""}):
                with patch('google_adk_extras.runners.registry.tool_registry.logger') as mock_logger:
                    result = await registry.register_function_tool(
                        name="function_no_docs",
                        function=function_no_docs,
                        validate_docstring=True
                    )
                    
                    assert result is True
                    mock_logger.warning.assert_called()

    # MCP Tool Wrapper Tests

    @pytest.mark.asyncio
    async def test_register_mcp_tool_success(self, registry):
        """Test successful MCP tool registration."""
        mock_mcp_tool = Mock()
        mock_mcp_tool.name = "test_mcp_tool"
        mock_mcp_tool.description = "Test MCP tool"
        
        # Mock session manager
        mock_session_manager = AsyncMock()
        mock_session = Mock()
        mock_session_manager.create_session.return_value = mock_session
        mock_mcp_tool._mcp_session_manager = mock_session_manager
        
        # Mock MCP base tool
        mock_base_tool = Mock()
        mock_base_tool.name = "test_mcp_tool"
        mock_base_tool.description = "Test MCP tool"
        mock_base_tool.inputSchema = {"type": "object"}
        mock_mcp_tool._mcp_tool = mock_base_tool
        
        result = await registry.register_mcp_tool(
            name="test_mcp_tool",
            mcp_tool=mock_mcp_tool,
            test_connection=True
        )
        
        assert result is True
        assert "test_mcp_tool" in registry._registered_tools
        tool_info = registry._registered_tools["test_mcp_tool"]
        assert tool_info.tool_type == ToolType.MCP

    @pytest.mark.asyncio
    async def test_register_mcp_tool_connection_failure(self, registry):
        """Test MCP tool registration with connection failure."""
        mock_mcp_tool = Mock()
        mock_mcp_tool.name = "failing_mcp_tool"
        mock_mcp_tool.description = "MCP tool with connection issues"
        
        # Mock session manager that fails
        mock_session_manager = AsyncMock()
        mock_session_manager.create_session.side_effect = Exception("Connection failed")
        mock_mcp_tool._mcp_session_manager = mock_session_manager
        
        with patch('google_adk_extras.runners.registry.tool_registry.logger') as mock_logger:
            result = await registry.register_mcp_tool(
                name="failing_mcp_tool",
                mcp_tool=mock_mcp_tool,
                test_connection=True
            )
            
            assert result is True  # Registration succeeds but with warning
            mock_logger.warning.assert_called()

    # OpenAPI Tool Wrapper Tests

    @pytest.mark.asyncio
    async def test_register_openapi_tool_success(self, registry):
        """Test successful OpenAPI tool registration."""
        mock_rest_tool = Mock()
        mock_rest_tool.name = "test_api_tool"
        mock_rest_tool.description = "Test REST API tool"
        
        # Mock function declaration
        mock_declaration = Mock()
        mock_declaration.name = "test_api_tool"
        mock_declaration.description = "Test REST API tool"
        mock_declaration.parameters = Mock()
        mock_rest_tool._get_declaration.return_value = mock_declaration
        
        # Mock endpoint
        mock_endpoint = Mock()
        mock_endpoint.url = "https://api.example.com/test"
        mock_endpoint.method = "GET"
        mock_rest_tool.endpoint = mock_endpoint
        
        result = await registry.register_openapi_tool(
            name="test_api_tool",
            rest_api_tool=mock_rest_tool,
            validate_schema=True,
            test_endpoint=True
        )
        
        assert result is True
        assert "test_api_tool" in registry._registered_tools
        tool_info = registry._registered_tools["test_api_tool"]
        assert tool_info.tool_type == ToolType.OPENAPI

    @pytest.mark.asyncio
    async def test_register_openapi_tool_invalid_endpoint(self, registry):
        """Test OpenAPI tool registration with invalid endpoint."""
        mock_rest_tool = Mock()
        mock_rest_tool.name = "invalid_api_tool"
        mock_rest_tool.description = "API tool with invalid endpoint"
        
        # Mock invalid endpoint
        mock_endpoint = Mock()
        mock_endpoint.url = "invalid-url"
        mock_rest_tool.endpoint = mock_endpoint
        
        mock_declaration = Mock()
        mock_declaration.parameters = Mock()
        mock_rest_tool._get_declaration.return_value = mock_declaration
        
        with patch('google_adk_extras.runners.registry.tool_registry.logger') as mock_logger:
            result = await registry.register_openapi_tool(
                name="invalid_api_tool",
                rest_api_tool=mock_rest_tool,
                test_endpoint=True
            )
            
            assert result is True  # Registration succeeds but with warning
            mock_logger.warning.assert_called()

    # Agent Tool Wrapper Tests

    @pytest.mark.asyncio
    async def test_register_agent_tool_success(self, registry):
        """Test successful AgentTool registration."""
        # Mock wrapped agent
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_agent.description = "Test agent for tool wrapping"
        mock_agent.input_schema = Mock()
        mock_agent.output_schema = Mock()
        
        # Mock AgentTool
        mock_agent_tool = Mock()
        mock_agent_tool.name = "test_agent_tool"
        mock_agent_tool.description = "Agent tool wrapper"
        mock_agent_tool.agent = mock_agent
        mock_agent_tool.skip_summarization = False
        
        # Mock function declaration
        mock_declaration = Mock()
        mock_declaration.name = "test_agent_tool"
        mock_declaration.parameters = Mock()
        mock_declaration.response = Mock()
        mock_agent_tool._get_declaration.return_value = mock_declaration
        
        result = await registry.register_agent_tool(
            name="test_agent_tool",
            agent_tool=mock_agent_tool,
            validate_agent=True
        )
        
        assert result is True
        assert "test_agent_tool" in registry._registered_tools
        tool_info = registry._registered_tools["test_agent_tool"]
        assert tool_info.tool_type == ToolType.AGENT

    @pytest.mark.asyncio
    async def test_register_agent_tool_circular_reference_warning(self, registry):
        """Test AgentTool registration with circular reference warning."""
        # Mock wrapped agent with same name as tool
        mock_agent = Mock()
        mock_agent.name = "circular_tool"  # Same as tool name
        mock_agent.description = "Agent with circular reference"
        
        mock_agent_tool = Mock()
        mock_agent_tool.name = "circular_tool"
        mock_agent_tool.agent = mock_agent
        
        with patch('google_adk_extras.runners.registry.tool_registry.logger') as mock_logger:
            result = await registry.register_agent_tool(
                name="circular_tool",
                agent_tool=mock_agent_tool,
                validate_agent=True
            )
            
            assert result is True
            mock_logger.warning.assert_called()

    # Google Tool Wrapper Tests

    @pytest.mark.asyncio
    async def test_register_google_tool_success(self, registry):
        """Test successful GoogleTool registration."""
        mock_google_tool = Mock()
        mock_google_tool.name = "test_google_tool"
        mock_google_tool.description = "Test Google tool"
        mock_google_tool.__class__.__name__ = "GoogleTool"
        
        # Mock credentials manager
        mock_credentials_manager = Mock()
        mock_google_tool._credentials_manager = mock_credentials_manager
        
        # Mock metadata extraction
        with patch.object(registry, '_extract_google_tool_metadata', return_value={"has_credentials": True}):
            result = await registry.register_google_tool(
                name="test_google_tool",
                google_tool=mock_google_tool,
                validate_credentials=True
            )
            
            assert result is True
            assert "test_google_tool" in registry._registered_tools
            tool_info = registry._registered_tools["test_google_tool"]
            assert tool_info.tool_type == ToolType.GOOGLE

    @pytest.mark.asyncio
    async def test_register_google_api_tool_success(self, registry):
        """Test successful GoogleApiTool registration."""
        mock_google_api_tool = Mock()
        mock_google_api_tool.name = "test_google_api_tool"
        mock_google_api_tool.description = "Test Google API tool"
        mock_google_api_tool.__class__.__name__ = "GoogleApiTool"
        
        # Mock wrapped REST tool
        mock_rest_tool = Mock()
        mock_rest_tool.auth_credential = Mock()
        mock_google_api_tool._rest_api_tool = mock_rest_tool
        
        # Mock metadata extraction
        with patch.object(registry, '_extract_google_tool_metadata', return_value={"has_credentials": True, "api_name": "test"}):
            result = await registry.register_google_tool(
                name="test_google_api_tool",
                google_tool=mock_google_api_tool,
                validate_credentials=True
            )
            
            assert result is True
            assert "test_google_api_tool" in registry._registered_tools
            tool_info = registry._registered_tools["test_google_api_tool"]
            assert tool_info.tool_type == ToolType.GOOGLE_API

    @pytest.mark.asyncio
    async def test_register_google_tool_no_credentials_warning(self, registry):
        """Test Google tool registration with no credentials warning."""
        mock_google_tool = Mock()
        mock_google_tool.name = "no_creds_tool"
        mock_google_tool._credentials_manager = None
        mock_google_tool.__class__.__name__ = "GoogleTool"
        
        # Mock metadata extraction to return no credentials
        with patch.object(registry, '_extract_google_tool_metadata', return_value={"has_credentials": False}):
            with patch('google_adk_extras.runners.registry.tool_registry.logger') as mock_logger:
                result = await registry.register_google_tool(
                    name="no_creds_tool",
                    google_tool=mock_google_tool,
                    validate_credentials=True
                )
                
                assert result is True
                mock_logger.warning.assert_called()

    # Toolset Registration Tests

    @pytest.mark.asyncio
    async def test_register_toolset_success(self, registry):
        """Test successful toolset registration."""
        # Mock toolset
        mock_toolset = AsyncMock()
        
        # Mock tools from toolset
        mock_tool1 = Mock()
        mock_tool1.name = "tool1"
        mock_tool2 = Mock()  
        mock_tool2.name = "tool2"
        mock_toolset.get_tools.return_value = [mock_tool1, mock_tool2]
        
        # Mock detect_tool_type
        with patch.object(registry, 'detect_tool_type', return_value=ToolType.FUNCTION):
            result = await registry.register_toolset(
                name="test_toolset",
                toolset=mock_toolset,
                auto_register_tools=True
            )
        
        assert result is True
        assert "test_toolset" in registry._toolsets
        assert "test_toolset.tool1" in registry._registered_tools
        assert "test_toolset.tool2" in registry._registered_tools

    @pytest.mark.asyncio
    async def test_register_toolset_error_cleanup(self, registry):
        """Test toolset registration with error and cleanup."""
        mock_toolset = AsyncMock()
        mock_toolset.get_tools.side_effect = Exception("Toolset error")
        
        result = await registry.register_toolset(
            name="failing_toolset",
            toolset=mock_toolset,
            auto_register_tools=True
        )
        
        assert result is False
        assert "failing_toolset" not in registry._toolsets

    # Metadata Extraction Tests

    @pytest.mark.asyncio
    async def test_extract_function_tool_metadata(self, registry):
        """Test FunctionTool metadata extraction."""
        def test_func(param1: str, param2: int = 10) -> str:
            """Test function with parameters."""
            return f"{param1}: {param2}"
        
        mock_function_tool = Mock()
        mock_function_tool._get_mandatory_args.return_value = ["param1"]
        mock_function_tool._ignore_params = ["tool_context"]
        
        # Mock function declaration
        mock_declaration = Mock()
        mock_declaration.name = "test_func"
        mock_declaration.description = "Test function with parameters."
        mock_declaration.parameters = Mock()
        mock_function_tool._get_declaration.return_value = mock_declaration
        
        metadata = await registry._extract_function_tool_metadata(mock_function_tool, test_func)
        
        assert metadata['tool_type'] == 'function'
        assert metadata['function_name'] == 'test_func'
        assert metadata['is_coroutine'] is False
        assert metadata['docstring'] == "Test function with parameters."
        assert 'signature' in metadata
        assert 'parameters' in metadata
        assert metadata['mandatory_args'] == ["param1"]
        assert metadata['ignore_params'] == ["tool_context"]

    @pytest.mark.asyncio
    async def test_extract_mcp_tool_metadata(self, registry):
        """Test MCP tool metadata extraction."""
        mock_mcp_tool = Mock()
        
        # Mock MCP base tool
        mock_base_tool = Mock()
        mock_base_tool.name = "test_mcp"
        mock_base_tool.description = "Test MCP tool"
        mock_base_tool.inputSchema = {"type": "object", "properties": {}}
        mock_mcp_tool._mcp_tool = mock_base_tool
        
        # Mock session manager
        mock_session_manager = Mock()
        mock_session_manager.__class__.__name__ = "MCPSessionManager"
        mock_mcp_tool._mcp_session_manager = mock_session_manager
        
        metadata = await registry._extract_mcp_tool_metadata(mock_mcp_tool)
        
        assert metadata['tool_type'] == 'mcp'
        assert metadata['has_session_manager'] is True
        assert metadata['mcp_name'] == 'test_mcp'
        assert metadata['mcp_description'] == 'Test MCP tool'
        assert metadata['input_schema'] == {"type": "object", "properties": {}}
        assert metadata['session_manager_type'] == 'MCPSessionManager'

    # Tool Type Counter Tests

    def test_tool_type_counters_initialization(self, registry):
        """Test that tool type counters are properly initialized."""
        counters = registry.get_tool_types()
        
        # Check all tool types are initialized to 0
        for tool_type in ToolType:
            assert tool_type in counters
            assert counters[tool_type] == 0

    def test_tool_type_counters_update(self, registry):
        """Test that tool type counters are updated correctly."""
        def test_func():
            """Test function."""
            pass
        
        mock_function_tool = Mock()
        mock_function_tool.name = "test_func"
        mock_function_tool.description = "Test function."
        
        with patch('google_adk_extras.runners.registry.tool_registry.FunctionTool', 
                   return_value=mock_function_tool):
            registry.register_tool("test_func", mock_function_tool, ToolType.FUNCTION)
            
            counters = registry.get_tool_types()
            assert counters[ToolType.FUNCTION] == 1

    def test_get_tools_by_type(self, registry):
        """Test getting tools by type."""
        # Register a function tool
        mock_function_tool = Mock()
        registry._registered_tools["func_tool"] = ToolInfo(
            name="func_tool",
            tool=mock_function_tool,
            tool_type=ToolType.FUNCTION
        )
        
        # Register an MCP tool
        mock_mcp_tool = Mock()
        registry._registered_tools["mcp_tool"] = ToolInfo(
            name="mcp_tool", 
            tool=mock_mcp_tool,
            tool_type=ToolType.MCP
        )
        
        function_tools = registry.get_tools_by_type(ToolType.FUNCTION)
        mcp_tools = registry.get_tools_by_type(ToolType.MCP)
        
        assert function_tools == ["func_tool"]
        assert mcp_tools == ["mcp_tool"]

    def test_get_authenticated_tools(self, registry):
        """Test getting authenticated tools."""
        # Mock tool with auth
        mock_auth_tool = Mock()
        mock_auth_tool.auth_credential = Mock()
        tool_info_auth = ToolInfo("auth_tool", mock_auth_tool, ToolType.MCP)
        tool_info_auth.has_auth = True
        registry._registered_tools["auth_tool"] = tool_info_auth
        
        # Mock tool without auth
        mock_no_auth_tool = Mock()
        tool_info_no_auth = ToolInfo("no_auth_tool", mock_no_auth_tool, ToolType.FUNCTION)
        tool_info_no_auth.has_auth = False
        registry._registered_tools["no_auth_tool"] = tool_info_no_auth
        
        auth_tools = registry.get_authenticated_tools()
        assert auth_tools == ["auth_tool"]

    def test_get_tool_usage_stats(self, registry):
        """Test getting tool usage statistics."""
        mock_tool = Mock()
        tool_info = ToolInfo("test_tool", mock_tool, ToolType.FUNCTION)
        tool_info.usage_count = 5
        tool_info.error_count = 1
        tool_info.last_used = 1234567890.0
        tool_info.registered_at = 1234567800.0
        registry._registered_tools["test_tool"] = tool_info
        
        stats = registry.get_tool_usage_stats("test_tool")
        
        assert stats is not None
        assert stats['usage_count'] == 5
        assert stats['error_count'] == 1
        assert stats['error_rate'] == 0.2  # 1/5
        assert stats['last_used'] == 1234567890.0
        assert stats['registered_at'] == 1234567800.0

    def test_get_tool_usage_stats_not_found(self, registry):
        """Test getting usage stats for non-existent tool."""
        stats = registry.get_tool_usage_stats("nonexistent_tool")
        assert stats is None


class TestToolInfo:
    """Test suite for ToolInfo class."""
    
    def test_tool_info_creation(self):
        """Test ToolInfo creation with string tool type."""
        mock_tool = Mock()
        tool_info = ToolInfo(
            name="test_tool",
            tool=mock_tool,
            tool_type="function",  # String type
            strategy_name="test_strategy",
            metadata={"key": "value"}
        )
        
        assert tool_info.name == "test_tool"
        assert tool_info.tool == mock_tool
        assert tool_info.tool_type == ToolType.FUNCTION  # Converted to enum
        assert tool_info.strategy_name == "test_strategy"
        assert tool_info.metadata == {"key": "value"}
        assert tool_info.health_status == ToolHealthStatus.INITIALIZING

    def test_tool_info_enum_tool_type(self):
        """Test ToolInfo creation with enum tool type."""
        mock_tool = Mock()
        tool_info = ToolInfo(
            name="test_tool",
            tool=mock_tool,
            tool_type=ToolType.MCP  # Enum type
        )
        
        assert tool_info.tool_type == ToolType.MCP

    def test_tool_info_invalid_tool_type(self):
        """Test ToolInfo creation with invalid tool type."""
        mock_tool = Mock()
        tool_info = ToolInfo(
            name="test_tool",
            tool=mock_tool,
            tool_type="invalid_type"
        )
        
        assert tool_info.tool_type == ToolType.UNKNOWN

    def test_tool_info_usage_tracking(self):
        """Test ToolInfo usage tracking."""
        mock_tool = Mock()
        tool_info = ToolInfo("test_tool", mock_tool, ToolType.FUNCTION)
        
        assert tool_info.usage_count == 0
        assert tool_info.error_count == 0
        assert tool_info.last_used is None
        
        # Mark as used
        tool_info.mark_used()
        assert tool_info.usage_count == 1
        assert tool_info.last_used is not None
        
        # Mark error
        tool_info.mark_error()
        assert tool_info.error_count == 1

    def test_tool_info_has_auth_detection(self):
        """Test ToolInfo authentication detection."""
        # Tool with auth - use spec to control what attributes exist
        mock_auth_tool = Mock(spec=['auth_credential'])
        mock_auth_tool.auth_credential = Mock()  # Set the auth credential
        tool_info_auth = ToolInfo("auth_tool", mock_auth_tool, ToolType.MCP)
        assert tool_info_auth.has_auth is True
        
        # Tool without auth - use spec with no auth attributes
        mock_no_auth_tool = Mock(spec=['name', 'description'])
        tool_info_no_auth = ToolInfo("no_auth_tool", mock_no_auth_tool, ToolType.FUNCTION)
        assert tool_info_no_auth.has_auth is False

    def test_tool_info_to_dict(self):
        """Test ToolInfo dictionary conversion."""
        mock_tool = Mock(spec=['name', 'description'])  # Tool without auth attributes
        tool_info = ToolInfo(
            name="test_tool",
            tool=mock_tool,
            tool_type=ToolType.FUNCTION,
            strategy_name="test_strategy",
            metadata={"key": "value"}
        )
        tool_info.usage_count = 5
        tool_info.error_count = 1
        
        result = tool_info.to_dict()
        
        assert result['name'] == "test_tool"
        assert result['tool_type'] == "function"
        assert result['strategy_name'] == "test_strategy"
        assert result['metadata'] == {"key": "value"}
        assert result['usage_count'] == 5
        assert result['error_count'] == 1
        assert result['health_status'] == "initializing"
        assert result['has_auth'] is False


# Parameterized tests for all tool types
@pytest.mark.parametrize("tool_type,expected_enum", [
    ("function", ToolType.FUNCTION),
    ("mcp", ToolType.MCP),
    ("openapi", ToolType.OPENAPI),
    ("agent", ToolType.AGENT),
    ("google", ToolType.GOOGLE),
    ("google_api", ToolType.GOOGLE_API),
    ("toolset", ToolType.TOOLSET),
    ("unknown", ToolType.UNKNOWN),
    ("invalid", ToolType.UNKNOWN),
])
def test_tool_type_string_conversion(tool_type, expected_enum):
    """Test tool type string to enum conversion."""
    mock_tool = Mock()
    tool_info = ToolInfo("test_tool", mock_tool, tool_type)
    assert tool_info.tool_type == expected_enum


if __name__ == "__main__":
    pytest.main([__file__])