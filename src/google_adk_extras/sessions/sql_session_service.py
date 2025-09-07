"""SQL-based session service implementation using SQLAlchemy."""

import json
import logging
from typing import Any, Optional
from datetime import datetime, timezone

try:
    from sqlalchemy import create_engine, Column, String, Text, DateTime
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    raise ImportError(
        "SQLAlchemy is required for SQLSessionService. "
        "Install it with: pip install sqlalchemy"
    )

from google.adk.events.event import Event
from .base_custom_session_service import BaseCustomSessionService


logger = logging.getLogger('google_adk_extras.' + __name__)

# Use the modern declarative_base import
Base = declarative_base()


class SQLSessionModel(Base):
    """SQLAlchemy model for storing sessions."""
    __tablename__ = 'adk_sessions'

    # Primary key
    id = Column(String, primary_key=True)
    
    # Session identifiers
    app_name = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # Session data
    state = Column(Text, nullable=False)  # JSON string
    events = Column(Text, nullable=False)  # JSON string
    last_update_time = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class SQLSessionService(BaseCustomSessionService):
    """SQL-based session service implementation.

    This service stores sessions in a SQL database using SQLAlchemy.
    It supports various SQL databases including SQLite, PostgreSQL, and MySQL.
    """

    def __init__(self, database_url: str):
        """Initialize the SQL session service.
        
        Args:
            database_url: Database connection string (e.g., 'sqlite:///sessions.db')
        """
        super().__init__()
        self.database_url = database_url
        self.engine: Optional[object] = None
        self.session_local: Optional[object] = None

    async def _initialize_impl(self) -> None:
        """Initialize the database connection and create tables.
        
        Raises:
            RuntimeError: If database initialization fails.
        """
        try:
            self.engine = create_engine(self.database_url)
            Base.metadata.create_all(self.engine)
            self.session_local = sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=self.engine
            )
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to initialize SQL session service: {e}")

    async def _cleanup_impl(self) -> None:
        """Clean up database connections."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
        self.session_local = None

    def _get_db_session(self):
        """Get a database session.
        
        Returns:
            A database session object.
            
        Raises:
            RuntimeError: If the service is not initialized.
        """
        if not self.session_local:
            raise RuntimeError("Service not initialized")
        return self.session_local()

    def _serialize_state(self, state: dict[str, Any]) -> str:
        """Serialize session state to JSON string.
        
        Args:
            state: The state dictionary to serialize.
            
        Returns:
            JSON string representation of the state.
            
        Raises:
            ValueError: If serialization fails.
        """
        try:
            return json.dumps(state)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize state: {e}")

    def _deserialize_state(self, state_str: str) -> dict[str, Any]:
        """Deserialize session state from JSON string.
        
        Args:
            state_str: JSON string representation of the state.
            
        Returns:
            The deserialized state dictionary.
            
        Raises:
            ValueError: If deserialization fails.
        """
        try:
            return json.loads(state_str) if state_str else {}
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to deserialize state: {e}")

    def _serialize_events(self, events: list[Event]) -> str:
        """Serialize events to JSON string.
        
        Args:
            events: List of events to serialize.
            
        Returns:
            JSON string representation of the events.
            
        Raises:
            ValueError: If serialization fails.
        """
        try:
            # Convert events to dictionaries
            event_dicts = [event.model_dump() for event in events]
            return json.dumps(event_dicts)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize events: {e}")

    def _deserialize_events(self, events_str: str) -> list[Event]:
        """Deserialize events from JSON string.
        
        Args:
            events_str: JSON string representation of the events.
            
        Returns:
            List of deserialized events.
            
        Raises:
            ValueError: If deserialization fails.
        """
        try:
            event_dicts = json.loads(events_str) if events_str else []
            return [Event(**event_dict) for event_dict in event_dicts]
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to deserialize events: {e}")

    async def _create_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> "Session":
        """Implementation of session creation.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            state: Optional initial state for the session.
            session_id: Optional specific ID for the session.
            
        Returns:
            The created Session object.
            
        Raises:
            RuntimeError: If session creation fails.
        """
        # Import Session inside the function to avoid circular import
        from google.adk.sessions.session import Session
        import time
        import uuid
        
        # Generate session ID if not provided
        session_id = session_id or str(uuid.uuid4())
        
        # Create session object
        session = Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=state or {},
            events=[],
            last_update_time=time.time()
        )
        
        # Save to database
        db_session = self._get_db_session()
        try:
            db_session_model = SQLSessionModel(
                id=session_id,
                app_name=app_name,
                user_id=user_id,
                state=self._serialize_state(session.state),
                events=self._serialize_events(session.events),
                last_update_time=datetime.fromtimestamp(session.last_update_time, tz=timezone.utc)
            )
            
            db_session.add(db_session_model)
            db_session.commit()
        except SQLAlchemyError as e:
            db_session.rollback()
            raise RuntimeError(f"Failed to create session: {e}")
        finally:
            db_session.close()
        
        return session

    async def _get_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional["GetSessionConfig"] = None,
    ) -> Optional["Session"]:
        """Implementation of session retrieval.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session to retrieve.
            config: Optional configuration for session retrieval.
            
        Returns:
            The Session object if found, None otherwise.
            
        Raises:
            RuntimeError: If session retrieval fails.
        """
        db_session = self._get_db_session()
        try:
            db_session_model = db_session.query(SQLSessionModel).filter(
                SQLSessionModel.id == session_id,
                SQLSessionModel.app_name == app_name,
                SQLSessionModel.user_id == user_id
            ).first()
            
            if not db_session_model:
                return None
            
            # Create session object
            # Import Session inside the function to avoid circular import
            from google.adk.sessions.session import Session
            session = Session(
                id=db_session_model.id,
                app_name=db_session_model.app_name,
                user_id=db_session_model.user_id,
                state=self._deserialize_state(db_session_model.state),
                events=self._deserialize_events(db_session_model.events),
                last_update_time=db_session_model.last_update_time.timestamp()
            )
            
            # Apply config filters if provided
            if config:
                if config.num_recent_events:
                    session.events = session.events[-config.num_recent_events:]
                if config.after_timestamp:
                    filtered_events = [
                        event for event in session.events 
                        if event.timestamp >= config.after_timestamp
                    ]
                    session.events = filtered_events
            
            return session
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to get session: {e}")
        finally:
            db_session.close()

    async def _list_sessions_impl(
        self,
        *,
        app_name: str,
        user_id: str
    ) -> "ListSessionsResponse":
        """Implementation of session listing.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            
        Returns:
            A ListSessionsResponse containing the sessions.
            
        Raises:
            RuntimeError: If session listing fails.
        """
        db_session = self._get_db_session()
        try:
            # Retrieve all sessions for user (without events)
            db_session_models = db_session.query(SQLSessionModel).filter(
                SQLSessionModel.app_name == app_name,
                SQLSessionModel.user_id == user_id
            ).all()
            
            # Create session objects without events
            sessions = []
            for db_model in db_session_models:
                # Import Session inside the function to avoid circular import
                from google.adk.sessions.session import Session
                session = Session(
                    id=db_model.id,
                    app_name=db_model.app_name,
                    user_id=db_model.user_id,
                    state=self._deserialize_state(db_model.state),
                    events=[],  # Empty events for listing
                    last_update_time=db_model.last_update_time.timestamp()
                )
                sessions.append(session)
            
            try:
                from google.adk.sessions.base_session_service import ListSessionsResponse
                return ListSessionsResponse(sessions=sessions)
            except Exception:
                from types import SimpleNamespace
                return SimpleNamespace(sessions=sessions)
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to list sessions: {e}")
        finally:
            db_session.close()

    async def _delete_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str
    ) -> None:
        """Implementation of session deletion.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session to delete.
            
        Raises:
            RuntimeError: If session deletion fails.
        """
        db_session = self._get_db_session()
        try:
            # Delete from database
            db_session.query(SQLSessionModel).filter(
                SQLSessionModel.id == session_id,
                SQLSessionModel.app_name == app_name,
                SQLSessionModel.user_id == user_id
            ).delete()
            
            db_session.commit()
        except SQLAlchemyError as e:
            db_session.rollback()
            raise RuntimeError(f"Failed to delete session: {e}")
        finally:
            db_session.close()

    async def _append_event_impl(self, session: "Session", event: Event) -> None:
        """Implementation of event appending.
        
        Args:
            session: The session to append the event to.
            event: The event to append.
            
        Raises:
            RuntimeError: If appending the event fails.
            ValueError: If the session is not found.
        """
        db_session = self._get_db_session()
        try:
            # Update session in database
            db_session_model = db_session.query(SQLSessionModel).filter(
                SQLSessionModel.id == session.id,
                SQLSessionModel.app_name == session.app_name,
                SQLSessionModel.user_id == session.user_id
            ).first()
            
            if not db_session_model:
                raise ValueError(f"Session {session.id} not found")
            
            # Update the session model
            db_session_model.events = self._serialize_events(session.events)
            db_session_model.last_update_time = datetime.fromtimestamp(session.last_update_time, tz=timezone.utc)
            
            # Apply state changes from event if present
            if event.actions and event.actions.state_delta:
                # Update state in the session model
                current_state = self._deserialize_state(db_session_model.state)
                current_state.update(event.actions.state_delta)
                db_session_model.state = self._serialize_state(current_state)
            
            db_session.commit()
        except SQLAlchemyError as e:
            db_session.rollback()
            raise RuntimeError(f"Failed to append event: {e}")
        finally:
            db_session.close()
