"""MongoDB-based session service implementation (async via PyMongo wrappers).

This refactor aligns behavior with the reference ADK Mongo session service:
- Collections: `sessions`, `events`, `app_states`, `user_states`.
- Events stored separately (raw JSON) and merged on read with filtering.
- App/user state merged into session via `State.APP_PREFIX`/`State.USER_PREFIX`.
- State deltas in events upserted into `app_states` / `user_states`.

Note: PyMongo does not expose a public asyncio client in 4.x, so we wrap
blocking calls with ``asyncio.to_thread`` to keep the API non-blocking.
"""

import asyncio
import copy
import time
import uuid
from typing import Any, Optional

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except ImportError:  # pragma: no cover - optional backend
    raise ImportError(
        "PyMongo is required for MongoSessionService. "
        "Install it with: pip install pymongo"
    )

from google.adk.events.event import Event
from google.adk.sessions.base_session_service import (
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session
from google.adk.sessions.state import State

from .base_custom_session_service import BaseCustomSessionService


class MongoSessionService(BaseCustomSessionService):
    """MongoDB-based session service with separate event/state collections."""

    def __init__(self, connection_string: str, database_name: Optional[str] = None):
        """Initialize the MongoDB session service.

        Args:
            connection_string: MongoDB connection string.
            database_name: Database name. If omitted, uses the DB in the URI
                or defaults to ``adk_sessions``.
        """
        super().__init__()
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db = None
        self.sessions = None
        self.events = None
        self.app_states = None
        self.user_states = None

    # ---- lifecycle -----------------------------------------------------
    async def _initialize_impl(self) -> None:
        try:
            self.client = MongoClient(self.connection_string)
            db_name = self.database_name or (self.client.get_default_database().name if self.client.get_default_database() is not None else "adk_sessions")
            self.db = self.client[db_name]
            self.sessions = self.db["sessions"]
            self.events = self.db["events"]
            self.app_states = self.db["app_states"]
            self.user_states = self.db["user_states"]

            def _ensure_indexes():
                self.sessions.create_index([("app_name", 1), ("user_id", 1), ("id", 1)], name="session_key")
                self.sessions.create_index("last_update_time")
                self.events.create_index([("app_name", 1), ("user_id", 1), ("id", 1), ("timestamp", 1)], name="event_key")
                self.app_states.create_index([("app_name", 1), ("key", 1)], name="app_state_key", unique=True)
                self.user_states.create_index([("app_name", 1), ("user_id", 1), ("key", 1)], name="user_state_key", unique=True)

            await asyncio.to_thread(_ensure_indexes)
        except PyMongoError as e:  # pragma: no cover - connection errors
            raise RuntimeError(f"Failed to initialize MongoDB session service: {e}")

    async def _cleanup_impl(self) -> None:
        if self.client:
            self.client.close()
        self.client = None
        self.db = None
        self.sessions = None
        self.events = None
        self.app_states = None
        self.user_states = None

    # ---- helpers -------------------------------------------------------
    async def _merge_state(self, app_name: str, user_id: str, session: Session) -> Session:
        """Merge app and user state into the session."""

        def _load_states():
            app_states = list(self.app_states.find({"app_name": app_name}))
            user_states = list(self.user_states.find({"app_name": app_name, "user_id": user_id}))
            return app_states, user_states

        app_states, user_states = await asyncio.to_thread(_load_states)
        for st in app_states:
            session.state[State.APP_PREFIX + st["key"]] = st["value"]
        for st in user_states:
            session.state[State.USER_PREFIX + st["key"]] = st["value"]
        return session

    # ---- CRUD ----------------------------------------------------------
    async def _create_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        sid = session_id or uuid.uuid4().hex
        now = time.time()
        session_state = state or {}

        def _insert():
            self.sessions.insert_one(
                {
                    "app_name": app_name,
                    "user_id": user_id,
                    "id": sid,
                    "state": session_state,
                    "last_update_time": now,
                }
            )

        try:
            await asyncio.to_thread(_insert)
        except PyMongoError as e:
            raise RuntimeError(f"Failed to create session: {e}")

        session = Session(
            id=sid,
            app_name=app_name,
            user_id=user_id,
            state=session_state,
            events=[],
            last_update_time=now,
        )
        return await self._merge_state(app_name, user_id, copy.deepcopy(session))

    async def _get_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        def _load():
            doc = self.sessions.find_one({"app_name": app_name, "user_id": user_id, "id": session_id})
            if not doc:
                return None, []
            events_docs = list(self.events.find({"app_name": app_name, "user_id": user_id, "id": session_id}).sort("timestamp", 1))
            return doc, events_docs

        try:
            doc, raw_events = await asyncio.to_thread(_load)
        except PyMongoError as e:
            raise RuntimeError(f"Failed to get session: {e}")

        if not doc:
            return None

        events = [Event.model_validate_json(e["raw"]) for e in raw_events]

        if config:
            if config.after_timestamp is not None:
                events = [e for e in events if e.timestamp is None or e.timestamp >= config.after_timestamp]
            if config.num_recent_events is not None and events:
                events = events[-config.num_recent_events :]

        session = Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=doc.get("state", {}),
            events=events,
            last_update_time=doc.get("last_update_time", 0.0),
        )
        return await self._merge_state(app_name, user_id, copy.deepcopy(session))

    async def _list_sessions_impl(
        self,
        *,
        app_name: str,
        user_id: str,
    ) -> ListSessionsResponse:
        def _fetch():
            return list(self.sessions.find({"app_name": app_name, "user_id": user_id}))

        try:
            docs = await asyncio.to_thread(_fetch)
        except PyMongoError as e:
            raise RuntimeError(f"Failed to list sessions: {e}")

        sessions: list[Session] = []
        for doc in docs:
            sessions.append(
                Session(
                    id=doc["id"],
                    app_name=app_name,
                    user_id=user_id,
                    state={},  # keep listing light
                    events=[],
                    last_update_time=doc.get("last_update_time", 0.0),
                )
            )
        return ListSessionsResponse(sessions=sessions)

    async def _delete_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> None:
        def _delete():
            filt = {"app_name": app_name, "user_id": user_id, "id": session_id}
            self.sessions.delete_one(filt)
            self.events.delete_many(filt)

        try:
            await asyncio.to_thread(_delete)
        except PyMongoError as e:
            raise RuntimeError(f"Failed to delete session: {e}")

    async def _append_event_impl(self, session: Session, event: Event) -> None:
        if event.partial:
            return  # Do not store partial events

        filt = {"app_name": session.app_name, "user_id": session.user_id, "id": session.id}

        # Check for existence and staleness
        def _load_session():
            return self.sessions.find_one(filt)

        doc = await asyncio.to_thread(_load_session)
        if not doc:
            raise ValueError("session not found")
        if doc.get("last_update_time", 0.0) > session.last_update_time:
            raise ValueError("stale session")

        # Store the event and update session
        def _write():
            self.events.insert_one({**filt, "raw": event.model_dump_json(), "timestamp": event.timestamp})
            self.sessions.update_one(
                filt,
                {"$set": {"state": session.state, "last_update_time": session.last_update_time}},
            )

            # Upsert state deltas
            if event.actions and event.actions.state_delta:
                for key, value in event.actions.state_delta.items():
                    if key.startswith(State.APP_PREFIX):
                        app_key = key[len(State.APP_PREFIX) :]
                        self.app_states.update_one(
                            {"app_name": session.app_name, "key": app_key},
                            {"$set": {"value": value}},
                            upsert=True,
                        )
                    elif key.startswith(State.USER_PREFIX):
                        user_key = key[len(State.USER_PREFIX) :]
                        self.user_states.update_one(
                            {"app_name": session.app_name, "user_id": session.user_id, "key": user_key},
                            {"$set": {"value": value}},
                            upsert=True,
                        )

        try:
            await asyncio.to_thread(_write)
        except PyMongoError as e:
            raise RuntimeError(f"Failed to append event: {e}")
