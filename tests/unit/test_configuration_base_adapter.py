"""Unit tests for Enhanced Configuration Base Adapter."""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch

import pytest

from google_adk_extras.configuration.base_adapter import (
    EnhancedConfigAdapter,
    ConfigSourceType,
    ConfigurationContext,
    AdapterResult,
    ValidationIssue,
    ValidationSeverity,
    ConfigurationError,
    register_adapter,
    get_adapter,
    list_adapters,
    _adapter_registry
)


class MockConfig:
    """Mock configuration class for testing."""
    
    def __init__(self, value: str = "test"):
        self.value = value
    
    def model_validate(self, data):
        """Mock Pydantic validation."""
        if data.get('value') == 'invalid':
            raise ValueError("Invalid value")
    
    def model_dump(self):
        """Mock Pydantic model dump."""
        return {'value': self.value}


class MockConfigAdapter(EnhancedConfigAdapter):
    """Test implementation of EnhancedConfigAdapter."""
    
    def get_supported_source_types(self) -> List[ConfigSourceType]:
        return [ConfigSourceType.DICT, ConfigSourceType.YAML_FILE]
    
    def can_handle_source(self, source: Any, context=None) -> bool:
        return isinstance(source, dict) or str(source).endswith('.test')
    
    def _load_raw_config(self, source: Any, context: ConfigurationContext) -> Dict[str, Any]:
        if isinstance(source, dict):
            return source.copy()
        elif str(source).endswith('.test'):
            return {'value': 'from_test_file'}
        else:
            raise ConfigurationError(f"Cannot load from {source}")
    
    def _create_target_config(
        self,
        raw_config: Dict[str, Any],
        context: ConfigurationContext,
        validation_issues: List[ValidationIssue]
    ) -> MockConfig:
        if 'error' in raw_config:
            validation_issues.append(ValidationIssue(
                path="test",
                severity=ValidationSeverity.ERROR,
                message="Test error",
                suggestion="Remove error key"
            ))
            raise ConfigurationError("Test error")
        
        return MockConfig(raw_config.get('value', 'default'))


@pytest.fixture(autouse=True)
def clear_adapter_registry():
    """Clear adapter registry before each test."""
    global _adapter_registry
    _adapter_registry.clear()
    yield
    _adapter_registry.clear()


@pytest.fixture
def test_adapter():
    """Create test adapter instance."""
    return MockConfigAdapter(
        target_type=MockConfig,
        enable_interpolation=True,
        enable_validation=True
    )


@pytest.fixture
def test_context():
    """Create test configuration context."""
    return ConfigurationContext(
        source_type=ConfigSourceType.DICT,
        interpolation_enabled=True,
        validation_enabled=True
    )


