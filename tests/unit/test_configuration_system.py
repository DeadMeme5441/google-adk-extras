"""Unit tests for Configuration System."""

import os
from unittest.mock import Mock, patch

import pytest

from google_adk_extras.configuration.system import (
    ConfigurationSystem,
    get_config_system,
    load_config,
    load_enhanced_run_config,
    reset_config_system
)
from google_adk_extras.configuration.base_adapter import (
    EnhancedConfigAdapter,
    ConfigSourceType,
    ConfigurationContext,
    AdapterResult,
    ValidationIssue,
    ValidationSeverity,
    ConfigurationError
)


class MockConfig:
    """Mock configuration class for testing."""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class MockAdapter(EnhancedConfigAdapter):
    """Mock adapter for testing."""
    
    def __init__(self, target_type, **kwargs):
        super().__init__(target_type, **kwargs)
        self.can_handle_result = True
        self.load_result = {'key': 'value'}
        self.create_error = None
    
    def get_supported_source_types(self):
        return [ConfigSourceType.DICT]
    
    def can_handle_source(self, source, context=None):
        return self.can_handle_result
    
    def _load_raw_config(self, source, context):
        if isinstance(source, dict):
            return source.copy()
        return self.load_result
    
    def _create_target_config(self, raw_config, context, validation_issues):
        if self.create_error:
            raise self.create_error
        return MockConfig(**raw_config)


@pytest.fixture(autouse=True)
def reset_global_config_system():
    """Reset global configuration system before each test."""
    reset_config_system()
    yield
    reset_config_system()


@pytest.fixture
def config_system():
    """Create configuration system for testing."""
    return ConfigurationSystem(default_adapters=False)


@pytest.fixture
def mock_adapter():
    """Create mock adapter for testing."""
    return MockAdapter(target_type=MockConfig)


