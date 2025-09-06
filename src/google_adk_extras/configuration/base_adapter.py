"""Enhanced Configuration Adapter Base Classes.

This module provides the foundation for flexible configuration architecture
supporting multiple input formats through a clean adapter pattern.
"""

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from pathlib import Path

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ConfigSourceType(Enum):
    """Configuration source types."""
    YAML_FILE = auto()
    JSON_FILE = auto()
    TOML_FILE = auto()
    DICT = auto()
    ENV_VARS = auto()
    REMOTE_URL = auto()
    CUSTOM = auto()


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Configuration validation issue."""
    
    path: str
    """Configuration path where issue occurred."""
    
    severity: ValidationSeverity
    """Severity level of the issue."""
    
    message: str
    """Human-readable description of the issue."""
    
    suggestion: Optional[str] = None
    """Optional suggestion for fixing the issue."""
    
    source_location: Optional[str] = None
    """Optional source file/line information."""


@dataclass
class ConfigurationContext:
    """Context for configuration processing."""
    
    source_type: ConfigSourceType
    """Type of configuration source."""
    
    source_path: Optional[str] = None
    """Path to source file or URL."""
    
    environment: Optional[str] = None
    """Environment context (dev, prod, test)."""
    
    interpolation_enabled: bool = True
    """Whether environment variable interpolation is enabled."""
    
    validation_enabled: bool = True
    """Whether validation is enabled."""
    
    strict_mode: bool = False
    """Whether to fail fast on validation errors."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional context metadata."""


