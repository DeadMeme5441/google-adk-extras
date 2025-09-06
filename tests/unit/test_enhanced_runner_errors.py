"""Unit tests for enhanced runner error handling."""

import pytest
from pathlib import Path
from unittest.mock import Mock

from google_adk_extras.runners.errors import (
    ConfigurationError,
    RegistryError,
    ToolExecutionError,
    YamlSystemContext,
    YamlSystemError,
)


class TestYamlSystemContext:
    """Test cases for YamlSystemContext."""
    
    def test_basic_initialization(self):
        """Test basic YamlSystemContext initialization."""
        context = YamlSystemContext(
            system_name="test-system",
            config_path="/path/to/config.yaml"
        )
        
        assert context.system_name == "test-system"
        assert context.config_path == "/path/to/config.yaml"
        assert context.current_agent is None
        assert context.current_tool is None
        assert context.invocation_id is None
        assert context.session_id is None
        assert context.user_id is None
        assert context.additional_context == {}
    
    def test_full_initialization(self):
        """Test YamlSystemContext with all fields."""
        additional_context = {"key": "value"}
        context = YamlSystemContext(
            system_name="full-system",
            config_path=Path("/full/path/config.yaml"),
            current_agent="test_agent",
            current_tool="test_tool",
            invocation_id="inv_123",
            session_id="sess_456",
            user_id="user_789",
            additional_context=additional_context
        )
        
        assert context.system_name == "full-system"
        assert context.config_path == Path("/full/path/config.yaml")
        assert context.current_agent == "test_agent"
        assert context.current_tool == "test_tool"
        assert context.invocation_id == "inv_123"
        assert context.session_id == "sess_456"
        assert context.user_id == "user_789"
        assert context.additional_context == additional_context
    
    def test_with_agent(self):
        """Test creating context with different agent."""
        original = YamlSystemContext(
            system_name="test-system",
            current_agent="original_agent",
            current_tool="some_tool"
        )
        
        new_context = original.with_agent("new_agent")
        
        # Should have new agent and reset tool
        assert new_context.current_agent == "new_agent"
        assert new_context.current_tool is None
        
        # Should preserve other fields
        assert new_context.system_name == "test-system"
        
        # Should be different object
        assert new_context is not original
        assert original.current_agent == "original_agent"
    
    def test_with_tool(self):
        """Test creating context with different tool."""
        original = YamlSystemContext(
            system_name="test-system",
            current_agent="test_agent",
            current_tool="original_tool"
        )
        
        new_context = original.with_tool("new_tool")
        
        # Should have new tool and preserve agent
        assert new_context.current_tool == "new_tool"
        assert new_context.current_agent == "test_agent"
        
        # Should preserve other fields
        assert new_context.system_name == "test-system"
        
        # Should be different object
        assert new_context is not original
        assert original.current_tool == "original_tool"
    
    def test_with_invocation(self):
        """Test creating context with invocation details."""
        original = YamlSystemContext(system_name="test-system")
        
        new_context = original.with_invocation("inv_123", "sess_456", "user_789")
        
        assert new_context.invocation_id == "inv_123"
        assert new_context.session_id == "sess_456"
        assert new_context.user_id == "user_789"
        
        # Should preserve other fields
        assert new_context.system_name == "test-system"
        
        # Should be different object
        assert new_context is not original
        assert original.invocation_id is None
    
    def test_add_context(self):
        """Test adding additional context."""
        original = YamlSystemContext(
            system_name="test-system",
            additional_context={"existing": "value"}
        )
        
        new_context = original.add_context("new_key", "new_value")
        
        expected_context = {"existing": "value", "new_key": "new_value"}
        assert new_context.additional_context == expected_context
        
        # Should be different object
        assert new_context is not original
        assert original.additional_context == {"existing": "value"}
    
    def test_get_location_string_system_only(self):
        """Test location string with system name only."""
        context = YamlSystemContext(system_name="test-system")
        assert context.get_location_string() == "test-system"
    
    def test_get_location_string_with_agent(self):
        """Test location string with agent."""
        context = YamlSystemContext(
            system_name="test-system",
            current_agent="test_agent"
        )
        assert context.get_location_string() == "test-system -> agent:test_agent"
    
    def test_get_location_string_full(self):
        """Test location string with agent and tool."""
        context = YamlSystemContext(
            system_name="test-system",
            current_agent="test_agent",
            current_tool="test_tool"
        )
        expected = "test-system -> agent:test_agent -> tool:test_tool"
        assert context.get_location_string() == expected
    
    def test_get_location_string_tool_without_agent(self):
        """Test location string with tool but no agent."""
        context = YamlSystemContext(
            system_name="test-system",
            current_tool="test_tool"
        )
        assert context.get_location_string() == "test-system -> tool:test_tool"


