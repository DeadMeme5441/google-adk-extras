"""Environment Variable Interpolation Utilities.

This module provides standalone environment variable interpolation services
for configuration values with comprehensive validation and error reporting.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Pattern, Tuple, Union

from .base_adapter import ValidationIssue, ValidationSeverity, ConfigurationContext

logger = logging.getLogger(__name__)


class InterpolationSyntax(Enum):
    """Environment variable interpolation syntax styles."""
    SHELL = auto()          # ${VAR} or ${VAR:-default}
    PYTHON = auto()         # {VAR} or {VAR:default}
    ANSIBLE = auto()        # {{ VAR }} or {{ VAR | default('value') }}
    MUSTACHE = auto()       # {{VAR}} or {{VAR}}
    CUSTOM = auto()         # Custom pattern


@dataclass
class InterpolationPattern:
    """Environment variable interpolation pattern."""
    
    syntax: InterpolationSyntax
    """Syntax style for this pattern."""
    
    regex: Pattern[str]
    """Compiled regex pattern for matching."""
    
    group_names: List[str]
    """Names of regex capture groups."""
    
    supports_defaults: bool = True
    """Whether this pattern supports default values."""
    
    example: str = ""
    """Example usage of this pattern."""


@dataclass
class InterpolationConfig:
    """Configuration for environment variable interpolation."""
    
    enabled_syntaxes: List[InterpolationSyntax] = field(default_factory=lambda: [
        InterpolationSyntax.SHELL,
        InterpolationSyntax.PYTHON
    ])
    """List of enabled interpolation syntaxes."""
    
    allow_undefined: bool = False
    """Whether to allow undefined environment variables (returns empty string)."""
    
    case_sensitive: bool = True
    """Whether environment variable names are case-sensitive."""
    
    recursive_interpolation: bool = True
    """Whether to recursively interpolate values that contain more variables."""
    
    max_recursion_depth: int = 10
    """Maximum recursion depth for nested interpolation."""
    
    prefix_filter: Optional[str] = None
    """Optional prefix filter for environment variables (e.g., 'APP_')."""
    
    custom_patterns: List[InterpolationPattern] = field(default_factory=list)
    """Custom interpolation patterns to use."""
    
    validation_enabled: bool = True
    """Whether to perform validation during interpolation."""


class EnvironmentInterpolator:
    """Standalone environment variable interpolation service.
    
    Provides comprehensive environment variable interpolation with:
    - Multiple syntax support (shell, python, ansible, etc.)
    - Default value handling
    - Recursive interpolation
    - Validation and error reporting
    - Performance optimization through caching
    """
    
    # Built-in interpolation patterns
    PATTERNS: Dict[InterpolationSyntax, InterpolationPattern] = {
        InterpolationSyntax.SHELL: InterpolationPattern(
            syntax=InterpolationSyntax.SHELL,
            regex=re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*?)(?::[-]?([^}]*))?\}'),
            group_names=['var_name', 'default_value'],
            supports_defaults=True,
            example='${DATABASE_URL:-postgresql://localhost/db}'
        ),
        InterpolationSyntax.PYTHON: InterpolationPattern(
            syntax=InterpolationSyntax.PYTHON,
            regex=re.compile(r'\{([A-Za-z_][A-Za-z0-9_]*?)(?::([^}]*))?\}'),
            group_names=['var_name', 'default_value'],
            supports_defaults=True,
            example='{DATABASE_URL:postgresql://localhost/db}'
        ),
        InterpolationSyntax.ANSIBLE: InterpolationPattern(
            syntax=InterpolationSyntax.ANSIBLE,
            regex=re.compile(r'\{\{\s*([A-Za-z_][A-Za-z0-9_]*?)\s*(?:\|\s*default\([\'"]([^\'"]*?)[\'"]\))?\s*\}\}'),
            group_names=['var_name', 'default_value'],
            supports_defaults=True,
            example='{{ DATABASE_URL | default("postgresql://localhost/db") }}'
        ),
        InterpolationSyntax.MUSTACHE: InterpolationPattern(
            syntax=InterpolationSyntax.MUSTACHE,
            regex=re.compile(r'\{\{([A-Za-z_][A-Za-z0-9_]*?)\}\}'),
            group_names=['var_name'],
            supports_defaults=False,
            example='{{DATABASE_URL}}'
        ),
    }
    
    def __init__(self, config: Optional[InterpolationConfig] = None):
        """Initialize environment interpolator.
        
        Args:
            config: Interpolation configuration (uses defaults if None)
        """
        self.config = config or InterpolationConfig()
        self._cache: Dict[str, str] = {}
        self._active_patterns: List[InterpolationPattern] = []
        
        # Build active patterns list
        self._build_active_patterns()
        
        logger.debug(f"Initialized EnvironmentInterpolator with {len(self._active_patterns)} patterns")
    
    def _build_active_patterns(self) -> None:
        """Build list of active interpolation patterns."""
        self._active_patterns = []
        
        # Add built-in patterns for enabled syntaxes
        for syntax in self.config.enabled_syntaxes:
            if syntax in self.PATTERNS:
                self._active_patterns.append(self.PATTERNS[syntax])
        
        # Add custom patterns
        self._active_patterns.extend(self.config.custom_patterns)
        
        logger.debug(f"Built {len(self._active_patterns)} active interpolation patterns")
    
    def interpolate(
        self, 
        config: Union[Dict[str, Any], str], 
        context: Optional[ConfigurationContext] = None,
        validation_issues: Optional[List[ValidationIssue]] = None
    ) -> Union[Dict[str, Any], str]:
        """Interpolate environment variables in configuration.
        
        Args:
            config: Configuration dict or string to interpolate
            context: Optional configuration context
            validation_issues: Optional list to append validation issues to
            
        Returns:
            Union[Dict[str, Any], str]: Configuration with interpolated values
        """
        validation_issues = validation_issues or []
        
        if isinstance(config, str):
            return self._interpolate_string(config, "", validation_issues)
        elif isinstance(config, dict):
            return self._interpolate_dict(config, "", validation_issues)
        elif isinstance(config, list):
            return self._interpolate_list(config, "", validation_issues)
        else:
            return config
    
    def _interpolate_string(
        self, 
        value: str, 
        path: str,
        validation_issues: List[ValidationIssue],
        depth: int = 0
    ) -> str:
        """Interpolate environment variables in a string value.
        
        Args:
            value: String value to interpolate
            path: Configuration path for error reporting
            validation_issues: List to append validation issues to
            depth: Current recursion depth
            
        Returns:
            str: String with interpolated environment variables
        """
        if depth > self.config.max_recursion_depth:
            validation_issues.append(ValidationIssue(
                path=path,
                severity=ValidationSeverity.WARNING,
                message=f"Maximum recursion depth ({self.config.max_recursion_depth}) exceeded",
                suggestion="Check for circular environment variable references"
            ))
            return value
        
        # Cache check
        cache_key = f"{value}:{depth}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        original_value = value
        
        # Apply each active pattern
        for pattern in self._active_patterns:
            value = self._apply_pattern(value, pattern, path, validation_issues, depth)
        
        # Cache result
        self._cache[cache_key] = value
        
        # Recursive interpolation if value changed and enabled
        if (self.config.recursive_interpolation and 
            value != original_value and 
            self._has_interpolation_syntax(value)):
            value = self._interpolate_string(value, path, validation_issues, depth + 1)
        
        return value
    
    def _apply_pattern(
        self,
        value: str,
        pattern: InterpolationPattern,
        path: str,
        validation_issues: List[ValidationIssue],
        depth: int
    ) -> str:
        """Apply a specific interpolation pattern to a value.
        
        Args:
            value: Value to process
            pattern: Interpolation pattern to apply
            path: Configuration path for error reporting
            validation_issues: List to append validation issues to
            depth: Current recursion depth
            
        Returns:
            str: Value with pattern applied
        """
        def replace_match(match) -> str:
            groups = match.groups()
            var_name = groups[0] if groups else ""
            default_value = groups[1] if len(groups) > 1 and groups[1] is not None else ""
            
            # Apply prefix filter if configured
            if (self.config.prefix_filter and 
                not var_name.startswith(self.config.prefix_filter)):
                return match.group(0)  # Return original match
            
            # Get environment variable value
            env_value = self._get_env_value(var_name, default_value, path, validation_issues)
            
            return env_value
        
        return pattern.regex.sub(replace_match, value)
    
    def _get_env_value(
        self,
        var_name: str,
        default_value: str,
        path: str,
        validation_issues: List[ValidationIssue]
    ) -> str:
        """Get environment variable value with validation.
        
        Args:
            var_name: Environment variable name
            default_value: Default value if variable is not set
            path: Configuration path for error reporting
            validation_issues: List to append validation issues to
            
        Returns:
            str: Environment variable value or default
        """
        # Handle case sensitivity
        actual_var_name = var_name
        if not self.config.case_sensitive:
            # Find case-insensitive match
            env_keys = list(os.environ.keys())
            matching_keys = [k for k in env_keys if k.lower() == var_name.lower()]
            if matching_keys:
                actual_var_name = matching_keys[0]
        
        # Get environment variable
        env_value = os.environ.get(actual_var_name)
        
        if env_value is not None:
            return env_value
        
        # Variable not found
        if default_value:
            if self.config.validation_enabled:
                validation_issues.append(ValidationIssue(
                    path=path,
                    severity=ValidationSeverity.INFO,
                    message=f"Environment variable '{var_name}' not found, using default value",
                    suggestion=f"Consider setting {var_name} environment variable"
                ))
            return default_value
        
        if self.config.allow_undefined:
            if self.config.validation_enabled:
                validation_issues.append(ValidationIssue(
                    path=path,
                    severity=ValidationSeverity.WARNING,
                    message=f"Environment variable '{var_name}' not found, using empty string",
                    suggestion=f"Set {var_name} environment variable or provide default value"
                ))
            return ""
        
        # Undefined variable in strict mode
        if self.config.validation_enabled:
            validation_issues.append(ValidationIssue(
                path=path,
                severity=ValidationSeverity.ERROR,
                message=f"Required environment variable '{var_name}' is not defined",
                suggestion=f"Set {var_name} environment variable or provide default value"
            ))
        
        return f"${{{var_name}}}"  # Return placeholder for undefined required vars
    
    def _interpolate_dict(
        self,
        config: Dict[str, Any],
        path: str,
        validation_issues: List[ValidationIssue]
    ) -> Dict[str, Any]:
        """Interpolate environment variables in dictionary values."""
        result = {}
        
        for key, value in config.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, str):
                result[key] = self._interpolate_string(value, current_path, validation_issues)
            elif isinstance(value, dict):
                result[key] = self._interpolate_dict(value, current_path, validation_issues)
            elif isinstance(value, list):
                result[key] = self._interpolate_list(value, current_path, validation_issues)
            else:
                result[key] = value
        
        return result
    
    def _interpolate_list(
        self,
        config: List[Any],
        path: str,
        validation_issues: List[ValidationIssue]
    ) -> List[Any]:
        """Interpolate environment variables in list values."""
        result = []
        
        for i, value in enumerate(config):
            current_path = f"{path}[{i}]"
            
            if isinstance(value, str):
                result.append(self._interpolate_string(value, current_path, validation_issues))
            elif isinstance(value, dict):
                result.append(self._interpolate_dict(value, current_path, validation_issues))
            elif isinstance(value, list):
                result.append(self._interpolate_list(value, current_path, validation_issues))
            else:
                result.append(value)
        
        return result
    
    def _has_interpolation_syntax(self, value: str) -> bool:
        """Check if value contains interpolation syntax."""
        for pattern in self._active_patterns:
            if pattern.regex.search(value):
                return True
        return False
    
    def add_custom_pattern(self, pattern: InterpolationPattern) -> None:
        """Add a custom interpolation pattern.
        
        Args:
            pattern: Custom interpolation pattern to add
        """
        self.config.custom_patterns.append(pattern)
        self._build_active_patterns()
        self.clear_cache()
        
        logger.debug(f"Added custom interpolation pattern: {pattern.example}")
    
    def clear_cache(self) -> None:
        """Clear interpolation cache."""
        self._cache.clear()
        logger.debug("Cleared interpolation cache")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Dict[str, int]: Cache statistics
        """
        return {
            'cache_size': len(self._cache),
            'active_patterns': len(self._active_patterns),
            'enabled_syntaxes': len(self.config.enabled_syntaxes),
            'custom_patterns': len(self.config.custom_patterns)
        }


