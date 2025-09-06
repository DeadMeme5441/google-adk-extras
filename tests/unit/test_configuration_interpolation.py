"""Unit tests for Environment Variable Interpolation."""

import os
from unittest.mock import patch, Mock

import pytest

from google_adk_extras.configuration.interpolation import (
    EnvironmentInterpolator,
    InterpolationConfig,
    InterpolationSyntax,
    InterpolationPattern,
    create_interpolator,
    interpolate_string
)
from google_adk_extras.configuration.base_adapter import (
    ValidationIssue,
    ValidationSeverity,
    ConfigurationContext,
    ConfigSourceType
)


@pytest.fixture
def clean_env():
    """Fixture to provide clean environment for tests."""
    original_env = dict(os.environ)
    os.environ.clear()
    
    # Set test environment variables
    os.environ.update({
        'TEST_VAR': 'test_value',
        'DATABASE_URL': 'postgresql://localhost/testdb',
        'API_KEY': 'secret123',
        'PORT': '8080',
        'DEBUG': 'true',
        'EMPTY_VAR': '',
        'PREFIX_APP_NAME': 'myapp',
        'PREFIX_VERSION': '1.0.0'
    })
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def interpolator():
    """Create default interpolator for testing."""
    return EnvironmentInterpolator()


@pytest.fixture
def validation_issues():
    """Create list for collecting validation issues."""
    return []


class TestInterpolationConfig:
    """Test cases for InterpolationConfig."""
    
    def test_default_config(self):
        """Test default interpolation configuration."""
        config = InterpolationConfig()
        
        assert InterpolationSyntax.SHELL in config.enabled_syntaxes
        assert InterpolationSyntax.PYTHON in config.enabled_syntaxes
        assert config.allow_undefined == False
        assert config.case_sensitive == True
        assert config.recursive_interpolation == True
        assert config.max_recursion_depth == 10
        assert config.prefix_filter is None
        assert config.custom_patterns == []
        assert config.validation_enabled == True
    
    def test_custom_config(self):
        """Test custom interpolation configuration."""
        config = InterpolationConfig(
            enabled_syntaxes=[InterpolationSyntax.ANSIBLE],
            allow_undefined=True,
            case_sensitive=False,
            recursive_interpolation=False,
            max_recursion_depth=5,
            prefix_filter="APP_",
            validation_enabled=False
        )
        
        assert config.enabled_syntaxes == [InterpolationSyntax.ANSIBLE]
        assert config.allow_undefined == True
        assert config.case_sensitive == False
        assert config.recursive_interpolation == False
        assert config.max_recursion_depth == 5
        assert config.prefix_filter == "APP_"
        assert config.validation_enabled == False