class TestYamlSystemError:
    """Test cases for YamlSystemError."""
    
    def test_basic_error(self):
        """Test basic YamlSystemError creation."""
        context = YamlSystemContext(system_name="test-system")
        error = YamlSystemError("Test error", context)
        
        assert "[test-system] Test error" in str(error)
        assert error.context is context
        assert error.original_error is None
        assert error.error_code is None
        assert error.suggested_fixes == []
    
    def test_error_with_original(self):
        """Test YamlSystemError with original exception."""
        context = YamlSystemContext(system_name="test-system")
        original = ValueError("Original error")
        error = YamlSystemError("Wrapped error", context, original_error=original)
        
        error_str = str(error)
        assert "[test-system] Wrapped error" in error_str
        assert "Caused by: ValueError: Original error" in error_str
        assert error.original_error is original
    
    def test_error_with_code_and_fixes(self):
        """Test YamlSystemError with error code and suggested fixes."""
        context = YamlSystemContext(
            system_name="test-system",
            current_agent="test_agent"
        )
        fixes = ["Fix 1", "Fix 2"]
        error = YamlSystemError(
            "Test error",
            context,
            error_code="ERR_001",
            suggested_fixes=fixes
        )
        
        error_str = str(error)
        assert "[test-system -> agent:test_agent] Test error" in error_str
        assert "Error Code: ERR_001" in error_str
        assert "Suggested fixes:" in error_str
        assert "1. Fix 1" in error_str
        assert "2. Fix 2" in error_str
        
        assert error.error_code == "ERR_001"
        assert error.suggested_fixes == fixes
    
    def test_get_debug_info_basic(self):
        """Test getting debug info from basic error."""
        context = YamlSystemContext(
            system_name="test-system",
            config_path="/path/to/config.yaml",
            current_agent="test_agent"
        )
        error = YamlSystemError("Test error", context, error_code="ERR_001")
        
        debug_info = error.get_debug_info()
        
        assert debug_info['error_type'] == 'YamlSystemError'
        assert 'Test error' in debug_info['message']
        assert debug_info['context']['system_name'] == 'test-system'
        assert debug_info['context']['config_path'] == '/path/to/config.yaml'
        assert debug_info['context']['current_agent'] == 'test_agent'
        assert debug_info['error_code'] == 'ERR_001'
        assert 'original_error' not in debug_info
    
    def test_get_debug_info_with_original(self):
        """Test getting debug info with original exception."""
        context = YamlSystemContext(system_name="test-system")
        original = ValueError("Original error")
        error = YamlSystemError("Wrapped error", context, original_error=original)
        
        debug_info = error.get_debug_info()
        
        assert 'original_error' in debug_info
        original_info = debug_info['original_error']
        assert original_info['type'] == 'ValueError'
        assert original_info['message'] == 'Original error'
        assert 'traceback' in original_info
        assert isinstance(original_info['traceback'], list)


class TestToolExecutionError:
    """Test cases for ToolExecutionError."""
    
    def test_basic_tool_error(self):
        """Test basic ToolExecutionError creation."""
        context = YamlSystemContext(
            system_name="test-system",
            current_tool="test_tool"
        )
        error = ToolExecutionError("Tool failed", context)
        
        error_str = str(error)
        assert "[test-system -> tool:test_tool] Tool failed" in error_str
        assert error.tool_type is None
        assert error.execution_time is None
        assert error.timeout is None
    
    def test_tool_error_with_type(self):
        """Test ToolExecutionError with tool type."""
        context = YamlSystemContext(system_name="test-system")
        error = ToolExecutionError(
            "Tool failed", 
            context, 
            tool_type="mcp"
        )
        
        error_str = str(error)
        assert "Tool failed (tool_type: mcp)" in error_str
        assert error.tool_type == "mcp"
    
    def test_tool_error_with_timing(self):
        """Test ToolExecutionError with execution timing."""
        context = YamlSystemContext(system_name="test-system")
        error = ToolExecutionError(
            "Tool timed out",
            context,
            tool_type="openapi",
            execution_time=30.5,
            timeout=30.0
        )
        
        error_str = str(error)
        assert "Tool timed out (tool_type: openapi)" in error_str
        assert "(executed for 30.5s, timeout: 30.0s)" in error_str
        assert error.execution_time == 30.5
        assert error.timeout == 30.0
    
    def test_tool_error_inheritance(self):
        """Test that ToolExecutionError inherits from YamlSystemError."""
        context = YamlSystemContext(system_name="test-system")
        error = ToolExecutionError("Tool failed", context)
        
        assert isinstance(error, YamlSystemError)
        assert isinstance(error, ToolExecutionError)


