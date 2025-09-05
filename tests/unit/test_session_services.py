"""Unit tests for session services using pytest."""

import pytest
import asyncio
import tempfile
import shutil
import os
from unittest.mock import patch, MagicMock

from google.adk.sessions.session import Session
from google.adk.events.event import Event

from custom_adk_services.sessions.base_custom_session_service import BaseCustomSessionService
from custom_adk_services.sessions.sql_session_service import SQLSessionService
from custom_adk_services.sessions.yaml_file_session_service import YamlFileSessionService


class TestBaseCustomSessionService:
    """Test the base custom session service class."""

    @pytest.mark.asyncio
    async def test_initialize_and_cleanup(self):
        """Test initialization and cleanup methods."""

        class TestService(BaseCustomSessionService):
            async def _initialize_impl(self):
                pass

            async def _cleanup_impl(self):
                pass

            async def _create_session_impl(self, *, app_name, user_id, state=None, session_id=None):
                pass

            async def _get_session_impl(self, *, app_name, user_id, session_id, config=None):
                pass

            async def _list_sessions_impl(self, *, app_name, user_id):
                pass

            async def _delete_session_impl(self, *, app_name, user_id, session_id):
                pass

            async def _append_event_impl(self, session, event):
                pass

        service = TestService()
        assert not service._initialized

        # Test initialization
        await service.initialize()
        assert service._initialized

        # Test cleanup
        await service.cleanup()
        assert not service._initialized


class TestYamlFileSessionService:
    """Test the YAML file session service."""

    @pytest.mark.asyncio
    async def test_initialization(self, temp_dir):
        """Test that the YAML file service initializes correctly."""
        service = YamlFileSessionService(temp_dir)
        await service.initialize()
        assert service._initialized
        await service.cleanup()

    @pytest.mark.asyncio
    async def test_create_and_get_session(self, temp_dir):
        """Test creating and retrieving a session."""
        service = YamlFileSessionService(temp_dir)
        await service.initialize()

        try:
            # Create a session
            session = await service.create_session(
                app_name="test_app",
                user_id="test_user",
                state={"theme": "dark", "language": "en"}
            )

            assert session.id is not None
            assert session.app_name == "test_app"
            assert session.user_id == "test_user"
            assert session.state == {"theme": "dark", "language": "en"}
            assert len(session.events) == 0

            # Retrieve the session
            retrieved_session = await service.get_session(
                app_name="test_app",
                user_id="test_user",
                session_id=session.id
            )

            assert retrieved_session is not None
            assert retrieved_session.id == session.id
            assert retrieved_session.app_name == "test_app"
            assert retrieved_session.user_id == "test_user"
            assert retrieved_session.state == {"theme": "dark", "language": "en"}

        finally:
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_list_sessions(self, temp_dir):
        """Test listing sessions."""
        service = YamlFileSessionService(temp_dir)
        await service.initialize()

        try:
            # Create multiple sessions with unique identifiers
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            
            session1 = await service.create_session(
                app_name=f"test_app_{unique_id}",
                user_id=f"test_user_{unique_id}",
                state={"session": 1}
            )

            session2 = await service.create_session(
                app_name=f"test_app_{unique_id}",
                user_id=f"test_user_{unique_id}",
                state={"session": 2}
            )

            # List sessions
            sessions_response = await service.list_sessions(
                app_name=f"test_app_{unique_id}",
                user_id=f"test_user_{unique_id}"
            )

            assert len(sessions_response.sessions) == 2
            session_ids = {s.id for s in sessions_response.sessions}
            assert session1.id in session_ids
            assert session2.id in session_ids

            # Verify events are empty in list response
            for session in sessions_response.sessions:
                assert len(session.events) == 0

        finally:
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_delete_session(self, temp_dir):
        """Test deleting a session."""
        service = YamlFileSessionService(temp_dir)
        await service.initialize()

        try:
            # Create a session
            session = await service.create_session(
                app_name="test_app",
                user_id="test_user",
                state={"theme": "dark"}
            )

            # Verify session exists
            retrieved_session = await service.get_session(
                app_name="test_app",
                user_id="test_user",
                session_id=session.id
            )
            assert retrieved_session is not None

            # Delete session
            await service.delete_session(
                app_name="test_app",
                user_id="test_user",
                session_id=session.id
            )

            # Verify session is deleted
            deleted_session = await service.get_session(
                app_name="test_app",
                user_id="test_user",
                session_id=session.id
            )
            assert deleted_session is None

        finally:
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_append_event(self, temp_dir):
        """Test appending an event to a session."""
        service = YamlFileSessionService(temp_dir)
        await service.initialize()

        try:
            # Create a session
            session = await service.create_session(
                app_name="test_app",
                user_id="test_user",
                state={"theme": "dark"}
            )

            # Create an event
            event = Event(
                invocation_id="test_invocation",
                author="user",
                content=None
            )

            # Append event
            returned_event = await service.append_event(session, event)

            assert returned_event.invocation_id == "test_invocation"
            assert returned_event.author == "user"

            # Verify event was added to session
            updated_session = await service.get_session(
                app_name="test_app",
                user_id="test_user",
                session_id=session.id
            )

            assert len(updated_session.events) == 1
            assert updated_session.events[0].invocation_id == "test_invocation"

        finally:
            await service.cleanup()