class TestEnvironmentInterpolator:
    """Test cases for EnvironmentInterpolator."""
    
    def test_interpolator_initialization(self):
        """Test interpolator initialization."""
        config = InterpolationConfig(enabled_syntaxes=[InterpolationSyntax.SHELL])
        interpolator = EnvironmentInterpolator(config)
        
        assert interpolator.config == config
        assert len(interpolator._active_patterns) == 1
        assert isinstance(interpolator._cache, dict)
    
    def test_default_initialization(self):
        """Test interpolator with default config."""
        interpolator = EnvironmentInterpolator()
        
        assert len(interpolator._active_patterns) == 2  # SHELL and PYTHON
    
    def test_shell_syntax_interpolation(self, clean_env, interpolator, validation_issues):
        """Test shell syntax ${VAR} interpolation."""
        test_cases = [
            ("${TEST_VAR}", "test_value"),
            ("${DATABASE_URL}", "postgresql://localhost/testdb"),
            ("prefix_${API_KEY}_suffix", "prefix_secret123_suffix"),
            ("${PORT}", "8080"),
        ]
        
        for input_str, expected in test_cases:
            result = interpolator._interpolate_string(input_str, "test", validation_issues)
            assert result == expected, f"Failed for input: {input_str}"
    
    def test_shell_syntax_with_defaults(self, clean_env, interpolator, validation_issues):
        """Test shell syntax with default values."""
        test_cases = [
            ("${UNDEFINED_VAR:-default_value}", "default_value"),
            ("${TEST_VAR:-fallback}", "test_value"),  # Should use actual value
            ("${EMPTY_VAR:-fallback}", ""),  # Should use empty value, not fallback
            ("${UNDEFINED:-}", ""),  # Empty default
        ]
        
        for input_str, expected in test_cases:
            result = interpolator._interpolate_string(input_str, "test", validation_issues)
            assert result == expected, f"Failed for input: {input_str}"
    
    def test_python_syntax_interpolation(self, clean_env, interpolator, validation_issues):
        """Test Python syntax {VAR} interpolation."""
        test_cases = [
            ("{TEST_VAR}", "test_value"),
            ("{DATABASE_URL}", "postgresql://localhost/testdb"),
            ("prefix_{API_KEY}_suffix", "prefix_secret123_suffix"),
            ("{UNDEFINED_VAR:default_value}", "default_value"),
        ]
        
        for input_str, expected in test_cases:
            result = interpolator._interpolate_string(input_str, "test", validation_issues)
            assert result == expected, f"Failed for input: {input_str}"
    
    def test_mixed_syntax_interpolation(self, clean_env, interpolator, validation_issues):
        """Test mixed syntax interpolation."""
        input_str = "${TEST_VAR} and {DATABASE_URL}"
        expected = "test_value and postgresql://localhost/testdb"
        
        result = interpolator._interpolate_string(input_str, "test", validation_issues)
        assert result == expected
    
    def test_recursive_interpolation(self, clean_env, validation_issues):
        """Test recursive environment variable interpolation."""
        os.environ['NESTED_VAR'] = '${TEST_VAR}'
        os.environ['DOUBLE_NESTED'] = '${NESTED_VAR}_suffix'
        
        interpolator = EnvironmentInterpolator()
        
        result = interpolator._interpolate_string("${DOUBLE_NESTED}", "test", validation_issues)
        assert result == "test_value_suffix"
    
    def test_max_recursion_depth(self, clean_env, interpolator, validation_issues):
        """Test maximum recursion depth protection."""
        # Create circular reference
        os.environ['CIRCULAR_A'] = '${CIRCULAR_B}'
        os.environ['CIRCULAR_B'] = '${CIRCULAR_A}'
        
        interpolator.config.max_recursion_depth = 2
        
        result = interpolator._interpolate_string("${CIRCULAR_A}", "test", validation_issues)
        
        # Should stop recursion and add warning
        assert len(validation_issues) > 0
        assert any(issue.severity == ValidationSeverity.WARNING 
                  for issue in validation_issues)
    
    def test_undefined_variable_strict_mode(self, clean_env, interpolator, validation_issues):
        """Test undefined variable in strict mode."""
        interpolator.config.allow_undefined = False
        
        result = interpolator._interpolate_string("${UNDEFINED_VAR}", "test", validation_issues)
        
        # Should return placeholder and add error
        assert result == "${UNDEFINED_VAR}"
        assert len(validation_issues) > 0
        assert any(issue.severity == ValidationSeverity.ERROR 
                  for issue in validation_issues)
    
    def test_undefined_variable_allow_mode(self, clean_env, validation_issues):
        """Test undefined variable with allow_undefined=True."""
        config = InterpolationConfig(allow_undefined=True)
        interpolator = EnvironmentInterpolator(config)
        
        result = interpolator._interpolate_string("${UNDEFINED_VAR}", "test", validation_issues)
        
        # Should return empty string and add warning
        assert result == ""
        assert len(validation_issues) > 0
        assert any(issue.severity == ValidationSeverity.WARNING 
                  for issue in validation_issues)
    
    def test_case_sensitive_variables(self, clean_env, validation_issues):
        """Test case-sensitive variable handling."""
        os.environ['TestVar'] = 'mixed_case'
        
        # Case sensitive (default)
        config = InterpolationConfig(case_sensitive=True)
        interpolator = EnvironmentInterpolator(config)
        
        result = interpolator._interpolate_string("${testvar}", "test", validation_issues)
        assert "${testvar}" in result  # Should not match
        
        # Case insensitive
        config = InterpolationConfig(case_sensitive=False)
        interpolator = EnvironmentInterpolator(config)
        validation_issues.clear()
        
        result = interpolator._interpolate_string("${testvar}", "test", validation_issues)
        assert result == "mixed_case"
    
    def test_prefix_filter(self, clean_env, validation_issues):
        """Test prefix filtering."""
        config = InterpolationConfig(prefix_filter="PREFIX_")
        interpolator = EnvironmentInterpolator(config)
        
        # Should interpolate prefixed variables
        result = interpolator._interpolate_string("${PREFIX_APP_NAME}", "test", validation_issues)
        assert result == "myapp"
        
        # Should not interpolate non-prefixed variables
        result = interpolator._interpolate_string("${TEST_VAR}", "test", validation_issues)
        assert result == "${TEST_VAR}"
    
    def test_dict_interpolation(self, clean_env, interpolator):
        """Test dictionary interpolation."""
        config_dict = {
            'database_url': '${DATABASE_URL}',
            'api_config': {
                'key': '${API_KEY}',
                'port': '${PORT}'
            },
            'static_value': 'unchanged'
        }
        
        result = interpolator.interpolate(config_dict)
        
        assert result['database_url'] == 'postgresql://localhost/testdb'
        assert result['api_config']['key'] == 'secret123'
        assert result['api_config']['port'] == '8080'
        assert result['static_value'] == 'unchanged'
    
    def test_list_interpolation(self, clean_env, interpolator):
        """Test list interpolation."""
        config_list = [
            '${TEST_VAR}',
            {'nested': '${API_KEY}'},
            'static',
            ['${PORT}', 'static']
        ]
        
        result = interpolator.interpolate(config_list)
        
        assert result[0] == 'test_value'
        assert result[1]['nested'] == 'secret123'
        assert result[2] == 'static'
        assert result[3][0] == '8080'
        assert result[3][1] == 'static'
    
    def test_string_interpolation(self, clean_env, interpolator):
        """Test direct string interpolation."""
        result = interpolator.interpolate('${TEST_VAR}')
        assert result == 'test_value'
    
    def test_non_string_passthrough(self, clean_env, interpolator):
        """Test non-string values pass through unchanged."""
        test_values = [123, 45.67, True, False, None]
        
        for value in test_values:
            result = interpolator.interpolate(value)
            assert result == value
    
    def test_ansible_syntax(self, clean_env, validation_issues):
        """Test Ansible syntax interpolation."""
        config = InterpolationConfig(enabled_syntaxes=[InterpolationSyntax.ANSIBLE])
        interpolator = EnvironmentInterpolator(config)
        
        test_cases = [
            ("{{ TEST_VAR }}", "test_value"),
            ('{{ UNDEFINED_VAR | default("fallback") }}', "fallback"),
            ("{{ DATABASE_URL }}", "postgresql://localhost/testdb"),
        ]
        
        for input_str, expected in test_cases:
            result = interpolator._interpolate_string(input_str, "test", validation_issues)
            assert result == expected, f"Failed for input: {input_str}"
    
    def test_mustache_syntax(self, clean_env, validation_issues):
        """Test Mustache syntax interpolation."""
        config = InterpolationConfig(enabled_syntaxes=[InterpolationSyntax.MUSTACHE])
        interpolator = EnvironmentInterpolator(config)
        
        test_cases = [
            ("{{TEST_VAR}}", "test_value"),
            ("{{DATABASE_URL}}", "postgresql://localhost/testdb"),
        ]
        
        for input_str, expected in test_cases:
            result = interpolator._interpolate_string(input_str, "test", validation_issues)
            assert result == expected, f"Failed for input: {input_str}"
    
    def test_custom_pattern(self, clean_env, validation_issues):
        """Test custom interpolation pattern."""
        import re
        
        # Custom pattern: %{VAR}
        custom_pattern = InterpolationPattern(
            syntax=InterpolationSyntax.CUSTOM,
            regex=re.compile(r'%\{([A-Za-z_][A-Za-z0-9_]*?)\}'),
            group_names=['var_name'],
            supports_defaults=False,
            example='%{TEST_VAR}'
        )
        
        config = InterpolationConfig(
            enabled_syntaxes=[],
            custom_patterns=[custom_pattern]
        )
        interpolator = EnvironmentInterpolator(config)
        
        result = interpolator._interpolate_string("%{TEST_VAR}", "test", validation_issues)
        assert result == "test_value"
    
    def test_cache_functionality(self, clean_env, interpolator, validation_issues):
        """Test interpolation caching."""
        input_str = "${TEST_VAR}_${API_KEY}"
        
        # First call - should cache
        result1 = interpolator._interpolate_string(input_str, "test", validation_issues)
        cache_size_after_first = len(interpolator._cache)
        
        # Second call - should use cache
        result2 = interpolator._interpolate_string(input_str, "test", validation_issues)
        cache_size_after_second = len(interpolator._cache)
        
        assert result1 == result2
        assert cache_size_after_first > 0
        assert cache_size_after_second == cache_size_after_first
    
    def test_clear_cache(self, interpolator):
        """Test cache clearing."""
        interpolator._cache['test'] = 'value'
        assert len(interpolator._cache) == 1
        
        interpolator.clear_cache()
        assert len(interpolator._cache) == 0
    
    def test_cache_stats(self, interpolator):
        """Test cache statistics."""
        stats = interpolator.get_cache_stats()
        
        assert 'cache_size' in stats
        assert 'active_patterns' in stats
        assert 'enabled_syntaxes' in stats
        assert 'custom_patterns' in stats
        assert isinstance(stats['cache_size'], int)
        assert isinstance(stats['active_patterns'], int)
    
    def test_add_custom_pattern(self, clean_env, interpolator, validation_issues):
        """Test adding custom pattern dynamically."""
        import re
        
        custom_pattern = InterpolationPattern(
            syntax=InterpolationSyntax.CUSTOM,
            regex=re.compile(r'#\{([A-Za-z_][A-Za-z0-9_]*?)\}'),
            group_names=['var_name'],
            supports_defaults=False
        )
        
        # Add pattern
        interpolator.add_custom_pattern(custom_pattern)
        
        # Test custom pattern works
        result = interpolator._interpolate_string("#{TEST_VAR}", "test", validation_issues)
        assert result == "test_value"