class TestEnhancedConfigAdapter:
    """Test cases for EnhancedConfigAdapter base class."""
    
    def test_adapter_initialization(self):
        """Test adapter initialization."""
        adapter = MockConfigAdapter(
            target_type=MockConfig,
            enable_interpolation=False,
            enable_validation=True,
            strict_mode=True
        )
        
        assert adapter.target_type == MockConfig
        assert adapter.enable_interpolation == False
        assert adapter.enable_validation == True
        assert adapter.strict_mode == True
        assert isinstance(adapter._interpolation_cache, dict)
    
    def test_supported_source_types(self, test_adapter):
        """Test getting supported source types."""
        types = test_adapter.get_supported_source_types()
        assert ConfigSourceType.DICT in types
        assert ConfigSourceType.YAML_FILE in types
    
    def test_can_handle_source(self, test_adapter):
        """Test source handling detection."""
        assert test_adapter.can_handle_source({'key': 'value'}) == True
        assert test_adapter.can_handle_source('config.test') == True
        assert test_adapter.can_handle_source('config.yaml') == False
        assert test_adapter.can_handle_source(123) == False
    
    def test_detect_source_type(self, test_adapter):
        """Test source type detection."""
        assert test_adapter._detect_source_type({'key': 'value'}) == ConfigSourceType.DICT
        assert test_adapter._detect_source_type('file.yaml') == ConfigSourceType.YAML_FILE
        assert test_adapter._detect_source_type('file.json') == ConfigSourceType.JSON_FILE
        assert test_adapter._detect_source_type('file.toml') == ConfigSourceType.TOML_FILE
        assert test_adapter._detect_source_type('https://example.com/config') == ConfigSourceType.REMOTE_URL
        assert test_adapter._detect_source_type('other') == ConfigSourceType.CUSTOM
    
    def test_successful_adaptation(self, test_adapter):
        """Test successful configuration adaptation."""
        source = {'value': 'test_value'}
        result = test_adapter.adapt(source)
        
        assert isinstance(result, AdapterResult)
        assert isinstance(result.config, MockConfig)
        assert result.config.value == 'test_value'
        assert len(result.validation_issues) == 0
        assert result.has_errors() == False
        assert result.processing_time > 0
    
    def test_adaptation_with_context(self, test_adapter, test_context):
        """Test adaptation with provided context."""
        source = {'value': 'context_test'}
        result = test_adapter.adapt(source, test_context)
        
        assert result.context == test_context
        assert result.config.value == 'context_test'
    
    @patch('google_adk_extras.configuration.interpolation.EnvironmentInterpolator')
    def test_interpolation_enabled(self, mock_interpolator_class, test_adapter):
        """Test environment variable interpolation."""
        mock_interpolator = Mock()
        mock_interpolator.interpolate.return_value = {'value': 'interpolated'}
        mock_interpolator_class.return_value = mock_interpolator
        
        source = {'value': '${TEST_VAR:-default}'}
        result = test_adapter.adapt(source)
        
        mock_interpolator.interpolate.assert_called_once()
        assert result.config.value == 'interpolated'
    
    def test_interpolation_disabled(self, test_adapter):
        """Test with interpolation disabled."""
        test_adapter.enable_interpolation = False
        
        source = {'value': '${TEST_VAR:-default}'}
        result = test_adapter.adapt(source)
        
        # Should not interpolate
        assert result.config.value == '${TEST_VAR:-default}'
    
    def test_validation_enabled(self, test_adapter):
        """Test with validation enabled."""
        source = {'value': 'invalid'}
        test_adapter.enable_validation = True
        
        result = test_adapter.adapt(source)
        
        # Should have validation issues
        assert len(result.validation_issues) > 0
    
    def test_validation_disabled(self, test_adapter):
        """Test with validation disabled."""
        source = {'value': 'invalid'}
        test_adapter.enable_validation = False
        
        result = test_adapter.adapt(source)
        
        # Should not validate beyond creation errors
        assert result.config.value == 'invalid'
    
    def test_strict_mode_error_handling(self, test_adapter):
        """Test strict mode error handling."""
        test_adapter.strict_mode = True
        source = {'error': True}
        
        with pytest.raises(ConfigurationError):
            test_adapter.adapt(source)
    
    def test_non_strict_mode_error_handling(self, test_adapter):
        """Test non-strict mode error handling."""
        test_adapter.strict_mode = False
        source = {'error': True}
        
        result = test_adapter.adapt(source)
        
        assert result.config is None
        assert result.has_errors() == True
        assert any(issue.severity == ValidationSeverity.ERROR 
                  for issue in result.validation_issues)
    
    def test_interpolation_cache_management(self, test_adapter):
        """Test interpolation cache management."""
        # Add something to cache
        test_adapter._interpolation_cache['test'] = 'value'
        assert len(test_adapter._interpolation_cache) == 1
        
        # Clear cache
        test_adapter.clear_interpolation_cache()
        assert len(test_adapter._interpolation_cache) == 0


class TestAdapterResult:
    """Test cases for AdapterResult class."""
    
    def test_result_creation(self):
        """Test adapter result creation."""
        config = MockConfig("test")
        context = ConfigurationContext(source_type=ConfigSourceType.DICT)
        issues = [ValidationIssue(
            path="test",
            severity=ValidationSeverity.WARNING,
            message="Test warning"
        )]
        
        result = AdapterResult(
            config=config,
            validation_issues=issues,
            context=context,
            processing_time=0.1,
            metadata={'key': 'value'}
        )
        
        assert result.config == config
        assert result.context == context
        assert len(result.validation_issues) == 1
        assert result.processing_time == 0.1
        assert result.metadata['key'] == 'value'
    
    def test_has_errors(self):
        """Test error detection."""
        result = AdapterResult(config=None)
        
        # No issues
        assert result.has_errors() == False
        
        # Warning only
        result.validation_issues.append(ValidationIssue(
            path="test", severity=ValidationSeverity.WARNING, message="Warning"
        ))
        assert result.has_errors() == False
        
        # With error
        result.validation_issues.append(ValidationIssue(
            path="test", severity=ValidationSeverity.ERROR, message="Error"
        ))
        assert result.has_errors() == True
    
    def test_has_warnings(self):
        """Test warning detection."""
        result = AdapterResult(config=None)
        
        # No issues
        assert result.has_warnings() == False
        
        # Error only
        result.validation_issues.append(ValidationIssue(
            path="test", severity=ValidationSeverity.ERROR, message="Error"
        ))
        assert result.has_warnings() == False
        
        # With warning
        result.validation_issues.append(ValidationIssue(
            path="test", severity=ValidationSeverity.WARNING, message="Warning"
        ))
        assert result.has_warnings() == True
    
    def test_get_issues_by_severity(self):
        """Test filtering issues by severity."""
        result = AdapterResult(config=None)
        result.validation_issues = [
            ValidationIssue(path="1", severity=ValidationSeverity.ERROR, message="Error 1"),
            ValidationIssue(path="2", severity=ValidationSeverity.WARNING, message="Warning 1"),
            ValidationIssue(path="3", severity=ValidationSeverity.ERROR, message="Error 2"),
            ValidationIssue(path="4", severity=ValidationSeverity.INFO, message="Info 1"),
        ]
        
        errors = result.get_issues_by_severity(ValidationSeverity.ERROR)
        assert len(errors) == 2
        assert all(issue.severity == ValidationSeverity.ERROR for issue in errors)
        
        warnings = result.get_issues_by_severity(ValidationSeverity.WARNING)
        assert len(warnings) == 1
        
        infos = result.get_issues_by_severity(ValidationSeverity.INFO)
        assert len(infos) == 1