class TestSQLSessionService:
    """Test the SQL session service."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test that the SQL service initializes correctly."""
        service = SQLSessionService("sqlite:///:memory:")
        await service.initialize()
        assert service._initialized
        await service.cleanup()

    @pytest.mark.asyncio
    async def test_create_and_get_session(self):
        """Test creating and retrieving a session."""
        service = SQLSessionService("sqlite:///:memory:")
        await service.initialize()

        try:
            # Create a session
            session = await service.create_session(
                app_name="test_app",
                user_id="test_user",
                state={"theme": "dark", "language": "en"}
            )

            assert session.id is not None
            assert session.app_name == "test_app"
            assert session.user_id == "test_user"
            assert session.state == {"theme": "dark", "language": "en"}
            assert len(session.events) == 0

            # Retrieve the session
            retrieved_session = await service.get_session(
                app_name="test_app",
                user_id="test_user",
                session_id=session.id
            )

            assert retrieved_session is not None
            assert retrieved_session.id == session.id
            assert retrieved_session.app_name == "test_app"
            assert retrieved_session.user_id == "test_user"
            assert retrieved_session.state == {"theme": "dark", "language": "en"}

        finally:
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_list_sessions(self):
        """Test listing sessions."""
        # Use a unique database for this test
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        service = SQLSessionService(f"sqlite:///:memory:?cache=shared&unique={unique_id}")
        await service.initialize()

        try:
            # Create multiple sessions
            session1 = await service.create_session(
                app_name=f"test_app_{unique_id}",
                user_id=f"test_user_{unique_id}",
                state={"session": 1}
            )

            session2 = await service.create_session(
                app_name=f"test_app_{unique_id}",
                user_id=f"test_user_{unique_id}",
                state={"session": 2}
            )

            # List sessions
            sessions_response = await service.list_sessions(
                app_name=f"test_app_{unique_id}",
                user_id=f"test_user_{unique_id}"
            )

            assert len(sessions_response.sessions) == 2
            session_ids = {s.id for s in sessions_response.sessions}
            assert session1.id in session_ids
            assert session2.id in session_ids

            # Verify events are empty in list response
            for session in sessions_response.sessions:
                assert len(session.events) == 0

        finally:
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_delete_session(self):
        """Test deleting a session."""
        service = SQLSessionService("sqlite:///:memory:")
        await service.initialize()

        try:
            # Create a session
            session = await service.create_session(
                app_name="test_app",
                user_id="test_user",
                state={"theme": "dark"}
            )

            # Verify session exists
            retrieved_session = await service.get_session(
                app_name="test_app",
                user_id="test_user",
                session_id=session.id
            )
            assert retrieved_session is not None

            # Delete session
            await service.delete_session(
                app_name="test_app",
                user_id="test_user",
                session_id=session.id
            )

            # Verify session is deleted
            deleted_session = await service.get_session(
                app_name="test_app",
                user_id="test_user",
                session_id=session.id
            )
            assert deleted_session is None

        finally:
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_append_event(self):
        """Test appending an event to a session."""
        service = SQLSessionService("sqlite:///:memory:")
        await service.initialize()

        try:
            # Create a session
            session = await service.create_session(
                app_name="test_app",
                user_id="test_user",
                state={"theme": "dark"}
            )

            # Create an event
            event = Event(
                invocation_id="test_invocation",
                author="user",
                content=None
            )

            # Append event
            returned_event = await service.append_event(session, event)

            assert returned_event.invocation_id == "test_invocation"
            assert returned_event.author == "user"

            # Verify event was added to session
            updated_session = await service.get_session(
                app_name="test_app",
                user_id="test_user",
                session_id=session.id
            )

            assert len(updated_session.events) == 1
            assert updated_session.events[0].invocation_id == "test_invocation"

        finally:
            await service.cleanup()