"""Base class for custom session services."""

import abc
from typing import Any, Optional

from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.adk.sessions.base_session_service import GetSessionConfig, ListSessionsResponse


class BaseCustomSessionService(BaseSessionService, abc.ABC):
    """Base class for custom session services with common functionality."""

    def __init__(self):
        """Initialize the base custom session service."""
        super().__init__()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the session service.
        
        This method should be called before using the service to ensure
        any required setup (database connections, etc.) is complete.
        """
        if not self._initialized:
            await self._initialize_impl()
            self._initialized = True

    @abc.abstractmethod
    async def _initialize_impl(self) -> None:
        """Implementation of service initialization.
        
        This method should handle any setup required for the service to function,
        such as database connections, creating tables, etc.
        """
        pass

    async def cleanup(self) -> None:
        """Clean up resources used by the session service.
        
        This method should be called when the service is no longer needed
        to ensure proper cleanup of resources.
        """
        if self._initialized:
            await self._cleanup_impl()
            self._initialized = False

    @abc.abstractmethod
    async def _cleanup_impl(self) -> None:
        """Implementation of service cleanup.
        
        This method should handle any cleanup required for the service,
        such as closing database connections.
        """
        pass

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """Create a new session."""
        if not self._initialized:
            await self.initialize()
        return await self._create_session_impl(
            app_name=app_name,
            user_id=user_id,
            state=state,
            session_id=session_id,
        )

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        """Get a session by ID."""
        if not self._initialized:
            await self.initialize()
        return await self._get_session_impl(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            config=config,
        )

    async def list_sessions(
        self,
        *,
        app_name: str,
        user_id: str
    ) -> ListSessionsResponse:
        """List all sessions for a user."""
        if not self._initialized:
            await self.initialize()
        return await self._list_sessions_impl(
            app_name=app_name,
            user_id=user_id,
        )

    async def delete_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str
    ) -> None:
        """Delete a session."""
        if not self._initialized:
            await self.initialize()
        await self._delete_session_impl(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )

    async def append_event(self, session: Session, event: Event) -> Event:
        """Append an event to a session."""
        if not self._initialized:
            await self.initialize()
        # Update the session object
        await super().append_event(session=session, event=event)
        session.last_update_time = event.timestamp
        # Update the storage
        await self._append_event_impl(session=session, event=event)
        return event

    @abc.abstractmethod
    async def _create_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """Implementation of session creation."""
        pass

    @abc.abstractmethod
    async def _get_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        """Implementation of session retrieval."""
        pass

    @abc.abstractmethod
    async def _list_sessions_impl(
        self,
        *,
        app_name: str,
        user_id: str
    ) -> ListSessionsResponse:
        """Implementation of session listing."""
        pass

    @abc.abstractmethod
    async def _delete_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str
    ) -> None:
        """Implementation of session deletion."""
        pass

    @abc.abstractmethod
    async def _append_event_impl(self, session: Session, event: Event) -> None:
        """Implementation of event appending."""
        pass