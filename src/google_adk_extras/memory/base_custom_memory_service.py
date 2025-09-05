"""Base class for custom memory services."""

from abc import abstractmethod
from typing import TYPE_CHECKING

from google.adk.memory.base_memory_service import BaseMemoryService

if TYPE_CHECKING:
    from google.adk.sessions.session import Session


class BaseCustomMemoryService(BaseMemoryService):
    """Base class for custom memory services with common functionality.

    This abstract base class provides a foundation for implementing custom
    memory services with automatic initialization and cleanup handling.
    """

    def __init__(self):
        """Initialize the base custom memory service."""
        super().__init__()
        self._initialized = False

    @abstractmethod
    async def _add_session_to_memory_impl(self, session: "Session") -> None:
        """Implementation of adding a session to memory.
        
        Args:
            session: The session to add to memory.
            
        Raises:
            RuntimeError: If adding the session to memory fails.
        """

    @abstractmethod
    async def _search_memory_impl(
        self, *, app_name: str, user_id: str, query: str
    ) -> "SearchMemoryResponse":
        """Implementation of searching memory.
        
        Args:
            app_name: The name of the application.
            user_id: The id of the user.
            query: The query to search for.
            
        Returns:
            A SearchMemoryResponse containing the matching memories.
            
        Raises:
            RuntimeError: If searching memory fails.
        """

    async def add_session_to_memory(self, session: "Session") -> None:
        """Add a session to the memory service.
        
        Args:
            session: The session to add.
            
        Raises:
            RuntimeError: If adding the session to memory fails.
        """
        if not self._initialized:
            await self.initialize()
        await self._add_session_to_memory_impl(session)

    async def search_memory(
        self, *, app_name: str, user_id: str, query: str
    ) -> "SearchMemoryResponse":
        """Search for sessions that match the query.
        
        Args:
            app_name: The name of the application.
            user_id: The id of the user.
            query: The query to search for.
            
        Returns:
            A SearchMemoryResponse containing the matching memories.
            
        Raises:
            RuntimeError: If searching memory fails.
        """
        if not self._initialized:
            await self.initialize()
        return await self._search_memory_impl(
            app_name=app_name, user_id=user_id, query=query
        )

    async def initialize(self) -> None:
        """Initialize the memory service.
        
        Raises:
            RuntimeError: If initialization fails.
        """
        if not self._initialized:
            await self._initialize_impl()
            self._initialized = True

    async def cleanup(self) -> None:
        """Clean up the memory service.
        
        Raises:
            RuntimeError: If cleanup fails.
        """
        if self._initialized:
            await self._cleanup_impl()
            self._initialized = False

    @abstractmethod
    async def _initialize_impl(self) -> None:
        """Implementation of initialization.
        
        Raises:
            RuntimeError: If initialization fails.
        """

    @abstractmethod
    async def _cleanup_impl(self) -> None:
        """Implementation of cleanup.
        
        Raises:
            RuntimeError: If cleanup fails.
        """