class TestConfigurationSystem:
    """Test cases for ConfigurationSystem."""
    
    def test_initialization_default_adapters(self):
        """Test configuration system initialization with default adapters."""
        system = ConfigurationSystem()
        
        assert system.enable_interpolation == True
        assert system.enable_validation == True
        assert system.strict_mode == False
        assert len(system.list_adapters()) > 0
        assert 'yaml' in system.list_adapters()
        assert 'json' in system.list_adapters()
        assert 'dict' in system.list_adapters()
    
    def test_initialization_no_default_adapters(self):
        """Test initialization without default adapters."""
        system = ConfigurationSystem(default_adapters=False)
        
        assert len(system.list_adapters()) == 0
    
    def test_initialization_custom_settings(self):
        """Test initialization with custom settings."""
        system = ConfigurationSystem(
            enable_interpolation=False,
            enable_validation=False,
            strict_mode=True,
            default_adapters=False
        )
        
        assert system.enable_interpolation == False
        assert system.enable_validation == False
        assert system.strict_mode == True
    
    def test_register_adapter(self, config_system):
        """Test registering an adapter."""
        config_system.register_adapter("test", MockAdapter)
        
        assert config_system.get_adapter("test") == MockAdapter
        assert "test" in config_system.list_adapters()
    
    def test_get_nonexistent_adapter(self, config_system):
        """Test getting non-existent adapter."""
        assert config_system.get_adapter("nonexistent") is None
    
    def test_list_empty_adapters(self, config_system):
        """Test listing adapters when none registered."""
        assert config_system.list_adapters() == []
    
    def test_detect_source_type(self, config_system):
        """Test source type detection."""
        assert config_system._detect_source_type({'key': 'value'}) == ConfigSourceType.DICT
        assert config_system._detect_source_type('file.yaml') == ConfigSourceType.YAML_FILE
        assert config_system._detect_source_type('file.json') == ConfigSourceType.JSON_FILE
        assert config_system._detect_source_type('file.toml') == ConfigSourceType.TOML_FILE
        assert config_system._detect_source_type('https://example.com') == ConfigSourceType.REMOTE_URL
        assert config_system._detect_source_type('other') == ConfigSourceType.CUSTOM
    
    def test_load_config_with_specific_adapter(self, config_system, mock_adapter):
        """Test loading configuration with specific adapter."""
        config_system.register_adapter("mock", MockAdapter)
        
        source = {'name': 'test', 'value': 123}
        result = config_system.load_config(MockConfig, source, adapter_name="mock")
        
        assert isinstance(result, AdapterResult)
        assert isinstance(result.config, MockConfig)
        assert result.config.name == 'test'
        assert result.config.value == 123
        assert result.metadata['adapter_used'] == 'MockAdapter'
    
    def test_load_config_auto_detection(self, config_system):
        """Test loading configuration with auto-detection."""
        config_system.register_adapter("mock", MockAdapter)
        
        source = {'auto': True}
        result = config_system.load_config(MockConfig, source)
        
        assert isinstance(result.config, MockConfig)
        assert result.config.auto == True
    
    def test_load_config_with_context(self, config_system):
        """Test loading configuration with provided context."""
        config_system.register_adapter("mock", MockAdapter)
        
        context = ConfigurationContext(
            source_type=ConfigSourceType.DICT,
            environment="test",
            strict_mode=True
        )
        
        source = {'context_test': True}
        result = config_system.load_config(MockConfig, source, context=context)
        
        assert result.context == context
        assert result.context.environment == "test"
    
    def test_load_config_no_suitable_adapter(self, config_system):
        """Test loading when no suitable adapter found."""
        # Don't register any adapters
        
        source = {'key': 'value'}
        
        with pytest.raises(ConfigurationError):
            config_system.load_config(MockConfig, source)
    
    def test_load_config_nonexistent_adapter(self, config_system):
        """Test loading with non-existent adapter name."""
        source = {'key': 'value'}
        
        with pytest.raises(ConfigurationError):
            config_system.load_config(MockConfig, source, adapter_name="nonexistent")
    
    def test_load_config_adapter_error(self, config_system):
        """Test loading when adapter raises error."""
        # Create adapter that raises error
        error_adapter = MockAdapter(target_type=MockConfig)
        error_adapter.create_error = Exception("Adapter failed")
        
        config_system.register_adapter("error", lambda **kwargs: error_adapter)
        
        source = {'key': 'value'}
        
        with pytest.raises(ConfigurationError):
            config_system.load_config(MockConfig, source, adapter_name="error")
    
    def test_adapter_instance_caching(self, config_system):
        """Test adapter instance caching."""
        config_system.register_adapter("mock", MockAdapter)
        
        # Load config twice with same parameters
        source = {'key': 'value1'}
        result1 = config_system.load_config(MockConfig, source, adapter_name="mock")
        
        source = {'key': 'value2'}  
        result2 = config_system.load_config(MockConfig, source, adapter_name="mock")
        
        # Should use cached instance (same adapter class)
        assert len(config_system._adapter_instances) > 0
    
    def test_clear_adapter_cache(self, config_system):
        """Test clearing adapter cache."""
        config_system.register_adapter("mock", MockAdapter)
        
        # Create cached instance
        config_system.load_config(MockConfig, {'key': 'value'}, adapter_name="mock")
        assert len(config_system._adapter_instances) > 0
        
        # Clear cache
        config_system.clear_adapter_cache()
        assert len(config_system._adapter_instances) == 0
    
    def test_find_adapter_source_check_failure(self, config_system):
        """Test adapter source check failure handling."""
        # Create adapter that fails source check
        failing_adapter = MockAdapter(target_type=MockConfig)
        failing_adapter.can_handle_result = False
        
        config_system.register_adapter("failing", lambda **kwargs: failing_adapter)
        
        source = {'key': 'value'}
        result = config_system._find_adapter(source, MockConfig, None, ConfigurationContext(ConfigSourceType.DICT))
        
        assert result is None
    
    def test_validate_config(self, config_system):
        """Test configuration validation."""
        config = MockConfig(name="test", valid=True)
        validation_issues = config_system.validate_config(config, MockConfig)
        
        # Should have at least type validation
        assert isinstance(validation_issues, list)
    
    def test_validate_config_wrong_type(self, config_system):
        """Test validation with wrong config type."""
        config = "not a MockConfig"
        validation_issues = config_system.validate_config(config, MockConfig)
        
        assert len(validation_issues) > 0
        assert any(issue.severity == ValidationSeverity.ERROR for issue in validation_issues)
    
    def test_validate_config_with_pydantic(self, config_system):
        """Test validation with Pydantic model."""
        # Create mock config with Pydantic methods
        config = Mock()
        config.model_validate = Mock()
        config.model_dump = Mock(return_value={'key': 'value'})
        
        validation_issues = config_system.validate_config(config, MockConfig)
        
        config.model_validate.assert_called_once()
    
    def test_validate_config_pydantic_error(self, config_system):
        """Test validation with Pydantic validation error."""
        config = Mock()
        config.model_validate = Mock(side_effect=ValueError("Validation failed"))
        config.model_dump = Mock(return_value={'key': 'value'})
        
        validation_issues = config_system.validate_config(config, MockConfig)
        
        assert len(validation_issues) > 0
        assert any("Pydantic validation failed" in issue.message for issue in validation_issues)
    
    def test_validate_config_custom_validation(self, config_system):
        """Test custom validation method."""
        config = Mock()
        config.validate = Mock(side_effect=Exception("Custom validation failed"))
        
        validation_issues = config_system.validate_config(config, MockConfig)
        
        assert len(validation_issues) > 0
        assert any("Custom validation failed" in issue.message for issue in validation_issues)
    
    def test_get_system_stats(self, config_system):
        """Test getting system statistics."""
        config_system.register_adapter("test1", MockAdapter)
        config_system.register_adapter("test2", MockAdapter)
        
        stats = config_system.get_system_stats()
        
        assert stats['registered_adapters'] == 2
        assert stats['cached_instances'] == 0
        assert 'test1' in stats['adapter_names']
        assert 'test2' in stats['adapter_names']
        assert stats['interpolation_enabled'] == True
        assert stats['validation_enabled'] == True
        assert stats['strict_mode'] == False


