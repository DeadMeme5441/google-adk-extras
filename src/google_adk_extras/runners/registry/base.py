"""Enhanced Registry Base Infrastructure.

This module provides the foundation for all enhanced registries with
event system, health monitoring, caching, and lifecycle management.
"""

import asyncio
import logging
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Generic
from weakref import WeakSet

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RegistryEventType(Enum):
    """Registry event types."""
    REGISTERED = auto()
    UNREGISTERED = auto() 
    UPDATED = auto()
    HEALTH_CHANGED = auto()
    STARTUP = auto()
    SHUTDOWN = auto()


class RegistryHealthStatus(Enum):
    """Health status for registry items."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class RegistryEvent:
    """Registry event data."""
    
    event_type: RegistryEventType
    """Type of registry event."""
    
    registry_name: str
    """Name of the registry that generated the event."""
    
    item_name: str
    """Name of the item involved in the event."""
    
    item: Optional[Any] = None
    """The item itself (for registration/update events)."""
    
    timestamp: float = field(default_factory=time.time)
    """Timestamp when event occurred."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional event metadata."""


@dataclass
class RegistryHealth:
    """Health information for a registry item."""
    
    item_name: str
    """Name of the item."""
    
    status: RegistryHealthStatus = RegistryHealthStatus.UNKNOWN
    """Current health status."""
    
    last_checked: float = field(default_factory=time.time)
    """Timestamp of last health check."""
    
    last_healthy: Optional[float] = None
    """Timestamp of last healthy status."""
    
    failure_count: int = 0
    """Number of consecutive failures."""
    
    details: Dict[str, Any] = field(default_factory=dict)
    """Additional health details."""
    
    def update_status(self, status: RegistryHealthStatus, details: Optional[Dict[str, Any]] = None):
        """Update health status.
        
        Args:
            status: New health status
            details: Optional additional details
        """
        old_status = self.status
        self.status = status
        self.last_checked = time.time()
        
        if status == RegistryHealthStatus.HEALTHY:
            self.last_healthy = self.last_checked
            self.failure_count = 0
        elif status == RegistryHealthStatus.UNHEALTHY:
            self.failure_count += 1
        
        if details:
            self.details.update(details)
        
        logger.debug(f"Health status changed for {self.item_name}: {old_status.value} -> {status.value}")
    
    def is_healthy(self) -> bool:
        """Check if item is currently healthy."""
        return self.status == RegistryHealthStatus.HEALTHY
    
    def is_stale(self, max_age_seconds: float = 300.0) -> bool:
        """Check if health information is stale.
        
        Args:
            max_age_seconds: Maximum age in seconds before health is considered stale
            
        Returns:
            bool: True if health information is stale
        """
        return (time.time() - self.last_checked) > max_age_seconds


