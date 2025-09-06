"""Unit tests for Configuration Adapters."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest

from google_adk_extras.configuration.adapters import (
    YAMLConfigAdapter,
    JSONConfigAdapter,
    TOMLConfigAdapter,
    DictConfigAdapter,
    EnvironmentConfigAdapter,
    RemoteConfigAdapter
)
from google_adk_extras.configuration.base_adapter import (
    ConfigSourceType,
    ConfigurationContext,
    ConfigurationError,
    ValidationIssue,
    ValidationSeverity
)


class MockConfig:
    """Mock configuration class for testing."""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def from_yaml_dict(cls, data):
        return cls(**data)
    
    @classmethod  
    def from_json(cls, data):
        return cls(**data)
    
    @classmethod
    def from_toml(cls, data):
        return cls(**data)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
    
    @classmethod
    def from_env(cls, data):
        return cls(**data)
    
    @classmethod
    def from_remote(cls, data):
        return cls(**data)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def clean_env():
    """Clean environment for testing."""
    original_env = dict(os.environ)
    os.environ.clear()
    
    # Set test environment variables
    os.environ.update({
        'TEST_VAR': 'test_value',
        'DATABASE_URL': 'postgresql://localhost/testdb',
        'API_KEY': 'secret123',
        'PORT': '8080',
        'DEBUG': 'true',
        'APP_NAME': 'myapp',
        'APP_VERSION': '1.0.0'
    })
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


class TestYAMLConfigAdapter:
    """Test cases for YAML configuration adapter."""
    
    @pytest.fixture
    def yaml_adapter(self):
        """Create YAML adapter for testing."""
        return YAMLConfigAdapter(target_type=MockConfig)
    
    def test_supported_source_types(self, yaml_adapter):
        """Test supported source types."""
        types = yaml_adapter.get_supported_source_types()
        assert ConfigSourceType.YAML_FILE in types
    
    def test_can_handle_yaml_files(self, yaml_adapter):
        """Test YAML file detection."""
        assert yaml_adapter.can_handle_source("config.yaml") == True
        assert yaml_adapter.can_handle_source("config.yml") == True
        assert yaml_adapter.can_handle_source("---\nkey: value") == True
        assert yaml_adapter.can_handle_source("config.json") == False
        assert yaml_adapter.can_handle_source({"key": "value"}) == False
    
    @patch('builtins.open', mock_open(read_data='key: value\nport: 8080'))
    @patch('google_adk_extras.configuration.adapters.yaml.safe_load')
    def test_load_from_yaml_file(self, mock_yaml_load, yaml_adapter, temp_dir):
        """Test loading from YAML file."""
        mock_yaml_load.return_value = {'key': 'value', 'port': 8080}
        
        yaml_file = temp_dir / "config.yaml"
        context = ConfigurationContext(source_type=ConfigSourceType.YAML_FILE)
        
        result = yaml_adapter._load_raw_config(yaml_file, context)
        
        assert result == {'key': 'value', 'port': 8080}
        assert context.source_path is not None
    
    @patch('google_adk_extras.configuration.adapters.yaml.safe_load')
    def test_load_from_yaml_string(self, mock_yaml_load, yaml_adapter):
        """Test loading from YAML string content."""
        mock_yaml_load.return_value = {'key': 'value'}
        
        yaml_content = "key: value"
        context = ConfigurationContext(source_type=ConfigSourceType.YAML_FILE)
        
        result = yaml_adapter._load_raw_config(yaml_content, context)
        
        assert result == {'key': 'value'}
    
    @patch('google_adk_extras.configuration.adapters.yaml.safe_load')
    def test_yaml_parse_error(self, mock_yaml_load, yaml_adapter):
        """Test YAML parsing error handling."""
        import yaml
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")
        
        context = ConfigurationContext(source_type=ConfigSourceType.YAML_FILE)
        
        with pytest.raises(ConfigurationError):
            yaml_adapter._load_raw_config("invalid: yaml: content", context)
    
    def test_yaml_import_error(self):
        """Test YAML adapter when PyYAML is not available."""
        with patch('google_adk_extras.configuration.adapters.yaml', None):
            with patch.dict('sys.modules', {'yaml': None}):
                adapter = YAMLConfigAdapter(target_type=MockConfig)
                context = ConfigurationContext(source_type=ConfigSourceType.YAML_FILE)
                
                with pytest.raises(ConfigurationError, match="PyYAML is required"):
                    adapter._load_raw_config("key: value", context)
    
    def test_create_target_config_with_yaml_method(self, yaml_adapter):
        """Test creating target config using from_yaml_dict method."""
        raw_config = {'name': 'test', 'value': 123}
        context = ConfigurationContext(source_type=ConfigSourceType.YAML_FILE)
        validation_issues = []
        
        result = yaml_adapter._create_target_config(raw_config, context, validation_issues)
        
        assert isinstance(result, MockConfig)
        assert result.name == 'test'
        assert result.value == 123
    
    def test_create_target_config_error(self, yaml_adapter):
        """Test target config creation error handling."""
        # Mock target type that raises exception
        yaml_adapter.target_type = Mock(side_effect=Exception("Creation failed"))
        
        raw_config = {'key': 'value'}
        context = ConfigurationContext(source_type=ConfigSourceType.YAML_FILE)
        validation_issues = []
        
        with pytest.raises(ConfigurationError):
            yaml_adapter._create_target_config(raw_config, context, validation_issues)
        
        assert len(validation_issues) > 0
        assert validation_issues[0].severity == ValidationSeverity.ERROR


class TestJSONConfigAdapter:
    """Test cases for JSON configuration adapter."""
    
    @pytest.fixture
    def json_adapter(self):
        """Create JSON adapter for testing."""
        return JSONConfigAdapter(target_type=MockConfig)
    
    def test_supported_source_types(self, json_adapter):
        """Test supported source types."""
        types = json_adapter.get_supported_source_types()
        assert ConfigSourceType.JSON_FILE in types
    
    def test_can_handle_json_sources(self, json_adapter):
        """Test JSON source detection."""
        assert json_adapter.can_handle_source("config.json") == True
        assert json_adapter.can_handle_source('{"key": "value"}') == True
        assert json_adapter.can_handle_source('[{"item": 1}]') == True
        assert json_adapter.can_handle_source("config.yaml") == False
        assert json_adapter.can_handle_source({"key": "value"}) == False
    
    @patch('builtins.open', mock_open(read_data='{"key": "value", "port": 8080}'))
    def test_load_from_json_file(self, json_adapter, temp_dir):
        """Test loading from JSON file."""
        json_file = temp_dir / "config.json"
        context = ConfigurationContext(source_type=ConfigSourceType.JSON_FILE)
        
        result = json_adapter._load_raw_config(json_file, context)
        
        assert result == {'key': 'value', 'port': 8080}
        assert context.source_path is not None
    
    def test_load_from_json_string(self, json_adapter):
        """Test loading from JSON string."""
        json_content = '{"key": "value", "number": 42}'
        context = ConfigurationContext(source_type=ConfigSourceType.JSON_FILE)
        
        result = json_adapter._load_raw_config(json_content, context)
        
        assert result == {'key': 'value', 'number': 42}
    
    def test_json_parse_error(self, json_adapter):
        """Test JSON parsing error handling."""
        invalid_json = '{"key": invalid_json}'
        context = ConfigurationContext(source_type=ConfigSourceType.JSON_FILE)
        
        with pytest.raises(ConfigurationError):
            json_adapter._load_raw_config(invalid_json, context)
    
    def test_non_object_json_error(self, json_adapter):
        """Test error when JSON is not an object."""
        json_array = '[1, 2, 3]'
        context = ConfigurationContext(source_type=ConfigSourceType.JSON_FILE)
        
        with pytest.raises(ConfigurationError):
            json_adapter._load_raw_config(json_array, context)
    
    def test_create_target_config(self, json_adapter):
        """Test creating target config from JSON data."""
        raw_config = {'name': 'json_test', 'enabled': True}
        context = ConfigurationContext(source_type=ConfigSourceType.JSON_FILE)
        validation_issues = []
        
        result = json_adapter._create_target_config(raw_config, context, validation_issues)
        
        assert isinstance(result, MockConfig)
        assert result.name == 'json_test'
        assert result.enabled == True


class TestTOMLConfigAdapter:
    """Test cases for TOML configuration adapter."""
    
    @pytest.fixture
    def toml_adapter(self):
        """Create TOML adapter for testing."""
        return TOMLConfigAdapter(target_type=MockConfig)
    
    def test_supported_source_types(self, toml_adapter):
        """Test supported source types."""
        types = toml_adapter.get_supported_source_types()
        assert ConfigSourceType.TOML_FILE in types
    
    def test_can_handle_toml_files(self, toml_adapter):
        """Test TOML file detection."""
        assert toml_adapter.can_handle_source("config.toml") == True
        assert toml_adapter.can_handle_source("config.yaml") == False
        assert toml_adapter.can_handle_source({"key": "value"}) == False
    
    @patch('google_adk_extras.configuration.adapters.tomli.load')
    @patch('builtins.open', mock_open())
    def test_load_from_toml_file(self, mock_open_file, mock_tomli_load, toml_adapter, temp_dir):
        """Test loading from TOML file."""
        mock_tomli_load.return_value = {'app': {'name': 'test', 'version': '1.0'}}
        
        toml_file = temp_dir / "config.toml"
        context = ConfigurationContext(source_type=ConfigSourceType.TOML_FILE)
        
        result = toml_adapter._load_raw_config(toml_file, context)
        
        assert result == {'app': {'name': 'test', 'version': '1.0'}}
        assert context.source_path is not None
    
    @patch('google_adk_extras.configuration.adapters.tomli.loads')
    def test_load_from_toml_string(self, mock_tomli_loads, toml_adapter):
        """Test loading from TOML string."""
        mock_tomli_loads.return_value = {'key': 'value'}
        
        toml_content = 'key = "value"'
        context = ConfigurationContext(source_type=ConfigSourceType.TOML_FILE)
        
        result = toml_adapter._load_raw_config(toml_content, context)
        
        assert result == {'key': 'value'}
    
    def test_toml_import_error(self):
        """Test TOML adapter when tomli is not available."""
        with patch.dict('sys.modules', {'tomli': None, 'tomllib': None}):
            adapter = TOMLConfigAdapter(target_type=MockConfig)
            context = ConfigurationContext(source_type=ConfigSourceType.TOML_FILE)
            
            with pytest.raises(ConfigurationError, match="tomli is required"):
                adapter._load_raw_config("key = 'value'", context)
    
    def test_create_target_config(self, toml_adapter):
        """Test creating target config from TOML data."""
        raw_config = {'database': {'host': 'localhost', 'port': 5432}}
        context = ConfigurationContext(source_type=ConfigSourceType.TOML_FILE)
        validation_issues = []
        
        result = toml_adapter._create_target_config(raw_config, context, validation_issues)
        
        assert isinstance(result, MockConfig)
        assert result.database['host'] == 'localhost'


class TestDictConfigAdapter:
    """Test cases for Dictionary configuration adapter."""
    
    @pytest.fixture
    def dict_adapter(self):
        """Create dictionary adapter for testing."""
        return DictConfigAdapter(target_type=MockConfig)
    
    def test_supported_source_types(self, dict_adapter):
        """Test supported source types."""
        types = dict_adapter.get_supported_source_types()
        assert ConfigSourceType.DICT in types
    
    def test_can_handle_dict_sources(self, dict_adapter):
        """Test dictionary source detection."""
        assert dict_adapter.can_handle_source({"key": "value"}) == True
        assert dict_adapter.can_handle_source("config.yaml") == False
        assert dict_adapter.can_handle_source(["list"]) == False
    
    def test_load_from_dict(self, dict_adapter):
        """Test loading from dictionary."""
        source_dict = {'name': 'test', 'config': {'nested': True}}
        context = ConfigurationContext(source_type=ConfigSourceType.DICT)
        
        result = dict_adapter._load_raw_config(source_dict, context)
        
        assert result == source_dict
        assert result is not source_dict  # Should be a deep copy
    
    def test_load_from_non_dict_error(self, dict_adapter):
        """Test error when source is not a dictionary."""
        context = ConfigurationContext(source_type=ConfigSourceType.DICT)
        
        with pytest.raises(ConfigurationError):
            dict_adapter._load_raw_config("not a dict", context)
    
    def test_create_target_config(self, dict_adapter):
        """Test creating target config from dictionary."""
        raw_config = {'service': 'api', 'port': 3000}
        context = ConfigurationContext(source_type=ConfigSourceType.DICT)
        validation_issues = []
        
        result = dict_adapter._create_target_config(raw_config, context, validation_issues)
        
        assert isinstance(result, MockConfig)
        assert result.service == 'api'
        assert result.port == 3000


class TestEnvironmentConfigAdapter:
    """Test cases for Environment configuration adapter."""
    
    @pytest.fixture
    def env_adapter(self, clean_env):
        """Create environment adapter for testing."""
        return EnvironmentConfigAdapter(target_type=MockConfig)
    
    def test_supported_source_types(self, env_adapter):
        """Test supported source types."""
        types = env_adapter.get_supported_source_types()
        assert ConfigSourceType.ENV_VARS in types
    
    def test_can_handle_env_sources(self, env_adapter):
        """Test environment source detection."""
        context = ConfigurationContext(source_type=ConfigSourceType.ENV_VARS)
        assert env_adapter.can_handle_source(None, context) == True
        assert env_adapter.can_handle_source(None, None) == True
        
        other_context = ConfigurationContext(source_type=ConfigSourceType.DICT)
        assert env_adapter.can_handle_source("config.yaml", other_context) == False
    
    def test_load_from_environment(self, env_adapter, clean_env):
        """Test loading from environment variables."""
        context = ConfigurationContext(source_type=ConfigSourceType.ENV_VARS)
        
        result = env_adapter._load_raw_config(None, context)
        
        assert 'test_var' in result
        assert 'database_url' in result
        assert 'api_key' in result
        assert result['test_var'] == 'test_value'
        assert result['database_url'] == 'postgresql://localhost/testdb'
    
    def test_prefix_filtering(self, clean_env):
        """Test environment variable prefix filtering."""
        adapter = EnvironmentConfigAdapter(target_type=MockConfig, prefix="APP_")
        context = ConfigurationContext(source_type=ConfigSourceType.ENV_VARS)
        
        result = adapter._load_raw_config(None, context)
        
        assert 'name' in result  # APP_NAME -> name
        assert 'version' in result  # APP_VERSION -> version
        assert 'test_var' not in result  # TEST_VAR should be filtered out
    
    def test_nested_key_conversion(self, env_adapter):
        """Test nested key conversion with separators."""
        os.environ['NESTED__KEY__VALUE'] = 'nested_value'
        os.environ['DATABASE__HOST'] = 'localhost'
        os.environ['DATABASE__PORT'] = '5432'
        
        context = ConfigurationContext(source_type=ConfigSourceType.ENV_VARS)
        
        result = env_adapter._load_raw_config(None, context)
        
        assert 'nested' in result
        assert 'database' in result
        assert result['nested']['key']['value'] == 'nested_value'
        assert result['database']['host'] == 'localhost'
        assert result['database']['port'] == 5432  # Should be converted to int
    
    def test_value_type_conversion(self, env_adapter, clean_env):
        """Test environment variable value type conversion."""
        os.environ.update({
            'BOOL_TRUE': 'true',
            'BOOL_FALSE': 'false',
            'BOOL_YES': 'yes',
            'BOOL_NO': 'no',
            'BOOL_ON': 'on',
            'BOOL_OFF': 'off',
            'BOOL_1': '1',
            'BOOL_0': '0',
            'NULL_VAR': 'null',
            'NONE_VAR': 'none',
            'EMPTY_VAR': '',
            'INT_VAR': '42',
            'FLOAT_VAR': '3.14',
            'JSON_VAR': '{"key": "value"}',
            'STRING_VAR': 'just a string'
        })
        
        context = ConfigurationContext(source_type=ConfigSourceType.ENV_VARS)
        result = env_adapter._load_raw_config(None, context)
        
        # Boolean conversions
        assert result['bool_true'] == True
        assert result['bool_false'] == False
        assert result['bool_yes'] == True
        assert result['bool_no'] == False
        assert result['bool_on'] == True
        assert result['bool_off'] == False
        assert result['bool_1'] == True
        assert result['bool_0'] == False
        
        # Null conversions
        assert result['null_var'] is None
        assert result['none_var'] is None
        assert result['empty_var'] is None
        
        # Numeric conversions
        assert result['int_var'] == 42
        assert result['float_var'] == 3.14
        
        # JSON conversion
        assert result['json_var'] == {"key": "value"}
        
        # String fallback
        assert result['string_var'] == "just a string"
    
    def test_create_target_config(self, env_adapter, clean_env):
        """Test creating target config from environment variables."""
        raw_config = {'app_name': 'test_app', 'debug': True}
        context = ConfigurationContext(source_type=ConfigSourceType.ENV_VARS)
        validation_issues = []
        
        result = env_adapter._create_target_config(raw_config, context, validation_issues)
        
        assert isinstance(result, MockConfig)
        assert result.app_name == 'test_app'
        assert result.debug == True


class TestRemoteConfigAdapter:
    """Test cases for Remote configuration adapter."""
    
    @pytest.fixture
    def remote_adapter(self):
        """Create remote adapter for testing."""
        return RemoteConfigAdapter(target_type=MockConfig, timeout=10)
    
    def test_supported_source_types(self, remote_adapter):
        """Test supported source types."""
        types = remote_adapter.get_supported_source_types()
        assert ConfigSourceType.REMOTE_URL in types
    
    def test_can_handle_remote_sources(self, remote_adapter):
        """Test remote source detection."""
        assert remote_adapter.can_handle_source("https://example.com/config.json") == True
        assert remote_adapter.can_handle_source("http://example.com/config.yaml") == True
        assert remote_adapter.can_handle_source("config.yaml") == False
        assert remote_adapter.can_handle_source({"key": "value"}) == False
    
    @patch('google_adk_extras.configuration.adapters.urlopen')
    def test_load_json_from_remote(self, mock_urlopen, remote_adapter):
        """Test loading JSON from remote URL."""
        mock_response = Mock()
        mock_response.read.return_value = b'{"key": "value", "number": 42}'
        mock_response.headers.get.return_value = 'application/json'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        url = "https://example.com/config.json"
        context = ConfigurationContext(source_type=ConfigSourceType.REMOTE_URL)
        
        result = remote_adapter._load_raw_config(url, context)
        
        assert result == {'key': 'value', 'number': 42}
        assert context.source_path == url
    
    @patch('google_adk_extras.configuration.adapters.urlopen')
    @patch('google_adk_extras.configuration.adapters.yaml.safe_load')
    def test_load_yaml_from_remote(self, mock_yaml_load, mock_urlopen, remote_adapter):
        """Test loading YAML from remote URL."""
        mock_yaml_load.return_value = {'service': 'api', 'port': 8080}
        mock_response = Mock()
        mock_response.read.return_value = b'service: api\nport: 8080'
        mock_response.headers.get.return_value = 'application/x-yaml'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        url = "https://example.com/config.yaml"
        context = ConfigurationContext(source_type=ConfigSourceType.REMOTE_URL)
        
        result = remote_adapter._load_raw_config(url, context)
        
        assert result == {'service': 'api', 'port': 8080}
    
    @patch('google_adk_extras.configuration.adapters.urlopen')
    def test_remote_request_with_headers(self, mock_urlopen, remote_adapter):
        """Test remote request with custom headers."""
        remote_adapter.headers = {'Authorization': 'Bearer token123'}
        
        mock_response = Mock()
        mock_response.read.return_value = b'{"authenticated": true}'
        mock_response.headers.get.return_value = 'application/json'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        url = "https://api.example.com/config"
        context = ConfigurationContext(source_type=ConfigSourceType.REMOTE_URL)
        
        result = remote_adapter._load_raw_config(url, context)
        
        # Verify request was created with headers
        call_args = mock_urlopen.call_args[0]
        request = call_args[0]
        assert 'Authorization' in request.headers
    
    @patch('google_adk_extras.configuration.adapters.urlopen')
    def test_remote_load_error(self, mock_urlopen, remote_adapter):
        """Test remote loading error handling."""
        mock_urlopen.side_effect = Exception("Connection failed")
        
        url = "https://example.com/config.json"
        context = ConfigurationContext(source_type=ConfigSourceType.REMOTE_URL)
        
        with pytest.raises(ConfigurationError):
            remote_adapter._load_raw_config(url, context)
    
    @patch('google_adk_extras.configuration.adapters.urlopen')
    def test_unknown_format_detection(self, mock_urlopen, remote_adapter):
        """Test automatic format detection."""
        # JSON content without explicit content type
        mock_response = Mock()
        mock_response.read.return_value = b'{"detected": "json"}'
        mock_response.headers.get.return_value = 'text/plain'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        url = "https://example.com/config"
        context = ConfigurationContext(source_type=ConfigSourceType.REMOTE_URL)
        
        result = remote_adapter._load_raw_config(url, context)
        
        assert result == {'detected': 'json'}
    
    def test_create_target_config(self, remote_adapter):
        """Test creating target config from remote data."""
        raw_config = {'remote_service': 'cdn', 'version': '2.0'}
        context = ConfigurationContext(source_type=ConfigSourceType.REMOTE_URL)
        validation_issues = []
        
        result = remote_adapter._create_target_config(raw_config, context, validation_issues)
        
        assert isinstance(result, MockConfig)
        assert result.remote_service == 'cdn'
        assert result.version == '2.0'


class TestAdapterErrorHandling:
    """Test error handling across all adapters."""
    
    def test_create_target_config_fallback_methods(self):
        """Test fallback methods for creating target configurations."""
        
        class ConfigWithFromDict:
            @classmethod
            def from_dict(cls, data):
                return cls(**data)
            
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        class ConfigWithDirectInit:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        # Test from_dict method
        adapter = DictConfigAdapter(target_type=ConfigWithFromDict)
        raw_config = {'name': 'test'}
        context = ConfigurationContext(source_type=ConfigSourceType.DICT)
        validation_issues = []
        
        result = adapter._create_target_config(raw_config, context, validation_issues)
        assert result.name == 'test'
        
        # Test direct initialization
        adapter = DictConfigAdapter(target_type=ConfigWithDirectInit)
        result = adapter._create_target_config(raw_config, context, validation_issues)
        assert result.name == 'test'
    
    def test_validation_issues_collection(self):
        """Test that validation issues are properly collected."""
        adapter = DictConfigAdapter(target_type=Mock)
        adapter.target_type.side_effect = Exception("Creation failed")
        
        raw_config = {'key': 'value'}
        context = ConfigurationContext(source_type=ConfigSourceType.DICT)
        validation_issues = []
        
        with pytest.raises(ConfigurationError):
            adapter._create_target_config(raw_config, context, validation_issues)
        
        assert len(validation_issues) == 1
        assert validation_issues[0].severity == ValidationSeverity.ERROR
        assert "Creation failed" in validation_issues[0].message