class TestValidationIssue:
    """Test cases for ValidationIssue class."""
    
    def test_issue_creation(self):
        """Test validation issue creation."""
        issue = ValidationIssue(
            path="config.database.host",
            severity=ValidationSeverity.ERROR,
            message="Database host is required",
            suggestion="Set database host in configuration",
            source_location="config.yaml:15"
        )
        
        assert issue.path == "config.database.host"
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.message == "Database host is required"
        assert issue.suggestion == "Set database host in configuration"
        assert issue.source_location == "config.yaml:15"
    
    def test_minimal_issue_creation(self):
        """Test minimal validation issue creation."""
        issue = ValidationIssue(
            path="test",
            severity=ValidationSeverity.WARNING,
            message="Test message"
        )
        
        assert issue.path == "test"
        assert issue.severity == ValidationSeverity.WARNING
        assert issue.message == "Test message"
        assert issue.suggestion is None
        assert issue.source_location is None


class TestConfigurationContext:
    """Test cases for ConfigurationContext class."""
    
    def test_context_creation(self):
        """Test configuration context creation."""
        context = ConfigurationContext(
            source_type=ConfigSourceType.YAML_FILE,
            source_path="/path/to/config.yaml",
            environment="production",
            interpolation_enabled=True,
            validation_enabled=True,
            strict_mode=False,
            metadata={'custom': 'value'}
        )
        
        assert context.source_type == ConfigSourceType.YAML_FILE
        assert context.source_path == "/path/to/config.yaml"
        assert context.environment == "production"
        assert context.interpolation_enabled == True
        assert context.validation_enabled == True
        assert context.strict_mode == False
        assert context.metadata['custom'] == 'value'
    
    def test_default_context(self):
        """Test default configuration context."""
        context = ConfigurationContext(source_type=ConfigSourceType.DICT)
        
        assert context.source_type == ConfigSourceType.DICT
        assert context.source_path is None
        assert context.environment is None
        assert context.interpolation_enabled == True
        assert context.validation_enabled == True
        assert context.strict_mode == False
        assert context.metadata == {}


class TestAdapterRegistry:
    """Test cases for adapter registry functions."""
    
    def test_register_adapter(self):
        """Test registering an adapter."""
        register_adapter("test", MockConfigAdapter)
        
        assert get_adapter("test") == MockConfigAdapter
        assert "test" in list_adapters()
    
    def test_get_nonexistent_adapter(self):
        """Test getting non-existent adapter."""
        assert get_adapter("nonexistent") is None
    
    def test_list_empty_adapters(self):
        """Test listing adapters when registry is empty."""
        assert list_adapters() == []
    
    def test_list_multiple_adapters(self):
        """Test listing multiple registered adapters."""
        register_adapter("adapter1", MockConfigAdapter)
        register_adapter("adapter2", MockConfigAdapter)
        
        adapters = list_adapters()
        assert len(adapters) == 2
        assert "adapter1" in adapters
        assert "adapter2" in adapters


class TestConfigurationError:
    """Test cases for ConfigurationError exception."""
    
    def test_basic_error(self):
        """Test basic configuration error."""
        error = ConfigurationError("Test error")
        
        assert str(error) == "Test error"
        assert error.validation_issues == []
    
    def test_error_with_validation_issues(self):
        """Test configuration error with validation issues."""
        issues = [
            ValidationIssue(path="test", severity=ValidationSeverity.ERROR, message="Error 1"),
            ValidationIssue(path="test", severity=ValidationSeverity.WARNING, message="Warning 1")
        ]
        
        error = ConfigurationError("Test error", validation_issues=issues)
        
        assert str(error) == "Test error"
        assert len(error.validation_issues) == 2
        assert error.validation_issues[0].message == "Error 1"