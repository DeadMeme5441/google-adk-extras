"""End-to-end tests simulating real usage scenarios."""

import pytest
import os
import sys

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from google.adk.events.event import Event
from google.genai.types import Blob, Part, Content

try:
    from google_adk_extras.sessions import SQLSessionService
except Exception:
    SQLSessionService = None
try:
    from google_adk_extras.sessions import YamlFileSessionService
except Exception:
    YamlFileSessionService = None
try:
    from google_adk_extras.artifacts import SQLArtifactService
except Exception:
    SQLArtifactService = None
from google_adk_extras.artifacts import LocalFolderArtifactService


class TestEndToEndScenarios:
    """Test end-to-end scenarios simulating real usage."""

    @pytest.mark.asyncio
    async def test_document_management_workflow(self, temp_dir):
        """Test a complete document management workflow."""
        # Setup services
        if YamlFileSessionService is None:
            pytest.skip("pyyaml not installed")
        session_service = YamlFileSessionService(temp_dir)
        artifact_service = LocalFolderArtifactService(temp_dir)
        
        try:
            # Initialize services
            await session_service.initialize()
            await artifact_service.initialize()
            
            # 1. User creates a new document editing session
            session = await session_service.create_session(
                app_name="document_editor",
                user_id="user123",
                state={
                    "current_document": "report.md",
                    "editor_theme": "dark",
                    "word_count": 0
                }
            )
            
            # 2. User uploads initial document content
            initial_content = b"# Annual Report\n\nThis is the initial content of our annual report."
            blob = Blob(data=initial_content, mime_type="text/markdown")
            artifact = Part(inline_data=blob)
            
            version = await artifact_service.save_artifact(
                app_name="document_editor",
                user_id="user123",
                session_id=session.id,
                filename="report.md",
                artifact=artifact
            )
            
            # 3. User makes edits and saves a new version
            updated_content = b"# Annual Report\n\nThis is the updated content of our annual report.\n\n## Executive Summary\n\nHere's our executive summary."
            updated_blob = Blob(data=updated_content, mime_type="text/markdown")
            updated_artifact = Part(inline_data=updated_blob)
            
            new_version = await artifact_service.save_artifact(
                app_name="document_editor",
                user_id="user123",
                session_id=session.id,
                filename="report.md",
                artifact=updated_artifact
            )
            
            # 4. User wants to see version history
            versions = await artifact_service.list_versions(
                app_name="document_editor",
                user_id="user123",
                session_id=session.id,
                filename="report.md"
            )
            
            assert len(versions) == 2
            assert versions == [0, 1]
            
            # 5. User loads the latest version
            latest_artifact = await artifact_service.load_artifact(
                app_name="document_editor",
                user_id="user123",
                session_id=session.id,
                filename="report.md"
            )
            
            assert latest_artifact is not None
            assert latest_artifact.inline_data.data == updated_content
            
            # 6. User decides to revert to version 0
            original_artifact = await artifact_service.load_artifact(
                app_name="document_editor",
                user_id="user123",
                session_id=session.id,
                filename="report.md",
                version=0
            )
            
            assert original_artifact is not None
            assert original_artifact.inline_data.data == initial_content
            
            # 7. User uploads an image attachment
            image_data = b"fake image bytes for diagram.png"
            image_blob = Blob(data=image_data, mime_type="image/png")
            image_artifact = Part(inline_data=image_blob)
            
            image_version = await artifact_service.save_artifact(
                app_name="document_editor",
                user_id="user123",
                session_id=session.id,
                filename="diagram.png",
                artifact=image_artifact
            )
            
            # 8. User lists all documents in session
            document_keys = await artifact_service.list_artifact_keys(
                app_name="document_editor",
                user_id="user123",
                session_id=session.id
            )
            
            assert len(document_keys) == 2
            assert "report.md" in document_keys
            assert "diagram.png" in document_keys
            
            # 9. Session is updated with document statistics
            updated_session = await session_service.get_session(
                app_name="document_editor",
                user_id="user123",
                session_id=session.id
            )
            
            # Add an event to track document activity
            event = Event(
                invocation_id="document_edit_1",
                author="user",
                content=Content(parts=[Part(text="User edited document 'report.md'")])
            )
            
            await session_service.append_event(updated_session, event)
            
            # 10. Session is retrieved to check activity log
            final_session = await session_service.get_session(
                app_name="document_editor",
                user_id="user123",
                session_id=session.id
            )
            
            assert len(final_session.events) == 1
            assert final_session.events[0].invocation_id == "document_edit_1"
            
        finally:
            # Cleanup
            await session_service.cleanup()
            await artifact_service.cleanup()

    @pytest.mark.asyncio
    async def test_multi_user_collaboration_scenario(self, temp_dir):
        """Test a multi-user collaboration scenario."""
        # Setup services
        if SQLSessionService is None or SQLArtifactService is None:
            pytest.skip("SQLAlchemy not installed")
        session_service = SQLSessionService("sqlite:///:memory:")
        artifact_service = SQLArtifactService("sqlite:///:memory:")
        
        try:
            # Initialize services
            await session_service.initialize()
            await artifact_service.initialize()
            
            # Create shared project session
            project_session = await session_service.create_session(
                app_name="collaborative_editor",
                user_id="project_shared",
                session_id="project_alpha",
                state={
                    "project_name": "Project Alpha",
                    "members": ["alice", "bob", "charlie"],
                    "status": "active"
                }
            )
            
            # Save all artifacts with the same user ID for this test scenario
            # (In a real collaborative scenario, we'd use a shared user ID or project ID)
            
            # Alice uploads initial design document
            alice_design = b"# Design Document\n\nInitial design by Alice."
            alice_blob = Blob(data=alice_design, mime_type="text/markdown")
            alice_artifact = Part(inline_data=alice_blob)
            
            await artifact_service.save_artifact(
                app_name="collaborative_editor",
                user_id="project_shared",  # Use shared user ID
                session_id="project_alpha",
                filename="design.md",
                artifact=alice_artifact
            )
            
            # Bob reviews and adds comments
            bob_comments = b"Alice, great start! I've added some suggestions."
            bob_blob = Blob(data=bob_comments, mime_type="text/plain")
            bob_artifact = Part(inline_data=bob_blob)
            
            await artifact_service.save_artifact(
                app_name="collaborative_editor",
                user_id="project_shared",  # Use shared user ID
                session_id="project_alpha",
                filename="feedback.txt",
                artifact=bob_artifact
            )
            
            # Charlie uploads implementation code
            charlie_code = b"def hello():\n    print('Hello, World!')"
            charlie_blob = Blob(data=charlie_code, mime_type="text/x-python")
            charlie_artifact = Part(inline_data=charlie_blob)
            
            await artifact_service.save_artifact(
                app_name="collaborative_editor",
                user_id="project_shared",  # Use shared user ID
                session_id="project_alpha",
                filename="hello.py",
                artifact=charlie_artifact
            )
            
            # List all project artifacts using the shared user ID
            project_artifacts = await artifact_service.list_artifact_keys(
                app_name="collaborative_editor",
                user_id="project_shared",
                session_id="project_alpha"
            )
            
            assert len(project_artifacts) == 3
            assert "design.md" in project_artifacts
            assert "feedback.txt" in project_artifacts
            assert "hello.py" in project_artifacts
            
            # Alice updates her design based on feedback (using shared user ID)
            updated_design = b"# Design Document\n\nUpdated design by Alice.\n\n## Incorporating Bob's Feedback\n\nAddressed all suggestions."
            updated_alice_blob = Blob(data=updated_design, mime_type="text/markdown")
            updated_alice_artifact = Part(inline_data=updated_alice_blob)
            
            new_version = await artifact_service.save_artifact(
                app_name="collaborative_editor",
                user_id="project_shared",  # Use shared user ID
                session_id="project_alpha",
                filename="design.md",
                artifact=updated_alice_artifact
            )
            
            # Verify versioning worked
            design_versions = await artifact_service.list_versions(
                app_name="collaborative_editor",
                user_id="project_shared",
                session_id="project_alpha",
                filename="design.md"
            )
            
            assert len(design_versions) == 2
            assert design_versions == [0, 1]
            
        finally:
            # Cleanup
            await session_service.cleanup()
            await artifact_service.cleanup()

    @pytest.mark.asyncio
    async def test_backup_and_restore_scenario(self, temp_dir):
        """Test backup and restore scenario using file-based services."""
        # Setup services
        if YamlFileSessionService is None:
            pytest.skip("pyyaml not installed")
        session_service = YamlFileSessionService(temp_dir)
        artifact_service = LocalFolderArtifactService(temp_dir)
        
        try:
            # Initialize services
            await session_service.initialize()
            await artifact_service.initialize()
            
            # Create a session with multiple artifacts
            session = await session_service.create_session(
                app_name="backup_restore_app",
                user_id="backup_user",
                state={
                    "last_backup": "2025-01-01T00:00:00Z",
                    "backup_count": 0
                }
            )
            
            # Create multiple artifacts
            artifacts_data = {
                "document1.txt": b"First document content",
                "document2.txt": b"Second document content",
                "image1.png": b"Fake image data 1",
                "image2.png": b"Fake image data 2",
                "code.py": b"print('Hello, World!')"
            }
            
            # Save all artifacts
            for filename, data in artifacts_data.items():
                mime_type = "text/plain" if filename.endswith(".txt") else \
                           "image/png" if filename.endswith(".png") else "text/x-python"
                blob = Blob(data=data, mime_type=mime_type)
                artifact = Part(inline_data=blob)
                
                await artifact_service.save_artifact(
                    app_name="backup_restore_app",
                    user_id="backup_user",
                    session_id=session.id,
                    filename=filename,
                    artifact=artifact
                )
            
            # Verify all artifacts were saved
            saved_artifacts = await artifact_service.list_artifact_keys(
                app_name="backup_restore_app",
                user_id="backup_user",
                session_id=session.id
            )
            
            assert len(saved_artifacts) == 5
            for filename in artifacts_data.keys():
                assert filename in saved_artifacts
            
            # Load and verify each artifact
            for filename, original_data in artifacts_data.items():
                loaded_artifact = await artifact_service.load_artifact(
                    app_name="backup_restore_app",
                    user_id="backup_user",
                    session_id=session.id,
                    filename=filename
                )
                
                assert loaded_artifact is not None
                assert loaded_artifact.inline_data.data == original_data
            
            # Update session state to reflect backup
            session = await session_service.get_session(
                app_name="backup_restore_app",
                user_id="backup_user",
                session_id=session.id
            )
            
            session.state["last_backup"] = "2025-01-02T12:00:00Z"
            session.state["backup_count"] = 1
            
            # In a real scenario, we'd save this updated session state
            # For now, we'll just verify we can retrieve it
            
            # Add an event for the backup operation
            backup_event = Event(
                invocation_id="backup_operation_1",
                author="system",
                content=Content(parts=[Part(text="Performed backup of 5 artifacts")])
            )
            
            await session_service.append_event(session, backup_event)
            
            # Verify session has the event
            updated_session = await session_service.get_session(
                app_name="backup_restore_app",
                user_id="backup_user",
                session_id=session.id
            )
            
            assert len(updated_session.events) == 1
            assert updated_session.events[0].invocation_id == "backup_operation_1"
            
        finally:
            # Cleanup
            await session_service.cleanup()
            await artifact_service.cleanup()