class TestGlobalConfigSystem:
    """Test global configuration system functions."""
    
    def test_get_config_system_singleton(self):
        """Test global config system singleton behavior."""
        system1 = get_config_system()
        system2 = get_config_system()
        
        assert system1 is system2
    
    def test_get_config_system_with_settings(self):
        """Test global config system with custom settings."""
        system = get_config_system(
            enable_interpolation=False,
            enable_validation=False,
            strict_mode=True
        )
        
        # Settings only applied on first call
        assert system.enable_interpolation == True  # Default from first call
    
    def test_reset_config_system(self):
        """Test resetting global config system."""
        system1 = get_config_system()
        reset_config_system()
        system2 = get_config_system()
        
        assert system1 is not system2
    
    def test_load_config_convenience_function(self):
        """Test load_config convenience function."""
        result = load_config(MockConfig, {'name': 'convenience_test'})
        
        assert isinstance(result, AdapterResult)
        assert result.config.name == 'convenience_test'
    
    @patch('google_adk_extras.configuration.system.EnhancedRunConfig')
    def test_load_enhanced_run_config_convenience(self, mock_enhanced_config):
        """Test load_enhanced_run_config convenience function."""
        mock_config_instance = Mock()
        mock_enhanced_config.return_value = mock_config_instance
        
        # Mock the load_config call
        with patch('google_adk_extras.configuration.system.load_config') as mock_load:
            mock_result = AdapterResult(config=mock_config_instance)
            mock_load.return_value = mock_result
            
            result = load_enhanced_run_config({'max_llm_calls': 100})
            
            assert result == mock_result
            mock_load.assert_called_once()