class TestConfigurationError:
    """Test cases for ConfigurationError."""
    
    def test_basic_config_error(self):
        """Test basic ConfigurationError creation."""
        context = YamlSystemContext(system_name="test-system")
        error = ConfigurationError("Invalid config", context)
        
        error_str = str(error)
        assert "[test-system] Invalid config" in error_str
        assert error.config_path is None
        assert error.config_section is None
    
    def test_config_error_with_section(self):
        """Test ConfigurationError with config section."""
        context = YamlSystemContext(system_name="test-system")
        error = ConfigurationError(
            "Missing field",
            context,
            config_section="agents[0].model"
        )
        
        error_str = str(error)
        assert "Missing field (section: agents[0].model)" in error_str
        assert error.config_section == "agents[0].model"
    
    def test_config_error_with_path(self):
        """Test ConfigurationError with config path."""
        context = YamlSystemContext(system_name="test-system")
        config_path = "/path/to/config.yaml"
        error = ConfigurationError(
            "Invalid syntax",
            context,
            config_path=config_path,
            config_section="runtime"
        )
        
        error_str = str(error)
        assert "Invalid syntax (section: runtime)" in error_str
        assert "(file: /path/to/config.yaml)" in error_str
        assert error.config_path == Path(config_path)
    
    def test_config_error_inheritance(self):
        """Test that ConfigurationError inherits from YamlSystemError."""
        context = YamlSystemContext(system_name="test-system")
        error = ConfigurationError("Config error", context)
        
        assert isinstance(error, YamlSystemError)
        assert isinstance(error, ConfigurationError)


class TestRegistryError:
    """Test cases for RegistryError."""
    
    def test_basic_registry_error(self):
        """Test basic RegistryError creation."""
        context = YamlSystemContext(system_name="test-system")
        error = RegistryError("Registry error", context)
        
        error_str = str(error)
        assert "[test-system] Registry error" in error_str
        assert error.registry_type is None
        assert error.missing_item is None
    
    def test_registry_error_with_missing_item(self):
        """Test RegistryError with missing item details."""
        context = YamlSystemContext(system_name="test-system")
        error = RegistryError(
            "Agent not found",
            context,
            registry_type="agent",
            missing_item="missing_agent"
        )
        
        error_str = str(error)
        assert "Agent not found (agent registry: missing_agent)" in error_str
        assert error.registry_type == "agent"
        assert error.missing_item == "missing_agent"
    
    def test_registry_error_inheritance(self):
        """Test that RegistryError inherits from YamlSystemError."""
        context = YamlSystemContext(system_name="test-system")
        error = RegistryError("Registry error", context)
        
        assert isinstance(error, YamlSystemError)
        assert isinstance(error, RegistryError)


class TestErrorIntegration:
    """Integration tests for error handling system."""
    
    def test_nested_error_context(self):
        """Test error with nested context changes."""
        base_context = YamlSystemContext(
            system_name="integration-system",
            config_path="/path/to/config.yaml"
        )
        
        agent_context = base_context.with_agent("processor_agent")
        tool_context = agent_context.with_tool("extract_data")
        invocation_context = tool_context.with_invocation("inv_123", "sess_456", "user_789")
        
        # Create error with full context
        original_error = ConnectionError("Connection failed")
        error = ToolExecutionError(
            "Tool execution failed due to connection issue",
            invocation_context,
            original_error=original_error,
            tool_type="mcp",
            execution_time=25.0,
            timeout=30.0,
            suggested_fixes=[
                "Check MCP server connectivity",
                "Verify network configuration",
                "Retry with exponential backoff"
            ]
        )
        
        # Verify comprehensive error message
        error_str = str(error)
        expected_location = "integration-system -> agent:processor_agent -> tool:extract_data"
        assert expected_location in error_str
        assert "Tool execution failed due to connection issue" in error_str
        assert "(tool_type: mcp)" in error_str
        assert "(executed for 25.0s, timeout: 30.0s)" in error_str
        assert "Caused by: ConnectionError: Connection failed" in error_str
        assert "Check MCP server connectivity" in error_str
        
        # Verify debug info
        debug_info = error.get_debug_info()
        assert debug_info['context']['invocation_id'] == 'inv_123'
        assert debug_info['context']['session_id'] == 'sess_456'
        assert debug_info['context']['user_id'] == 'user_789'
        assert debug_info['original_error']['type'] == 'ConnectionError'
    
    def test_error_chain_preservation(self):
        """Test that error chains are preserved properly."""
        context = YamlSystemContext(system_name="chain-test")
        
        # Create chain: ValueError -> ConfigurationError -> YamlSystemError
        original = ValueError("Invalid value")
        config_error = ConfigurationError(
            "Configuration validation failed",
            context,
            original_error=original,
            config_section="runtime.model"
        )
        
        final_error = YamlSystemError(
            "System initialization failed",
            context,
            original_error=config_error,
            suggested_fixes=["Review configuration file"]
        )
        
        # Verify the chain is preserved
        assert final_error.original_error is config_error
        assert config_error.original_error is original
        
        # Verify debug info captures the chain
        debug_info = final_error.get_debug_info()
        assert debug_info['original_error']['type'] == 'ConfigurationError'