@dataclass
class AdapterResult:
    """Result of configuration adaptation."""
    
    config: Any
    """The adapted configuration object."""
    
    validation_issues: List[ValidationIssue] = field(default_factory=list)
    """List of validation issues found."""
    
    context: Optional[ConfigurationContext] = None
    """Configuration context used."""
    
    processing_time: float = 0.0
    """Time taken to process configuration."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional result metadata."""
    
    def has_errors(self) -> bool:
        """Check if result has validation errors."""
        return any(issue.severity == ValidationSeverity.ERROR 
                  for issue in self.validation_issues)
    
    def has_warnings(self) -> bool:
        """Check if result has validation warnings."""
        return any(issue.severity == ValidationSeverity.WARNING 
                  for issue in self.validation_issues)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get validation issues by severity."""
        return [issue for issue in self.validation_issues if issue.severity == severity]


class EnhancedConfigAdapter(ABC):
    """Enhanced base class for configuration adapters.
    
    Provides common functionality:
    - Environment variable interpolation
    - Validation framework integration
    - Error reporting and suggestions
    - Performance monitoring
    - Context-aware processing
    """
    
    def __init__(
        self,
        target_type: Type[T],
        enable_interpolation: bool = True,
        enable_validation: bool = True,
        strict_mode: bool = False
    ):
        """Initialize enhanced configuration adapter.
        
        Args:
            target_type: Target configuration class to adapt to
            enable_interpolation: Whether to enable environment variable interpolation
            enable_validation: Whether to enable validation
            strict_mode: Whether to fail fast on validation errors
        """
        self.target_type = target_type
        self.enable_interpolation = enable_interpolation
        self.enable_validation = enable_validation
        self.strict_mode = strict_mode
        self._interpolation_cache: Dict[str, str] = {}
        
        logger.debug(f"Initialized {self.__class__.__name__} for {target_type.__name__}")
    
    @abstractmethod
    def get_supported_source_types(self) -> List[ConfigSourceType]:
        """Get list of supported configuration source types."""
        pass
    
    @abstractmethod
    def can_handle_source(self, source: Any, context: Optional[ConfigurationContext] = None) -> bool:
        """Check if adapter can handle the given configuration source.
        
        Args:
            source: Configuration source to check
            context: Optional configuration context
            
        Returns:
            bool: True if adapter can handle the source
        """
        pass
    
    @abstractmethod
    def _load_raw_config(self, source: Any, context: ConfigurationContext) -> Dict[str, Any]:
        """Load raw configuration data from source.
        
        Args:
            source: Configuration source
            context: Configuration context
            
        Returns:
            Dict[str, Any]: Raw configuration data
            
        Raises:
            ConfigurationError: If source cannot be loaded
        """
        pass
    
    def adapt(self, source: Any, context: Optional[ConfigurationContext] = None) -> AdapterResult:
        """Adapt configuration from source to target type.
        
        Args:
            source: Configuration source
            context: Optional configuration context
            
        Returns:
            AdapterResult: Adaptation result with config and validation info
            
        Raises:
            ConfigurationError: If adaptation fails in strict mode
        """
        import time
        start_time = time.time()
        
        # Create default context if not provided
        if context is None:
            context = ConfigurationContext(
                source_type=self._detect_source_type(source),
                interpolation_enabled=self.enable_interpolation,
                validation_enabled=self.enable_validation,
                strict_mode=self.strict_mode
            )
        
        validation_issues: List[ValidationIssue] = []
        
        try:
            # Load raw configuration
            raw_config = self._load_raw_config(source, context)
            
            # Apply environment variable interpolation
            if context.interpolation_enabled:
                raw_config = self._apply_interpolation(raw_config, context, validation_issues)
            
            # Create target configuration
            config = self._create_target_config(raw_config, context, validation_issues)
            
            # Perform validation
            if context.validation_enabled:
                self._validate_config(config, raw_config, context, validation_issues)
            
            # Create result
            result = AdapterResult(
                config=config,
                validation_issues=validation_issues,
                context=context,
                processing_time=time.time() - start_time
            )
            
            # Handle strict mode errors
            if context.strict_mode and result.has_errors():
                error_messages = [issue.message for issue in result.get_issues_by_severity(ValidationSeverity.ERROR)]
                raise ConfigurationError(f"Configuration validation failed: {'; '.join(error_messages)}")
            
            logger.info(f"Successfully adapted configuration from {context.source_type.name} "
                       f"({len(validation_issues)} issues, {result.processing_time:.3f}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"Configuration adaptation failed: {e}")
            
            if context.strict_mode:
                raise ConfigurationError(f"Failed to adapt configuration: {e}") from e
            
            # Return error result in non-strict mode
            validation_issues.append(ValidationIssue(
                path="root",
                severity=ValidationSeverity.ERROR,
                message=f"Configuration adaptation failed: {e}",
                suggestion="Check configuration format and syntax"
            ))
            
            return AdapterResult(
                config=None,
                validation_issues=validation_issues,
                context=context,
                processing_time=time.time() - start_time
            )
    
    def _detect_source_type(self, source: Any) -> ConfigSourceType:
        """Detect configuration source type."""
        if isinstance(source, dict):
            return ConfigSourceType.DICT
        elif isinstance(source, (str, Path)):
            source_str = str(source)
            if source_str.startswith(('http://', 'https://')):
                return ConfigSourceType.REMOTE_URL
            elif source_str.endswith('.yaml') or source_str.endswith('.yml'):
                return ConfigSourceType.YAML_FILE
            elif source_str.endswith('.json'):
                return ConfigSourceType.JSON_FILE
            elif source_str.endswith('.toml'):
                return ConfigSourceType.TOML_FILE
        
        return ConfigSourceType.CUSTOM
    
    def _apply_interpolation(
        self, 
        config: Dict[str, Any], 
        context: ConfigurationContext,
        validation_issues: List[ValidationIssue]
    ) -> Dict[str, Any]:
        """Apply environment variable interpolation to configuration."""
        try:
            from .interpolation import EnvironmentInterpolator
            interpolator = EnvironmentInterpolator()
            return interpolator.interpolate(config, context, validation_issues)
        except ImportError:
            # Graceful fallback if interpolation module not available
            return config
    
    @abstractmethod
    def _create_target_config(
        self, 
        raw_config: Dict[str, Any], 
        context: ConfigurationContext,
        validation_issues: List[ValidationIssue]
    ) -> T:
        """Create target configuration from raw config data.
        
        Args:
            raw_config: Raw configuration data
            context: Configuration context
            validation_issues: List to append validation issues to
            
        Returns:
            T: Target configuration instance
        """
        pass
    
    def _validate_config(
        self,
        config: T,
        raw_config: Dict[str, Any],
        context: ConfigurationContext,
        validation_issues: List[ValidationIssue]
    ) -> None:
        """Validate the created configuration.
        
        Args:
            config: Created configuration instance
            raw_config: Original raw configuration data
            context: Configuration context
            validation_issues: List to append validation issues to
        """
        # Default validation - subclasses can override
        if hasattr(config, 'model_validate'):
            try:
                # Pydantic validation
                config.model_validate(config.model_dump())
            except Exception as e:
                validation_issues.append(ValidationIssue(
                    path="model_validation",
                    severity=ValidationSeverity.ERROR,
                    message=f"Pydantic validation failed: {e}",
                    suggestion="Check configuration values and types"
                ))
    
    def clear_interpolation_cache(self) -> None:
        """Clear environment variable interpolation cache."""
        self._interpolation_cache.clear()
        logger.debug("Cleared interpolation cache")


class ConfigurationError(Exception):
    """Configuration processing error."""
    
    def __init__(self, message: str, validation_issues: Optional[List[ValidationIssue]] = None):
        super().__init__(message)
        self.validation_issues = validation_issues or []


# Registry for configuration adapters
_adapter_registry: Dict[str, Type[EnhancedConfigAdapter]] = {}


def register_adapter(name: str, adapter_class: Type[EnhancedConfigAdapter]) -> None:
    """Register a configuration adapter.
    
    Args:
        name: Name to register adapter under
        adapter_class: Adapter class to register
    """
    _adapter_registry[name] = adapter_class
    logger.debug(f"Registered configuration adapter: {name}")


def get_adapter(name: str) -> Optional[Type[EnhancedConfigAdapter]]:
    """Get registered configuration adapter by name.
    
    Args:
        name: Name of adapter to retrieve
        
    Returns:
        Type[EnhancedConfigAdapter]: Adapter class or None if not found
    """
    return _adapter_registry.get(name)


def list_adapters() -> List[str]:
    """List all registered adapter names.
    
    Returns:
        List[str]: List of registered adapter names
    """
    return list(_adapter_registry.keys())