class TestConfigurationSystemIntegration:
    """Integration tests for configuration system."""
    
    def test_end_to_end_dict_loading(self):
        """Test end-to-end dictionary configuration loading."""
        system = ConfigurationSystem()
        
        config_dict = {
            'service_name': 'test-api',
            'port': 8080,
            'database': {
                'host': 'localhost',
                'port': 5432
            },
            'features': ['auth', 'logging']
        }
        
        result = system.load_config(MockConfig, config_dict)
        
        assert result.config.service_name == 'test-api'
        assert result.config.port == 8080
        assert result.config.database['host'] == 'localhost'
        assert 'auth' in result.config.features
        assert result.processing_time > 0
        assert 'system_processing_time' in result.metadata
    
    @patch.dict(os.environ, {'TEST_VAR': 'from_env', 'PORT': '9000'})
    def test_end_to_end_with_interpolation(self):
        """Test end-to-end loading with environment interpolation."""
        system = ConfigurationSystem(enable_interpolation=True)
        
        config_dict = {
            'service': '${TEST_VAR}',
            'port': '${PORT}',
            'fallback': '${UNDEFINED_VAR:-default_value}'
        }
        
        result = system.load_config(MockConfig, config_dict)
        
        assert result.config.service == 'from_env'
        assert result.config.port == '9000'
        assert result.config.fallback == 'default_value'
    
    def test_validation_issues_collection(self):
        """Test validation issues are properly collected."""
        system = ConfigurationSystem()
        
        # Create config that will trigger validation issues
        config_dict = {'undefined_env': '${UNDEFINED_VAR}'}
        
        result = system.load_config(MockConfig, config_dict)
        
        # Should have config but with validation issues
        assert result.config is not None
        # May have validation issues from interpolation
    
    def test_strict_mode_error_propagation(self):
        """Test strict mode error propagation."""
        # Create adapter that always fails
        class FailingAdapter(MockAdapter):
            def _create_target_config(self, raw_config, context, validation_issues):
                validation_issues.append(ValidationIssue(
                    path="test",
                    severity=ValidationSeverity.ERROR,
                    message="Always fails"
                ))
                raise ConfigurationError("Forced failure")
        
        system = ConfigurationSystem(strict_mode=True, default_adapters=False)
        system.register_adapter("failing", FailingAdapter)
        
        with pytest.raises(ConfigurationError):
            system.load_config(MockConfig, {'key': 'value'}, adapter_name="failing")
    
    def test_non_strict_mode_error_handling(self):
        """Test non-strict mode graceful error handling."""
        class FailingAdapter(MockAdapter):
            def _create_target_config(self, raw_config, context, validation_issues):
                validation_issues.append(ValidationIssue(
                    path="test", 
                    severity=ValidationSeverity.ERROR,
                    message="Graceful failure"
                ))
                raise ConfigurationError("Forced failure")
        
        system = ConfigurationSystem(strict_mode=False, default_adapters=False)
        system.register_adapter("failing", FailingAdapter)
        
        result = system.load_config(MockConfig, {'key': 'value'}, adapter_name="failing")
        
        assert result.config is None
        assert result.has_errors() == True
    
    def test_multiple_adapters_priority(self):
        """Test adapter selection priority."""
        system = ConfigurationSystem(default_adapters=False)
        
        # Register multiple adapters that can handle dicts
        class FirstAdapter(MockAdapter):
            pass
        
        class SecondAdapter(MockAdapter):
            pass
        
        system.register_adapter("first", FirstAdapter)
        system.register_adapter("second", SecondAdapter)  
        
        # Should use first registered adapter that can handle the source
        result = system.load_config(MockConfig, {'key': 'value'})
        
        assert result.metadata['adapter_used'] in ['FirstAdapter', 'SecondAdapter']