def create_interpolator(
    syntax: Optional[List[InterpolationSyntax]] = None,
    allow_undefined: bool = False,
    case_sensitive: bool = True,
    recursive: bool = True
) -> EnvironmentInterpolator:
    """Create an environment interpolator with common settings.
    
    Args:
        syntax: List of enabled syntaxes (defaults to SHELL and PYTHON)
        allow_undefined: Whether to allow undefined environment variables
        case_sensitive: Whether variable names are case-sensitive
        recursive: Whether to enable recursive interpolation
        
    Returns:
        EnvironmentInterpolator: Configured interpolator
    """
    config = InterpolationConfig(
        enabled_syntaxes=syntax or [InterpolationSyntax.SHELL, InterpolationSyntax.PYTHON],
        allow_undefined=allow_undefined,
        case_sensitive=case_sensitive,
        recursive_interpolation=recursive
    )
    
    return EnvironmentInterpolator(config)


def interpolate_string(
    value: str,
    syntax: Optional[List[InterpolationSyntax]] = None,
    allow_undefined: bool = False
) -> str:
    """Convenience function to interpolate a single string.
    
    Args:
        value: String to interpolate
        syntax: List of enabled syntaxes
        allow_undefined: Whether to allow undefined environment variables
        
    Returns:
        str: Interpolated string
    """
    interpolator = create_interpolator(syntax, allow_undefined)
    return interpolator.interpolate(value)