"""Configuration Format Adapters.

This module provides concrete adapters for different configuration formats
including YAML, JSON, TOML, dictionary, and environment variables.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar
from urllib.parse import urlparse
from urllib.request import urlopen

from .base_adapter import (
    EnhancedConfigAdapter, 
    ConfigSourceType, 
    ConfigurationContext,
    ValidationIssue, 
    ValidationSeverity,
    ConfigurationError,
    register_adapter
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class YAMLConfigAdapter(EnhancedConfigAdapter):
    """Adapter for YAML configuration files and strings."""
    
    def get_supported_source_types(self) -> List[ConfigSourceType]:
        """Get supported source types."""
        return [ConfigSourceType.YAML_FILE]
    
    def can_handle_source(self, source: Any, context: Optional[ConfigurationContext] = None) -> bool:
        """Check if adapter can handle the source."""
        if isinstance(source, (str, Path)):
            source_str = str(source)
            return (source_str.endswith('.yaml') or 
                   source_str.endswith('.yml') or
                   source_str.startswith('---'))  # YAML document start
        return False
    
    def _load_raw_config(self, source: Any, context: ConfigurationContext) -> Dict[str, Any]:
        """Load raw configuration from YAML source."""
        try:
            import yaml
        except ImportError:
            raise ConfigurationError(
                "PyYAML is required for YAML configuration support. "
                "Install with: pip install pyyaml"
            )
        
        try:
            if isinstance(source, (str, Path)):
                source_path = Path(source)
                if source_path.exists():
                    # Load from file
                    with open(source_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        context.source_path = str(source_path.absolute())
                else:
                    # Treat as YAML content string
                    content = str(source)
            else:
                content = str(source)
            
            # Parse YAML
            config = yaml.safe_load(content)
            
            if not isinstance(config, dict):
                raise ConfigurationError(f"YAML content must be a dictionary, got {type(config).__name__}")
            
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load YAML configuration: {e}")
    
    def _create_target_config(
        self,
        raw_config: Dict[str, Any],
        context: ConfigurationContext,
        validation_issues: List[ValidationIssue]
    ) -> T:
        """Create target configuration from raw YAML data."""
        try:
            # Check if target type has from_yaml_dict method (like EnhancedRunConfig)
            if hasattr(self.target_type, 'from_yaml_dict'):
                return self.target_type.from_yaml_dict(raw_config)
            
            # Check if target type has from_dict method
            if hasattr(self.target_type, 'from_dict'):
                return self.target_type.from_dict(raw_config)
            
            # Try direct instantiation
            return self.target_type(**raw_config)
            
        except Exception as e:
            validation_issues.append(ValidationIssue(
                path="root",
                severity=ValidationSeverity.ERROR,
                message=f"Failed to create {self.target_type.__name__} from YAML: {e}",
                suggestion="Check YAML structure matches target configuration schema"
            ))
            raise ConfigurationError(f"Failed to create configuration: {e}")


class JSONConfigAdapter(EnhancedConfigAdapter):
    """Adapter for JSON configuration files and strings."""
    
    def get_supported_source_types(self) -> List[ConfigSourceType]:
        """Get supported source types."""
        return [ConfigSourceType.JSON_FILE]
    
    def can_handle_source(self, source: Any, context: Optional[ConfigurationContext] = None) -> bool:
        """Check if adapter can handle the source."""
        if isinstance(source, (str, Path)):
            source_str = str(source)
            return (source_str.endswith('.json') or
                   source_str.strip().startswith(('{', '[')))  # JSON content
        return False
    
    def _load_raw_config(self, source: Any, context: ConfigurationContext) -> Dict[str, Any]:
        """Load raw configuration from JSON source."""
        try:
            if isinstance(source, (str, Path)):
                source_path = Path(source)
                if source_path.exists():
                    # Load from file
                    with open(source_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        context.source_path = str(source_path.absolute())
                else:
                    # Treat as JSON content string
                    content = str(source)
            else:
                content = str(source)
            
            # Parse JSON
            config = json.loads(content)
            
            if not isinstance(config, dict):
                raise ConfigurationError(f"JSON content must be an object, got {type(config).__name__}")
            
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Failed to parse JSON: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load JSON configuration: {e}")
    
    def _create_target_config(
        self,
        raw_config: Dict[str, Any],
        context: ConfigurationContext,
        validation_issues: List[ValidationIssue]
    ) -> T:
        """Create target configuration from raw JSON data."""
        try:
            # Check if target type has from_json method
            if hasattr(self.target_type, 'from_json'):
                return self.target_type.from_json(raw_config)
            
            # Check if target type has from_dict method
            if hasattr(self.target_type, 'from_dict'):
                return self.target_type.from_dict(raw_config)
            
            # Try direct instantiation
            return self.target_type(**raw_config)
            
        except Exception as e:
            validation_issues.append(ValidationIssue(
                path="root",
                severity=ValidationSeverity.ERROR,
                message=f"Failed to create {self.target_type.__name__} from JSON: {e}",
                suggestion="Check JSON structure matches target configuration schema"
            ))
            raise ConfigurationError(f"Failed to create configuration: {e}")


class TOMLConfigAdapter(EnhancedConfigAdapter):
    """Adapter for TOML configuration files and strings."""
    
    def get_supported_source_types(self) -> List[ConfigSourceType]:
        """Get supported source types."""
        return [ConfigSourceType.TOML_FILE]
    
    def can_handle_source(self, source: Any, context: Optional[ConfigurationContext] = None) -> bool:
        """Check if adapter can handle the source."""
        if isinstance(source, (str, Path)):
            source_str = str(source)
            return source_str.endswith('.toml')
        return False
    
    def _load_raw_config(self, source: Any, context: ConfigurationContext) -> Dict[str, Any]:
        """Load raw configuration from TOML source."""
        try:
            import tomli
        except ImportError:
            try:
                import tomllib as tomli
            except ImportError:
                raise ConfigurationError(
                    "tomli is required for TOML configuration support. "
                    "Install with: pip install tomli"
                )
        
        try:
            if isinstance(source, (str, Path)):
                source_path = Path(source)
                if source_path.exists():
                    # Load from file
                    with open(source_path, 'rb') as f:
                        config = tomli.load(f)
                        context.source_path = str(source_path.absolute())
                else:
                    # Treat as TOML content string
                    config = tomli.loads(str(source))
            else:
                config = tomli.loads(str(source))
            
            if not isinstance(config, dict):
                raise ConfigurationError(f"TOML content must be a table, got {type(config).__name__}")
            
            return config
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load TOML configuration: {e}")
    
    def _create_target_config(
        self,
        raw_config: Dict[str, Any],
        context: ConfigurationContext,
        validation_issues: List[ValidationIssue]
    ) -> T:
        """Create target configuration from raw TOML data."""
        try:
            # Check if target type has from_toml method
            if hasattr(self.target_type, 'from_toml'):
                return self.target_type.from_toml(raw_config)
            
            # Check if target type has from_dict method
            if hasattr(self.target_type, 'from_dict'):
                return self.target_type.from_dict(raw_config)
            
            # Try direct instantiation
            return self.target_type(**raw_config)
            
        except Exception as e:
            validation_issues.append(ValidationIssue(
                path="root",
                severity=ValidationSeverity.ERROR,
                message=f"Failed to create {self.target_type.__name__} from TOML: {e}",
                suggestion="Check TOML structure matches target configuration schema"
            ))
            raise ConfigurationError(f"Failed to create configuration: {e}")


class DictConfigAdapter(EnhancedConfigAdapter):
    """Adapter for Python dictionary configurations."""
    
    def get_supported_source_types(self) -> List[ConfigSourceType]:
        """Get supported source types."""
        return [ConfigSourceType.DICT]
    
    def can_handle_source(self, source: Any, context: Optional[ConfigurationContext] = None) -> bool:
        """Check if adapter can handle the source."""
        return isinstance(source, dict)
    
    def _load_raw_config(self, source: Any, context: ConfigurationContext) -> Dict[str, Any]:
        """Load raw configuration from dictionary source."""
        if not isinstance(source, dict):
            raise ConfigurationError(f"Expected dictionary, got {type(source).__name__}")
        
        # Deep copy to avoid modifying original
        import copy
        return copy.deepcopy(source)
    
    def _create_target_config(
        self,
        raw_config: Dict[str, Any],
        context: ConfigurationContext,
        validation_issues: List[ValidationIssue]
    ) -> T:
        """Create target configuration from dictionary data."""
        try:
            # Check if target type has from_dict method
            if hasattr(self.target_type, 'from_dict'):
                return self.target_type.from_dict(raw_config)
            
            # Try direct instantiation
            return self.target_type(**raw_config)
            
        except Exception as e:
            validation_issues.append(ValidationIssue(
                path="root",
                severity=ValidationSeverity.ERROR,
                message=f"Failed to create {self.target_type.__name__} from dictionary: {e}",
                suggestion="Check dictionary structure matches target configuration schema"
            ))
            raise ConfigurationError(f"Failed to create configuration: {e}")


class EnvironmentConfigAdapter(EnhancedConfigAdapter):
    """Adapter for environment variable based configurations."""
    
    def __init__(
        self,
        target_type: Type[T],
        prefix: Optional[str] = None,
        separator: str = "__",
        enable_interpolation: bool = True,
        enable_validation: bool = True,
        strict_mode: bool = False
    ):
        """Initialize environment config adapter.
        
        Args:
            target_type: Target configuration type
            prefix: Environment variable prefix (e.g., 'APP_')
            separator: Separator for nested keys (e.g., '__')
            enable_interpolation: Whether to enable environment variable interpolation
            enable_validation: Whether to enable validation
            strict_mode: Whether to fail fast on validation errors
        """
        super().__init__(target_type, enable_interpolation, enable_validation, strict_mode)
        self.prefix = prefix
        self.separator = separator
    
    def get_supported_source_types(self) -> List[ConfigSourceType]:
        """Get supported source types."""
        return [ConfigSourceType.ENV_VARS]
    
    def can_handle_source(self, source: Any, context: Optional[ConfigurationContext] = None) -> bool:
        """Check if adapter can handle the source."""
        # Environment adapter handles environment variables or explicit ENV_VARS context
        return (source is None or 
                (context and context.source_type == ConfigSourceType.ENV_VARS))
    
    def _load_raw_config(self, source: Any, context: ConfigurationContext) -> Dict[str, Any]:
        """Load raw configuration from environment variables."""
        config = {}
        
        # Get environment variables with optional prefix filtering
        env_vars = {}
        for key, value in os.environ.items():
            if self.prefix:
                if key.startswith(self.prefix):
                    # Remove prefix
                    clean_key = key[len(self.prefix):]
                    env_vars[clean_key] = value
            else:
                env_vars[key] = value
        
        # Convert flat environment variables to nested dict
        for key, value in env_vars.items():
            self._set_nested_value(config, key, value)
        
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], key: str, value: str) -> None:
        """Set nested configuration value from flat environment key."""
        # Convert key to lowercase and split by separator
        parts = key.lower().split(self.separator)
        
        current = config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                # Key conflict - convert to dict
                current[part] = {'value': current[part]}
            current = current[part]
        
        # Set final value with type conversion
        final_key = parts[-1]
        current[final_key] = self._convert_env_value(value)
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate Python type."""
        # Handle common patterns
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        elif value.lower() in ('false', 'no', '0', 'off'):
            return False
        elif value.lower() in ('null', 'none', ''):
            return None
        
        # Try numeric conversion
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Try JSON parsing for complex types
        try:
            import json
            return json.loads(value)
        except (ValueError, json.JSONDecodeError):
            pass
        
        # Return as string
        return value
    
    def _create_target_config(
        self,
        raw_config: Dict[str, Any],
        context: ConfigurationContext,
        validation_issues: List[ValidationIssue]
    ) -> T:
        """Create target configuration from environment variables."""
        try:
            # Check if target type has from_env method
            if hasattr(self.target_type, 'from_env'):
                return self.target_type.from_env(raw_config)
            
            # Check if target type has from_dict method
            if hasattr(self.target_type, 'from_dict'):
                return self.target_type.from_dict(raw_config)
            
            # Try direct instantiation
            return self.target_type(**raw_config)
            
        except Exception as e:
            validation_issues.append(ValidationIssue(
                path="root",
                severity=ValidationSeverity.ERROR,
                message=f"Failed to create {self.target_type.__name__} from environment: {e}",
                suggestion="Check environment variable names and values match configuration schema"
            ))
            raise ConfigurationError(f"Failed to create configuration: {e}")


