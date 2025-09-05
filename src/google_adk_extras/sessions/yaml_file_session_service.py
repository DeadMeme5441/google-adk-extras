"""YAML file-based session service implementation."""

import json
import time
import uuid
import os
from typing import Any, Optional
from pathlib import Path

try:
    import yaml
except ImportError:
    raise ImportError(
        "PyYAML is required for YamlFileSessionService. "
        "Install it with: pip install PyYAML"
    )

from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.adk.sessions.base_session_service import GetSessionConfig, ListSessionsResponse

from .base_custom_session_service import BaseCustomSessionService


class YamlFileSessionService(BaseCustomSessionService):
    """YAML file-based session service implementation.

    This service stores sessions in YAML files in a hierarchical directory structure.
    Each session is stored in a separate YAML file organized by app name and user ID.
    """

    def __init__(self, base_directory: str = "./sessions"):
        """Initialize the YAML file session service.
        
        Args:
            base_directory: Base directory for storing session files. Defaults to "./sessions".
        """
        super().__init__()
        self.base_directory = Path(base_directory)
        # Create base directory if it doesn't exist
        self.base_directory.mkdir(parents=True, exist_ok=True)

    async def _initialize_impl(self) -> None:
        """Initialize the file system session service.
        
        Ensures the base directory exists.
        """
        # Ensure base directory exists
        self.base_directory.mkdir(parents=True, exist_ok=True)

    async def _cleanup_impl(self) -> None:
        """Clean up resources (no cleanup needed for file-based service)."""
        pass

    def _get_session_file_path(self, app_name: str, user_id: str, session_id: str) -> Path:
        """Generate file path for a session.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session.
            
        Returns:
            Path to the session file.
        """
        # Create app directory
        app_dir = self.base_directory / app_name
        app_dir.mkdir(exist_ok=True)
        
        # Create user directory
        user_dir = app_dir / user_id
        user_dir.mkdir(exist_ok=True)
        
        # Return session file path
        return user_dir / f"{session_id}.yaml"

    def _get_user_directory(self, app_name: str, user_id: str) -> Path:
        """Get the directory path for a user's sessions.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            
        Returns:
            Path to the user's session directory.
        """
        return self.base_directory / app_name / user_id

    def _serialize_events(self, events: list[Event]) -> list[dict]:
        """Serialize events to dictionaries.
        
        Args:
            events: List of Event objects to serialize.
            
        Returns:
            List of dictionaries representing the events.
        """
        return [event.model_dump() for event in events]

    def _deserialize_events(self, event_dicts: list[dict]) -> list[Event]:
        """Deserialize events from dictionaries.
        
        Args:
            event_dicts: List of dictionaries representing events.
            
        Returns:
            List of Event objects.
        """
        return [Event(**event_dict) for event_dict in event_dicts]

    def _session_to_dict(self, session: Session) -> dict:
        """Convert session to dictionary for YAML serialization.
        
        Args:
            session: The Session object to convert.
            
        Returns:
            Dictionary representation of the session.
        """
        return {
            "id": session.id,
            "app_name": session.app_name,
            "user_id": session.user_id,
            "state": session.state,
            "events": self._serialize_events(session.events),
            "last_update_time": session.last_update_time
        }

    def _dict_to_session(self, data: dict) -> Session:
        """Convert dictionary to session object.
        
        Args:
            data: Dictionary representation of the session.
            
        Returns:
            Session object.
        """
        return Session(
            id=data["id"],
            app_name=data["app_name"],
            user_id=data["user_id"],
            state=data["state"],
            events=self._deserialize_events(data["events"]),
            last_update_time=data["last_update_time"]
        )

    async def _create_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """Implementation of session creation.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            state: Optional initial state for the session.
            session_id: Optional specific ID for the session. If not provided,
                a UUID will be generated.
                
        Returns:
            The created Session object.
            
        Raises:
            RuntimeError: If session creation fails.
        """
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
        
        # Save to YAML file
        file_path = self._get_session_file_path(app_name, user_id, session_id)
        session_data = self._session_to_dict(session)
        
        try:
            with open(file_path, 'w') as f:
                yaml.dump(session_data, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            raise RuntimeError(f"Failed to save session to file: {e}")
        
        return session

    async def _get_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
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
        file_path = self._get_session_file_path(app_name, user_id, session_id)
        
        # Check if file exists
        if not file_path.exists():
            return None
        
        try:
            # Load from YAML file
            with open(file_path, 'r') as f:
                session_data = yaml.safe_load(f)
            
            # Create session object
            session = self._dict_to_session(session_data)
            
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
        except Exception as e:
            raise RuntimeError(f"Failed to load session from file: {e}")

    async def _list_sessions_impl(
        self,
        *,
        app_name: str,
        user_id: str
    ) -> ListSessionsResponse:
        """Implementation of session listing.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            
        Returns:
            A ListSessionsResponse containing the sessions.
            
        Raises:
            RuntimeError: If session listing fails.
        """
        user_dir = self._get_user_directory(app_name, user_id)
        
        # Check if user directory exists
        if not user_dir.exists():
            return ListSessionsResponse(sessions=[])
        
        sessions = []
        try:
            # Iterate through session files
            for file_path in user_dir.glob("*.yaml"):
                # Load session data
                with open(file_path, 'r') as f:
                    session_data = yaml.safe_load(f)
                
                # Create session object without events for performance
                session = Session(
                    id=session_data["id"],
                    app_name=session_data["app_name"],
                    user_id=session_data["user_id"],
                    state=session_data["state"],
                    events=[],  # Empty events for listing
                    last_update_time=session_data["last_update_time"]
                )
                sessions.append(session)
            
            return ListSessionsResponse(sessions=sessions)
        except Exception as e:
            raise RuntimeError(f"Failed to list sessions: {e}")

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
        file_path = self._get_session_file_path(app_name, user_id, session_id)
        
        # Delete file if it exists
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                raise RuntimeError(f"Failed to delete session file: {e}")

    async def _append_event_impl(self, session: Session, event: Event) -> None:
        """Implementation of event appending.
        
        Args:
            session: The session to append the event to.
            event: The event to append.
            
        Raises:
            RuntimeError: If appending the event fails.
            ValueError: If the session file is not found.
        """
        file_path = self._get_session_file_path(session.app_name, session.user_id, session.id)
        
        # Check if file exists
        if not file_path.exists():
            raise ValueError(f"Session file {file_path} not found")
        
        try:
            # Load existing session data
            with open(file_path, 'r') as f:
                session_data = yaml.safe_load(f)
            
            # Update session data
            session_data["events"] = self._serialize_events(session.events)
            session_data["last_update_time"] = session.last_update_time
            
            # Apply state changes from event if present
            if event.actions and event.actions.state_delta:
                session_data["state"] = session.state
            
            # Save updated session data
            with open(file_path, 'w') as f:
                yaml.dump(session_data, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            raise RuntimeError(f"Failed to update session file: {e}")