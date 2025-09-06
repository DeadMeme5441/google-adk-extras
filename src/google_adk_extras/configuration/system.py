"""Enhanced Configuration System.

This module provides a unified configuration system that automatically
detects and adapts multiple configuration formats using the adapter pattern.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from .base_adapter import (
    EnhancedConfigAdapter, 
    ConfigSourceType, 
    ConfigurationContext,
    AdapterResult,
    ValidationIssue,
    ValidationSeverity,
    ConfigurationError,
    get_adapter,
    list_adapters
)
from .adapters import (
    YAMLConfigAdapter,
    JSONConfigAdapter,
    TOMLConfigAdapter,
    DictConfigAdapter,
    EnvironmentConfigAdapter,
    RemoteConfigAdapter
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ConfigurationSystem:
    """Enhanced configuration system with automatic format detection.
    
    Provides a unified API for loading configurations from multiple sources:
    - YAML files and strings
    - JSON files and strings  
    - TOML files and strings
    - Python dictionaries
    - Environment variables
    - Remote URLs
    - Custom adapters
    
    Features:
    - Automatic format detection
    - Environment variable interpolation
    - Comprehensive validation and error reporting
    - Performance monitoring
    - Extensible adapter architecture
    """
    
    def __init__(
        self,
        enable_interpolation: bool = True,
        enable_validation: bool = True,
        strict_mode: bool = False,
        default_adapters: bool = True
    ):
        """Initialize configuration system.
        
        Args:
            enable_interpolation: Whether to enable environment variable interpolation
            enable_validation: Whether to enable validation
            strict_mode: Whether to fail fast on validation errors
            default_adapters: Whether to register default adapters
        """
        self.enable_interpolation = enable_interpolation
        self.enable_validation = enable_validation
        self.strict_mode = strict_mode
        
        self._adapters: Dict[str, Type[EnhancedConfigAdapter]] = {}
        self._adapter_instances: Dict[str, EnhancedConfigAdapter] = {}
        
        if default_adapters:
            self._register_default_adapters()
        
        logger.debug(f"Initialized ConfigurationSystem with {len(self._adapters)} adapters")
    
    def _register_default_adapters(self) -> None:
        """Register default configuration adapters."""
        self.register_adapter("yaml", YAMLConfigAdapter)
        self.register_adapter("json", JSONConfigAdapter)
        self.register_adapter("toml", TOMLConfigAdapter)
        self.register_adapter("dict", DictConfigAdapter)
        self.register_adapter("env", EnvironmentConfigAdapter)
        self.register_adapter("remote", RemoteConfigAdapter)
    
    def register_adapter(self, name: str, adapter_class: Type[EnhancedConfigAdapter]) -> None:
        """Register a configuration adapter.
        
        Args:
            name: Name to register adapter under
            adapter_class: Adapter class to register
        """
        self._adapters[name] = adapter_class
        logger.debug(f"Registered configuration adapter: {name}")
    
    def get_adapter(self, name: str) -> Optional[Type[EnhancedConfigAdapter]]:
        """Get registered adapter by name.
        
        Args:
            name: Name of adapter to retrieve
            
        Returns:
            Type[EnhancedConfigAdapter]: Adapter class or None if not found
        """
        return self._adapters.get(name)
    
    def list_adapters(self) -> List[str]:
        """List all registered adapter names.
        
        Returns:
            List[str]: List of registered adapter names
        """
        return list(self._adapters.keys())
    
    def load_config(
        self,
        target_type: Type[T],
        source: Any,
        adapter_name: Optional[str] = None,
        context: Optional[ConfigurationContext] = None,
        **adapter_kwargs
    ) -> AdapterResult:
        """Load configuration from source using automatic or specified adapter.
        
        Args:
            target_type: Target configuration class to create
            source: Configuration source (file path, dict, string, etc.)
            adapter_name: Optional specific adapter to use
            context: Optional configuration context
            **adapter_kwargs: Additional arguments for adapter
            
        Returns:
            AdapterResult: Adapter result with config and validation info
            
        Raises:
            ConfigurationError: If no suitable adapter found or loading fails
        """
        start_time = time.time()
        
        # Create default context if not provided
        if context is None:
            context = ConfigurationContext(
                source_type=self._detect_source_type(source),
                interpolation_enabled=self.enable_interpolation,
                validation_enabled=self.enable_validation,
                strict_mode=self.strict_mode
            )
        
        # Find suitable adapter
        adapter = self._find_adapter(source, target_type, adapter_name, context, **adapter_kwargs)
        
        if not adapter:
            available_adapters = ', '.join(self.list_adapters())
            raise ConfigurationError(
                f"No suitable adapter found for source type. "
                f"Available adapters: {available_adapters}"
            )
        
        # Load configuration
        try:
            result = adapter.adapt(source, context)
            result.metadata['system_processing_time'] = time.time() - start_time
            result.metadata['adapter_used'] = adapter.__class__.__name__
            
            logger.info(f"Successfully loaded {target_type.__name__} configuration "
                       f"using {adapter.__class__.__name__} "
                       f"({len(result.validation_issues)} issues, "
                       f"{result.metadata['system_processing_time']:.3f}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration loading failed: {e}") from e
    
    def _find_adapter(
        self,
        source: Any,
        target_type: Type[T],
        adapter_name: Optional[str],
        context: ConfigurationContext,
        **adapter_kwargs
    ) -> Optional[EnhancedConfigAdapter]:
        """Find suitable adapter for source and target type."""
        
        # Use specific adapter if requested
        if adapter_name:
            if adapter_name not in self._adapters:
                raise ConfigurationError(f"Adapter '{adapter_name}' not found")
            
            adapter_class = self._adapters[adapter_name]
            return self._get_adapter_instance(adapter_class, target_type, **adapter_kwargs)
        
        # Auto-detect adapter
        for name, adapter_class in self._adapters.items():
            try:
                adapter = self._get_adapter_instance(adapter_class, target_type, **adapter_kwargs)
                if adapter.can_handle_source(source, context):
                    logger.debug(f"Auto-selected adapter: {name}")
                    return adapter
            except Exception as e:
                logger.debug(f"Adapter {name} failed source check: {e}")
                continue
        
        return None
    
    def _get_adapter_instance(
        self,
        adapter_class: Type[EnhancedConfigAdapter],
        target_type: Type[T],
        **adapter_kwargs
    ) -> EnhancedConfigAdapter:
        """Get adapter instance with caching."""
        cache_key = f"{adapter_class.__name__}:{target_type.__name__}:{hash(str(adapter_kwargs))}"
        
        if cache_key not in self._adapter_instances:
            self._adapter_instances[cache_key] = adapter_class(
                target_type=target_type,
                enable_interpolation=self.enable_interpolation,
                enable_validation=self.enable_validation,
                strict_mode=self.strict_mode,
                **adapter_kwargs
            )
        
        return self._adapter_instances[cache_key]
    
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
    
    def validate_config(
        self,
        config: Any,
        target_type: Type[T],
        context: Optional[ConfigurationContext] = None
    ) -> List[ValidationIssue]:
        """Validate configuration against target type.
        
        Args:
            config: Configuration to validate
            target_type: Target configuration type
            context: Optional configuration context
            
        Returns:
            List[ValidationIssue]: List of validation issues
        """
        validation_issues: List[ValidationIssue] = []
        
        try:
            # Basic type validation
            if not isinstance(config, target_type):
                validation_issues.append(ValidationIssue(
                    path="root",
                    severity=ValidationSeverity.ERROR,
                    message=f"Configuration is not of expected type {target_type.__name__}",
                    suggestion=f"Ensure configuration creates valid {target_type.__name__} instance"
                ))
            
            # Pydantic validation if available
            if hasattr(config, 'model_validate'):
                try:
                    config.model_validate(config.model_dump())
                except Exception as e:
                    validation_issues.append(ValidationIssue(
                        path="model_validation",
                        severity=ValidationSeverity.ERROR,
                        message=f"Pydantic validation failed: {e}",
                        suggestion="Check configuration values and types"
                    ))
            
            # Custom validation if available
            if hasattr(config, 'validate'):
                try:
                    config.validate()
                except Exception as e:
                    validation_issues.append(ValidationIssue(
                        path="custom_validation",
                        severity=ValidationSeverity.WARNING,
                        message=f"Custom validation failed: {e}",
                        suggestion="Check custom validation requirements"
                    ))
            
        except Exception as e:
            validation_issues.append(ValidationIssue(
                path="validation_system",
                severity=ValidationSeverity.ERROR,
                message=f"Validation system error: {e}",
                suggestion="Check configuration system setup"
            ))
        
        return validation_issues
    
    def clear_adapter_cache(self) -> None:
        """Clear adapter instance cache."""
        self._adapter_instances.clear()
        logger.debug("Cleared adapter instance cache")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get configuration system statistics.
        
        Returns:
            Dict[str, Any]: System statistics
        """
        return {
            'registered_adapters': len(self._adapters),
            'cached_instances': len(self._adapter_instances),
            'adapter_names': list(self._adapters.keys()),
            'interpolation_enabled': self.enable_interpolation,
            'validation_enabled': self.enable_validation,
            'strict_mode': self.strict_mode
        }