class RemoteConfigAdapter(EnhancedConfigAdapter):
    """Adapter for remote configuration URLs."""
    
    def __init__(
        self,
        target_type: Type[T],
        enable_interpolation: bool = True,
        enable_validation: bool = True,
        strict_mode: bool = False,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None
    ):
        """Initialize remote config adapter.
        
        Args:
            target_type: Target configuration type
            enable_interpolation: Whether to enable environment variable interpolation
            enable_validation: Whether to enable validation
            strict_mode: Whether to fail fast on validation errors
            timeout: Request timeout in seconds
            headers: Optional HTTP headers
        """
        super().__init__(target_type, enable_interpolation, enable_validation, strict_mode)
        self.timeout = timeout
        self.headers = headers or {}
    
    def get_supported_source_types(self) -> List[ConfigSourceType]:
        """Get supported source types."""
        return [ConfigSourceType.REMOTE_URL]
    
    def can_handle_source(self, source: Any, context: Optional[ConfigurationContext] = None) -> bool:
        """Check if adapter can handle the source."""
        if isinstance(source, (str, Path)):
            source_str = str(source)
            parsed = urlparse(source_str)
            return parsed.scheme in ('http', 'https')
        return False
    
    def _load_raw_config(self, source: Any, context: ConfigurationContext) -> Dict[str, Any]:
        """Load raw configuration from remote URL."""
        try:
            url = str(source)
            context.source_path = url
            
            # Create request
            from urllib.request import Request, urlopen
            
            request = Request(url, headers=self.headers)
            
            # Fetch content
            with urlopen(request, timeout=self.timeout) as response:
                content = response.read().decode('utf-8')
                content_type = response.headers.get('content-type', '').lower()
            
            # Determine format and parse
            if 'application/json' in content_type or url.endswith('.json'):
                config = json.loads(content)
            elif 'application/x-yaml' in content_type or url.endswith(('.yaml', '.yml')):
                import yaml
                config = yaml.safe_load(content)
            elif url.endswith('.toml'):
                import tomli
                config = tomli.loads(content)
            else:
                # Try to detect format
                content = content.strip()
                if content.startswith('{'):
                    config = json.loads(content)
                elif content.startswith('---') or ':' in content:
                    import yaml
                    config = yaml.safe_load(content)
                else:
                    raise ConfigurationError(f"Unable to determine configuration format for URL: {url}")
            
            if not isinstance(config, dict):
                raise ConfigurationError(f"Remote configuration must be a dictionary, got {type(config).__name__}")
            
            return config
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load remote configuration from {source}: {e}")
    
    def _create_target_config(
        self,
        raw_config: Dict[str, Any],
        context: ConfigurationContext,
        validation_issues: List[ValidationIssue]
    ) -> T:
        """Create target configuration from remote data."""
        try:
            # Check if target type has from_remote method
            if hasattr(self.target_type, 'from_remote'):
                return self.target_type.from_remote(raw_config)
            
            # Check if target type has from_dict method
            if hasattr(self.target_type, 'from_dict'):
                return self.target_type.from_dict(raw_config)
            
            # Try direct instantiation
            return self.target_type(**raw_config)
            
        except Exception as e:
            validation_issues.append(ValidationIssue(
                path="root",
                severity=ValidationSeverity.ERROR,
                message=f"Failed to create {self.target_type.__name__} from remote config: {e}",
                suggestion="Check remote configuration structure matches target schema"
            ))
            raise ConfigurationError(f"Failed to create configuration: {e}")


# Register built-in adapters
register_adapter("yaml", YAMLConfigAdapter)
register_adapter("json", JSONConfigAdapter)
register_adapter("toml", TOMLConfigAdapter)
register_adapter("dict", DictConfigAdapter)
register_adapter("env", EnvironmentConfigAdapter)
register_adapter("remote", RemoteConfigAdapter)