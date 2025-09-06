"""Enhanced Configuration Architecture for google-adk-extras.

This package provides a flexible configuration system with adapter-based
architecture supporting multiple configuration formats and comprehensive
validation and error reporting.

Main Components:
- EnhancedConfigAdapter: Base class for configuration adapters
- EnvironmentInterpolator: Environment variable interpolation service
- ConfigurationSystem: Unified configuration loading system
- Built-in adapters for YAML, JSON, TOML, dict, environment, and remote configs

Quick Start:
    ```python
    from google_adk_extras.configuration import load_config
    from google_adk_extras.runners.config import EnhancedRunConfig
    
    # Load from YAML file
    result = load_config(EnhancedRunConfig, "config.yaml")
    config = result.config
    
    # Load from dictionary
    config_dict = {"max_llm_calls": 100}
    result = load_config(EnhancedRunConfig, config_dict)
    
    # Load with environment variable interpolation
    yaml_content = '''
    database_url: ${DATABASE_URL:-postgresql://localhost/db}
    api_key: ${API_KEY}
    '''
    result = load_config(EnhancedRunConfig, yaml_content)
    ```

Architecture Features:
- Automatic format detection
- Environment variable interpolation with multiple syntaxes
- Comprehensive validation and error reporting  
- Clean APIs for external system adapters
- Performance monitoring and caching
- Extensible adapter pattern
"""

from .base_adapter import (
    EnhancedConfigAdapter,
    ConfigSourceType,
    ConfigurationContext,
    AdapterResult,
    ValidationIssue,
    ValidationSeverity,
    ConfigurationError,
    register_adapter,
    get_adapter,
    list_adapters
)

from .interpolation import (
    EnvironmentInterpolator,
    InterpolationConfig,
    InterpolationSyntax,
    InterpolationPattern,
    create_interpolator,
    interpolate_string
)

from .adapters import (
    YAMLConfigAdapter,
    JSONConfigAdapter,
    TOMLConfigAdapter,
    DictConfigAdapter,
    EnvironmentConfigAdapter,
    RemoteConfigAdapter
)

from .system import (
    ConfigurationSystem,
    get_config_system,
    load_config,
    load_enhanced_run_config,
    reset_config_system
)

__all__ = [
    # Base classes and types
    'EnhancedConfigAdapter',
    'ConfigSourceType', 
    'ConfigurationContext',
    'AdapterResult',
    'ValidationIssue',
    'ValidationSeverity',
    'ConfigurationError',
    
    # Interpolation
    'EnvironmentInterpolator',
    'InterpolationConfig',
    'InterpolationSyntax',
    'InterpolationPattern',
    'create_interpolator',
    'interpolate_string',
    
    # Adapters
    'YAMLConfigAdapter',
    'JSONConfigAdapter',
    'TOMLConfigAdapter', 
    'DictConfigAdapter',
    'EnvironmentConfigAdapter',
    'RemoteConfigAdapter',
    
    # System
    'ConfigurationSystem',
    'get_config_system',
    'load_config',
    'load_enhanced_run_config',
    'reset_config_system',
    
    # Registry functions
    'register_adapter',
    'get_adapter',
    'list_adapters'
]

# Version info
__version__ = "1.0.0"
__author__ = "google-adk-extras team"
__description__ = "Enhanced Configuration Architecture with Flexible Adapter Pattern"