# Global configuration system instance
_global_config_system: Optional[ConfigurationSystem] = None


def get_config_system(
    enable_interpolation: bool = True,
    enable_validation: bool = True,
    strict_mode: bool = False
) -> ConfigurationSystem:
    """Get global configuration system instance.
    
    Args:
        enable_interpolation: Whether to enable environment variable interpolation
        enable_validation: Whether to enable validation
        strict_mode: Whether to fail fast on validation errors
        
    Returns:
        ConfigurationSystem: Global configuration system instance
    """
    global _global_config_system
    
    if _global_config_system is None:
        _global_config_system = ConfigurationSystem(
            enable_interpolation=enable_interpolation,
            enable_validation=enable_validation,
            strict_mode=strict_mode
        )
    
    return _global_config_system


def load_config(
    target_type: Type[T],
    source: Any,
    adapter_name: Optional[str] = None,
    context: Optional[ConfigurationContext] = None,
    **adapter_kwargs
) -> AdapterResult:
    """Convenience function to load configuration using global system.
    
    Args:
        target_type: Target configuration class to create
        source: Configuration source (file path, dict, string, etc.)
        adapter_name: Optional specific adapter to use
        context: Optional configuration context
        **adapter_kwargs: Additional arguments for adapter
        
    Returns:
        AdapterResult: Adapter result with config and validation info
    """
    config_system = get_config_system()
    return config_system.load_config(
        target_type=target_type,
        source=source,
        adapter_name=adapter_name,
        context=context,
        **adapter_kwargs
    )


def load_enhanced_run_config(
    source: Any,
    adapter_name: Optional[str] = None,
    **adapter_kwargs
) -> AdapterResult:
    """Convenience function to load EnhancedRunConfig.
    
    Args:
        source: Configuration source
        adapter_name: Optional specific adapter to use
        **adapter_kwargs: Additional arguments for adapter
        
    Returns:
        AdapterResult: Adapter result with EnhancedRunConfig
    """
    from ..runners.config import EnhancedRunConfig
    
    return load_config(
        target_type=EnhancedRunConfig,
        source=source,
        adapter_name=adapter_name,
        **adapter_kwargs
    )


def reset_config_system() -> None:
    """Reset global configuration system (primarily for testing)."""
    global _global_config_system
    _global_config_system = None