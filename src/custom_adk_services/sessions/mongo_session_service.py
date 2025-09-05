"""MongoDB-based session service implementation."""

import json
import time
import uuid
from typing import Any, Optional, Dict

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except ImportError:
    raise ImportError(
        "PyMongo is required for MongoSessionService. "
        "Install it with: pip install pymongo"
    )

from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.adk.sessions.base_session_service import GetSessionConfig, ListSessionsResponse

from .base_custom_session_service import BaseCustomSessionService


class MongoSessionService(BaseCustomSessionService):
    """MongoDB-based session service implementation."""

    def __init__(self, connection_string: str, database_name: str = "adk_sessions"):
        """Initialize the MongoDB session service.
        
        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use
        """
        super().__init__()
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None

    async def _initialize_impl(self) -> None:
        """Initialize the MongoDB connection."""
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            self.collection = self.db.sessions
            
            # Create indexes for better performance
            self.collection.create_index([("app_name", 1), ("user_id", 1)])
            self.collection.create_index("id")
        except PyMongoError as e:
            raise RuntimeError(f"Failed to initialize MongoDB session service: {e}")

    async def _cleanup_impl(self) -> None:
        """Clean up MongoDB connections."""
        if self.client:
            self.client.close()
            self.client = None
        self.db = None
        self.collection = None

    def _serialize_events(self, events: list[Event]) -> list[Dict]:
        """Serialize events to dictionaries."""
        return [event.model_dump() for event in events]

    def _deserialize_events(self, event_dicts: list[Dict]) -> list[Event]:
        """Deserialize events from dictionaries."""
        return [Event(**event_dict) for event_dict in event_dicts]

    async def _create_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """Implementation of session creation."""
        try:
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
            
            # Create document for MongoDB
            document = {
                "_id": session_id,
                "id": session_id,
                "app_name": app_name,
                "user_id": user_id,
                "state": session.state,
                "events": self._serialize_events(session.events),
                "last_update_time": session.last_update_time
            }
            
            # Insert into MongoDB
            self.collection.insert_one(document)
            
            return session
        except PyMongoError as e:
            raise RuntimeError(f"Failed to create session: {e}")

    async def _get_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        """Implementation of session retrieval."""
        try:
            # Retrieve from MongoDB
            document = self.collection.find_one({
                "_id": session_id,
                "app_name": app_name,
                "user_id": user_id
            })
            
            if not document:
                return None
            
            # Create session object
            session = Session(
                id=document["id"],
                app_name=document["app_name"],
                user_id=document["user_id"],
                state=document["state"],
                events=self._deserialize_events(document["events"]),
                last_update_time=document["last_update_time"]
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
        except PyMongoError as e:
            raise RuntimeError(f"Failed to get session: {e}")

    async def _list_sessions_impl(
        self,
        *,
        app_name: str,
        user_id: str
    ) -> ListSessionsResponse:
        """Implementation of session listing."""
        try:
            # Retrieve all sessions for user (without events for performance)
            cursor = self.collection.find(
                {
                    "app_name": app_name,
                    "user_id": user_id
                },
                {
                    "_id": 1,
                    "id": 1,
                    "app_name": 1,
                    "user_id": 1,
                    "state": 1,
                    "last_update_time": 1
                }
            )
            
            # Create session objects without events
            sessions = []
            for document in cursor:
                session = Session(
                    id=document["id"],
                    app_name=document["app_name"],
                    user_id=document["user_id"],
                    state=document["state"],
                    events=[],  # Empty events for listing
                    last_update_time=document["last_update_time"]
                )
                sessions.append(session)
            
            return ListSessionsResponse(sessions=sessions)
        except PyMongoError as e:
            raise RuntimeError(f"Failed to list sessions: {e}")

    async def _delete_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str
    ) -> None:
        """Implementation of session deletion."""
        try:
            # Delete from MongoDB
            self.collection.delete_one({
                "_id": session_id,
                "app_name": app_name,
                "user_id": user_id
            })
        except PyMongoError as e:
            raise RuntimeError(f"Failed to delete session: {e}")

    async def _append_event_impl(self, session: Session, event: Event) -> None:
        """Implementation of event appending."""
        try:
            # Prepare update data
            update_data = {
                "$set": {
                    "events": self._serialize_events(session.events),
                    "last_update_time": session.last_update_time
                }
            }
            
            # Apply state changes from event if present
            if event.actions and event.actions.state_delta:
                update_data["$set"]["state"] = session.state
            
            # Update session in MongoDB
            result = self.collection.update_one(
                {
                    "_id": session.id,
                    "app_name": session.app_name,
                    "user_id": session.user_id
                },
                update_data
            )
            
            if result.matched_count == 0:
                raise ValueError(f"Session {session.id} not found")
        except PyMongoError as e:
            raise RuntimeError(f"Failed to append event: {e}")