class RegistryCache(Generic[T]):
    """Thread-safe cache for registry items with TTL support."""
    
    def __init__(self, default_ttl: float = 300.0):
        """Initialize registry cache.
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache: Dict[str, tuple[T, float]] = {}  # name -> (item, expiry_time)
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
        
    def get(self, key: str) -> Optional[T]:
        """Get item from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            T: Cached item or None if not found/expired
        """
        with self._lock:
            if key in self._cache:
                item, expiry = self._cache[key]
                if time.time() < expiry:
                    return item
                else:
                    # Expired, remove from cache
                    del self._cache[key]
            return None
    
    def put(self, key: str, item: T, ttl: Optional[float] = None) -> None:
        """Put item in cache with TTL.
        
        Args:
            key: Cache key
            item: Item to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl or self._default_ttl
        expiry = time.time() + ttl
        
        with self._lock:
            self._cache[key] = (item, expiry)
    
    def remove(self, key: str) -> bool:
        """Remove item from cache.
        
        Args:
            key: Cache key to remove
            
        Returns:
            bool: True if item was found and removed
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cached items."""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired items from cache.
        
        Returns:
            int: Number of expired items removed
        """
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, (_, expiry) in self._cache.items():
                if current_time >= expiry:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)


class EnhancedRegistryBase(ABC, Generic[T]):
    """Enhanced base class for all registries.
    
    Provides common functionality:
    - Event system for registry changes
    - Health monitoring for registered items
    - Caching layer for performance
    - Lifecycle management
    """
    
    def __init__(
        self,
        name: str,
        cache_ttl: float = 300.0,
        health_check_interval: float = 60.0,
        enable_events: bool = True,
        enable_caching: bool = True,
        enable_health_monitoring: bool = True
    ):
        """Initialize enhanced registry base.
        
        Args:
            name: Registry name for identification
            cache_ttl: Cache time-to-live in seconds
            health_check_interval: Health check interval in seconds
            enable_events: Whether to enable event system
            enable_caching: Whether to enable caching
            enable_health_monitoring: Whether to enable health monitoring
        """
        self.name = name
        self._lock = threading.RLock()
        
        # Event system
        self._enable_events = enable_events
        self._event_listeners: WeakSet[Callable[[RegistryEvent], None]] = WeakSet()
        
        # Caching system
        self._enable_caching = enable_caching
        self._cache: Optional[RegistryCache[T]] = None
        if enable_caching:
            self._cache = RegistryCache[T](default_ttl=cache_ttl)
        
        # Health monitoring
        self._enable_health_monitoring = enable_health_monitoring
        self._health_info: Dict[str, RegistryHealth] = {}
        self._health_check_interval = health_check_interval
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Lifecycle management
        self._is_started = False
        self._is_shutdown = False
        
        logger.debug(f"Initialized enhanced registry '{name}' (events={enable_events}, cache={enable_caching}, health={enable_health_monitoring})")
    
    async def startup(self) -> None:
        """Start the registry and background tasks."""
        if self._is_started:
            logger.warning(f"Registry '{self.name}' is already started")
            return
        
        logger.info(f"Starting enhanced registry '{self.name}'")
        
        # Start health monitoring if enabled
        if self._enable_health_monitoring and self._health_check_interval > 0:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        self._is_started = True
        
        # Emit startup event
        if self._enable_events:
            self._emit_event(RegistryEvent(
                event_type=RegistryEventType.STARTUP,
                registry_name=self.name,
                item_name="registry"
            ))
        
        logger.info(f"Enhanced registry '{self.name}' started successfully")
    
    async def shutdown(self) -> None:
        """Shutdown the registry and cleanup resources."""
        if self._is_shutdown:
            logger.warning(f"Registry '{self.name}' is already shut down")
            return
        
        logger.info(f"Shutting down enhanced registry '{self.name}'")
        
        # Stop health monitoring
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Clear cache
        if self._cache:
            self._cache.clear()
        
        self._is_shutdown = True
        self._is_started = False
        
        # Emit shutdown event
        if self._enable_events:
            self._emit_event(RegistryEvent(
                event_type=RegistryEventType.SHUTDOWN,
                registry_name=self.name,
                item_name="registry"
            ))
        
        logger.info(f"Enhanced registry '{self.name}' shut down successfully")
    
    def add_event_listener(self, listener: Callable[[RegistryEvent], None]) -> None:
        """Add event listener for registry events.
        
        Args:
            listener: Callable that will receive RegistryEvent objects
        """
        if self._enable_events:
            self._event_listeners.add(listener)
            logger.debug(f"Added event listener to registry '{self.name}'")
    
    def remove_event_listener(self, listener: Callable[[RegistryEvent], None]) -> None:
        """Remove event listener.
        
        Args:
            listener: Listener to remove
        """
        if self._enable_events:
            self._event_listeners.discard(listener)
            logger.debug(f"Removed event listener from registry '{self.name}'")
    
    def _emit_event(self, event: RegistryEvent) -> None:
        """Emit registry event to all listeners.
        
        Args:
            event: Event to emit
        """
        if not self._enable_events:
            return
        
        # Create a copy of listeners to avoid issues with concurrent modification
        listeners = list(self._event_listeners)
        
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in event listener for registry '{self.name}': {e}")
    
    def get_health_info(self, item_name: str) -> Optional[RegistryHealth]:
        """Get health information for an item.
        
        Args:
            item_name: Name of item to get health info for
            
        Returns:
            RegistryHealth: Health information or None if not found
        """
        if not self._enable_health_monitoring:
            return None
        
        with self._lock:
            return self._health_info.get(item_name)
    
    def get_all_health_info(self) -> Dict[str, RegistryHealth]:
        """Get health information for all items.
        
        Returns:
            Dict[str, RegistryHealth]: Mapping of item names to health info
        """
        if not self._enable_health_monitoring:
            return {}
        
        with self._lock:
            return self._health_info.copy()
    
    def update_health_status(
        self, 
        item_name: str, 
        status: RegistryHealthStatus,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update health status for an item.
        
        Args:
            item_name: Name of item to update
            status: New health status
            details: Optional additional details
        """
        if not self._enable_health_monitoring:
            return
        
        with self._lock:
            if item_name not in self._health_info:
                self._health_info[item_name] = RegistryHealth(item_name=item_name)
            
            old_status = self._health_info[item_name].status
            self._health_info[item_name].update_status(status, details)
        
        # Emit health change event if status changed
        if self._enable_events and old_status != status:
            self._emit_event(RegistryEvent(
                event_type=RegistryEventType.HEALTH_CHANGED,
                registry_name=self.name,
                item_name=item_name,
                metadata={
                    'old_status': old_status.value,
                    'new_status': status.value,
                    'details': details or {}
                }
            ))
    
    def _remove_health_info(self, item_name: str) -> None:
        """Remove health information for an item.
        
        Args:
            item_name: Name of item to remove health info for
        """
        if not self._enable_health_monitoring:
            return
        
        with self._lock:
            if item_name in self._health_info:
                del self._health_info[item_name]
    
    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        logger.debug(f"Started health check loop for registry '{self.name}'")
        
        try:
            while not self._is_shutdown:
                await asyncio.sleep(self._health_check_interval)
                
                if self._is_shutdown:
                    break
                
                try:
                    await self._perform_health_checks()
                except Exception as e:
                    logger.error(f"Error during health checks for registry '{self.name}': {e}")
        
        except asyncio.CancelledError:
            logger.debug(f"Health check loop cancelled for registry '{self.name}'")
        except Exception as e:
            logger.error(f"Health check loop error for registry '{self.name}': {e}")
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all registered items."""
        # Get all items to check
        items_to_check = self._get_items_for_health_check()
        
        for item_name, item in items_to_check.items():
            try:
                status = await self._check_item_health(item_name, item)
                self.update_health_status(item_name, status)
            except Exception as e:
                logger.warning(f"Health check failed for {item_name} in registry '{self.name}': {e}")
                self.update_health_status(
                    item_name, 
                    RegistryHealthStatus.UNHEALTHY,
                    {'error': str(e)}
                )
        
        # Clean up health info for items that no longer exist
        with self._lock:
            existing_items = set(items_to_check.keys())
            health_items = set(self._health_info.keys())
            removed_items = health_items - existing_items
            
            for item_name in removed_items:
                del self._health_info[item_name]
                logger.debug(f"Removed stale health info for {item_name}")
    
    @abstractmethod
    def _get_items_for_health_check(self) -> Dict[str, T]:
        """Get all items that should be health checked.
        
        Returns:
            Dict[str, T]: Mapping of item names to items
        """
        pass
    
    async def _check_item_health(self, item_name: str, item: T) -> RegistryHealthStatus:
        """Check health of a specific item.
        
        Args:
            item_name: Name of the item
            item: The item to check
            
        Returns:
            RegistryHealthStatus: Health status of the item
        """
        # Default implementation - subclasses can override
        return RegistryHealthStatus.HEALTHY
    
    def _get_from_cache(self, key: str) -> Optional[T]:
        """Get item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            T: Cached item or None
        """
        if not self._enable_caching or not self._cache:
            return None
        
        return self._cache.get(key)
    
    def _put_in_cache(self, key: str, item: T, ttl: Optional[float] = None) -> None:
        """Put item in cache.
        
        Args:
            key: Cache key
            item: Item to cache
            ttl: Optional TTL override
        """
        if not self._enable_caching or not self._cache:
            return
        
        self._cache.put(key, item, ttl)
    
    def _remove_from_cache(self, key: str) -> None:
        """Remove item from cache.
        
        Args:
            key: Cache key to remove
        """
        if not self._enable_caching or not self._cache:
            return
        
        self._cache.remove(key)
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics.
        
        Returns:
            Dict[str, Any]: Registry statistics
        """
        stats = {
            'name': self.name,
            'started': self._is_started,
            'shutdown': self._is_shutdown,
            'events_enabled': self._enable_events,
            'caching_enabled': self._enable_caching,
            'health_monitoring_enabled': self._enable_health_monitoring,
        }
        
        if self._enable_caching and self._cache:
            stats['cache_size'] = self._cache.size()
        
        if self._enable_health_monitoring:
            health_summary = {'healthy': 0, 'degraded': 0, 'unhealthy': 0, 'unknown': 0}
            
            with self._lock:
                for health_info in self._health_info.values():
                    health_summary[health_info.status.value] += 1
            
            stats['health_summary'] = health_summary
            stats['total_monitored_items'] = len(self._health_info)
        
        return stats
    
    def __repr__(self) -> str:
        """String representation of registry."""
        return f"{self.__class__.__name__}(name='{self.name}', started={self._is_started})"