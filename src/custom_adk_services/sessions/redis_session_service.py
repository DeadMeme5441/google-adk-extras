"""Redis-based session service implementation."""

import json
import time
import uuid
from typing import Any, Optional, Dict

try:
    import redis
    from redis.exceptions import RedisError
except ImportError:
    raise ImportError(
        "Redis is required for RedisSessionService. "
        "Install it with: pip install redis"
    )

from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.adk.sessions.base_session_service import GetSessionConfig, ListSessionsResponse

from .base_custom_session_service import BaseCustomSessionService


class RedisSessionService(BaseCustomSessionService):
    """Redis-based session service implementation."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None):
        """Initialize the Redis session service.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (if required)
        """
        super().__init__()
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.client: Optional[redis.Redis] = None
        self.key_prefix = "adk_session:"

    async def _initialize_impl(self) -> None:
        """Initialize the Redis connection."""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
            # Test connection
            self.client.ping()
        except RedisError as e:
            raise RuntimeError(f"Failed to initialize Redis session service: {e}")

    async def _cleanup_impl(self) -> None:
        """Clean up Redis connections."""
        if self.client:
            self.client.close()
            self.client = None

    def _get_session_key(self, app_name: str, user_id: str, session_id: str) -> str:
        """Generate Redis key for a session."""
        return f"{self.key_prefix}{app_name}:{user_id}:{session_id}"

    def _get_user_sessions_key(self, app_name: str, user_id: str) -> str:
        """Generate Redis key for user sessions set."""
        return f"{self.key_prefix}{app_name}:{user_id}:sessions"

    def _serialize_state(self, state: dict[str, Any]) -> str:
        """Serialize session state to JSON string."""
        try:
            return json.dumps(state)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize state: {e}")

    def _deserialize_state(self, state_str: str) -> dict[str, Any]:
        """Deserialize session state from JSON string."""
        try:
            return json.loads(state_str) if state_str else {}
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to deserialize state: {e}")

    def _serialize_events(self, events: list[Event]) -> str:
        """Serialize events to JSON string."""
        try:
            event_dicts = [event.model_dump() for event in events]
            return json.dumps(event_dicts)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize events: {e}")

    def _deserialize_events(self, events_str: str) -> list[Event]:
        """Deserialize events from JSON string."""
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
            
            # Serialize data for storage
            session_data = {
                "id": session_id,
                "app_name": app_name,
                "user_id": user_id,
                "state": self._serialize_state(session.state),
                "events": self._serialize_events(session.events),
                "last_update_time": session.last_update_time
            }
            
            # Store session data in Redis
            session_key = self._get_session_key(app_name, user_id, session_id)
            self.client.hset(session_key, mapping=session_data)
            
            # Add to user sessions set
            user_sessions_key = self._get_user_sessions_key(app_name, user_id)
            self.client.sadd(user_sessions_key, session_id)
            
            # Set expiration (optional, can be configured)
            # self.client.expire(session_key, 86400)  # 24 hours
            
            return session
        except RedisError as e:
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
            # Retrieve from Redis
            session_key = self._get_session_key(app_name, user_id, session_id)
            session_data = self.client.hgetall(session_key)
            
            if not session_data:
                return None
            
            # Create session object
            session = Session(
                id=session_data["id"],
                app_name=session_data["app_name"],
                user_id=session_data["user_id"],
                state=self._deserialize_state(session_data["state"]),
                events=self._deserialize_events(session_data["events"]),
                last_update_time=float(session_data["last_update_time"])
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
        except RedisError as e:
            raise RuntimeError(f"Failed to get session: {e}")
        except (KeyError, ValueError) as e:
            raise RuntimeError(f"Failed to deserialize session data: {e}")

    async def _list_sessions_impl(
        self,
        *,
        app_name: str,
        user_id: str
    ) -> ListSessionsResponse:
        """Implementation of session listing."""
        try:
            # Get all session IDs for user
            user_sessions_key = self._get_user_sessions_key(app_name, user_id)
            session_ids = self.client.smembers(user_sessions_key)
            
            # Create session objects without events for performance
            sessions = []
            for session_id in session_ids:
                session_key = self._get_session_key(app_name, user_id, session_id)
                session_data = self.client.hgetall(session_key)
                
                if session_data:
                    session = Session(
                        id=session_data["id"],
                        app_name=session_data["app_name"],
                        user_id=session_data["user_id"],
                        state=self._deserialize_state(session_data["state"]),
                        events=[],  # Empty events for listing
                        last_update_time=float(session_data["last_update_time"])
                    )
                    sessions.append(session)
            
            return ListSessionsResponse(sessions=sessions)
        except RedisError as e:
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
            # Remove from Redis
            session_key = self._get_session_key(app_name, user_id, session_id)
            self.client.delete(session_key)
            
            # Remove from user sessions set
            user_sessions_key = self._get_user_sessions_key(app_name, user_id)
            self.client.srem(user_sessions_key, session_id)
        except RedisError as e:
            raise RuntimeError(f"Failed to delete session: {e}")

    async def _append_event_impl(self, session: Session, event: Event) -> None:
        """Implementation of event appending."""
        try:
            session_key = self._get_session_key(session.app_name, session.user_id, session.id)
            
            # Update session data
            update_data = {
                "events": self._serialize_events(session.events),
                "last_update_time": session.last_update_time
            }
            
            # Apply state changes from event if present
            if event.actions and event.actions.state_delta:
                # Get current state and update it
                current_state_str = self.client.hget(session_key, "state")
                current_state = self._deserialize_state(current_state_str) if current_state_str else {}
                current_state.update(event.actions.state_delta)
                update_data["state"] = self._serialize_state(current_state)
            
            # Update in Redis
            self.client.hset(session_key, mapping=update_data)
        except RedisError as e:
            raise RuntimeError(f"Failed to append event: {e}")
        except (KeyError, ValueError) as e:
            raise RuntimeError(f"Failed to update session data: {e}")