class TestConvenienceFunctions:
    """Test convenience functions for interpolation."""
    
    def test_create_interpolator_defaults(self, clean_env):
        """Test create_interpolator with defaults."""
        interpolator = create_interpolator()
        
        assert InterpolationSyntax.SHELL in interpolator.config.enabled_syntaxes
        assert InterpolationSyntax.PYTHON in interpolator.config.enabled_syntaxes
        assert interpolator.config.allow_undefined == False
        assert interpolator.config.case_sensitive == True
        assert interpolator.config.recursive_interpolation == True
    
    def test_create_interpolator_custom(self, clean_env):
        """Test create_interpolator with custom settings."""
        interpolator = create_interpolator(
            syntax=[InterpolationSyntax.ANSIBLE],
            allow_undefined=True,
            case_sensitive=False,
            recursive=False
        )
        
        assert interpolator.config.enabled_syntaxes == [InterpolationSyntax.ANSIBLE]
        assert interpolator.config.allow_undefined == True
        assert interpolator.config.case_sensitive == False
        assert interpolator.config.recursive_interpolation == False
    
    def test_interpolate_string_function(self, clean_env):
        """Test interpolate_string convenience function."""
        result = interpolate_string("${TEST_VAR}")
        assert result == "test_value"
        
        result = interpolate_string("${UNDEFINED:-fallback}")
        assert result == "fallback"
    
    def test_interpolate_string_with_options(self, clean_env):
        """Test interpolate_string with custom options."""
        result = interpolate_string(
            "${UNDEFINED_VAR}",
            syntax=[InterpolationSyntax.SHELL],
            allow_undefined=True
        )
        assert result == ""


class TestInterpolationWithValidation:
    """Test interpolation with validation context."""
    
    def test_validation_context_integration(self, clean_env):
        """Test interpolation with configuration context."""
        context = ConfigurationContext(
            source_type=ConfigSourceType.YAML_FILE,
            source_path="test.yaml",
            interpolation_enabled=True
        )
        
        interpolator = EnvironmentInterpolator()
        validation_issues = []
        
        result = interpolator.interpolate(
            {"value": "${TEST_VAR}"},
            context,
            validation_issues
        )
        
        assert result["value"] == "test_value"
        # Should have info about using actual value (no issues expected for found vars)
    
    def test_validation_disabled(self, clean_env):
        """Test interpolation with validation disabled."""
        config = InterpolationConfig(validation_enabled=False)
        interpolator = EnvironmentInterpolator(config)
        validation_issues = []
        
        # Use undefined variable
        result = interpolator._interpolate_string("${UNDEFINED}", "test", validation_issues)
        
        # Should still return placeholder but no validation issues
        assert result == "${UNDEFINED}"
        assert len(validation_issues) == 0