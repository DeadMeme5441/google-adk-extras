"""Integration tests for session and artifact services working together."""

import pytest
import os
import sys

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from google.adk.events.event import Event
from google.genai.types import Blob, Part

from google_adk_extras.sessions import (
    SQLSessionService,
    YamlFileSessionService
)
from google_adk_extras.artifacts import (
    SQLArtifactService,
    LocalFolderArtifactService
)


class TestSessionAndArtifactIntegration:
    """Test session and artifact services working together."""

    @pytest.mark.asyncio
    async def test_sql_session_with_sql_artifact(self):
        """Test SQL session service working with SQL artifact service."""
        # Create services
        session_service = SQLSessionService("sqlite:///:memory:")
        artifact_service = SQLArtifactService("sqlite:///:memory:")
        
        try:
            # Initialize services
            await session_service.initialize()
            await artifact_service.initialize()
            
            # Create a session
            session = await session_service.create_session(
                app_name="integration_test_app",
                user_id="integration_test_user",
                state={"theme": "dark"}
            )
            
            assert session.id is not None
            
            # Create an artifact
            test_data = b"Integration test artifact content."
            blob = Blob(data=test_data, mime_type="text/plain")
            artifact = Part(inline_data=blob)
            
            # Save artifact
            version = await artifact_service.save_artifact(
                app_name="integration_test_app",
                user_id="integration_test_user",
                session_id=session.id,
                filename="integration_test.txt",
                artifact=artifact
            )
            
            assert version == 0
            
            # Load artifact
            loaded_artifact = await artifact_service.load_artifact(
                app_name="integration_test_app",
                user_id="integration_test_user",
                session_id=session.id,
                filename="integration_test.txt"
            )
            
            assert loaded_artifact is not None
            assert loaded_artifact.inline_data.data == test_data
            
            # Create an event
            event = Event(
                invocation_id="integration_test_invocation",
                author="user",
                content=None
            )
            
            # Append event to session
            returned_event = await session_service.append_event(session, event)
            
            assert returned_event.invocation_id == "integration_test_invocation"
            
            # Retrieve updated session
            updated_session = await session_service.get_session(
                app_name="integration_test_app",
                user_id="integration_test_user",
                session_id=session.id
            )
            
            assert len(updated_session.events) == 1
            assert updated_session.events[0].invocation_id == "integration_test_invocation"
            
        finally:
            # Cleanup
            await session_service.cleanup()
            await artifact_service.cleanup()

    @pytest.mark.asyncio
    async def test_yaml_session_with_local_folder_artifact(self, temp_dir):
        """Test YAML session service working with local folder artifact service."""
        # Create services
        session_service = YamlFileSessionService(temp_dir)
        artifact_service = LocalFolderArtifactService(temp_dir)
        
        try:
            # Initialize services
            await session_service.initialize()
            await artifact_service.initialize()
            
            # Create a session
            session = await session_service.create_session(
                app_name="yaml_integration_test_app",
                user_id="yaml_integration_test_user",
                state={"theme": "light"}
            )
            
            assert session.id is not None
            
            # Create an artifact
            test_data = b"YAML integration test artifact content."
            blob = Blob(data=test_data, mime_type="text/plain")
            artifact = Part(inline_data=blob)
            
            # Save artifact
            version = await artifact_service.save_artifact(
                app_name="yaml_integration_test_app",
                user_id="yaml_integration_test_user",
                session_id=session.id,
                filename="yaml_integration_test.txt",
                artifact=artifact
            )
            
            assert version == 0
            
            # Load artifact
            loaded_artifact = await artifact_service.load_artifact(
                app_name="yaml_integration_test_app",
                user_id="yaml_integration_test_user",
                session_id=session.id,
                filename="yaml_integration_test.txt"
            )
            
            assert loaded_artifact is not None
            assert loaded_artifact.inline_data.data == test_data
            
            # Create an event
            event = Event(
                invocation_id="yaml_integration_test_invocation",
                author="user",
                content=None
            )
            
            # Append event to session
            returned_event = await session_service.append_event(session, event)
            
            assert returned_event.invocation_id == "yaml_integration_test_invocation"
            
            # Retrieve updated session
            updated_session = await session_service.get_session(
                app_name="yaml_integration_test_app",
                user_id="yaml_integration_test_user",
                session_id=session.id
            )
            
            assert len(updated_session.events) == 1
            assert updated_session.events[0].invocation_id == "yaml_integration_test_invocation"
            
        finally:
            # Cleanup
            await session_service.cleanup()
            await artifact_service.cleanup()

    @pytest.mark.asyncio
    async def test_cross_service_artifact_listing(self, temp_dir):
        """Test listing artifacts across different services."""
        # Create services
        session_service = YamlFileSessionService(temp_dir)
        artifact_service = LocalFolderArtifactService(temp_dir)
        
        try:
            # Initialize services
            await session_service.initialize()
            await artifact_service.initialize()
            
            # Create a session
            session = await session_service.create_session(
                app_name="cross_service_test_app",
                user_id="cross_service_test_user",
                state={"theme": "auto"}
            )
            
            # Create multiple artifacts
            test_data1 = b"First cross service test artifact."
            blob1 = Blob(data=test_data1, mime_type="text/plain")
            artifact1 = Part(inline_data=blob1)
            
            test_data2 = b"Second cross service test artifact."
            blob2 = Blob(data=test_data2, mime_type="text/plain")
            artifact2 = Part(inline_data=blob2)
            
            # Save artifacts
            await artifact_service.save_artifact(
                app_name="cross_service_test_app",
                user_id="cross_service_test_user",
                session_id=session.id,
                filename="artifact1.txt",
                artifact=artifact1
            )
            
            await artifact_service.save_artifact(
                app_name="cross_service_test_app",
                user_id="cross_service_test_user",
                session_id=session.id,
                filename="artifact2.txt",
                artifact=artifact2
            )
            
            # List artifacts
            artifact_keys = await artifact_service.list_artifact_keys(
                app_name="cross_service_test_app",
                user_id="cross_service_test_user",
                session_id=session.id
            )
            
            assert len(artifact_keys) == 2
            assert "artifact1.txt" in artifact_keys
            assert "artifact2.txt" in artifact_keys
            
        finally:
            # Cleanup
            await session_service.cleanup()
            await artifact_service.cleanup()