"""Unit tests for artifact services using pytest."""

import pytest

from google.genai.types import Blob, Part

from google_adk_extras.artifacts.base_custom_artifact_service import BaseCustomArtifactService
from google_adk_extras.artifacts.local_folder_artifact_service import LocalFolderArtifactService
try:
    from google_adk_extras.artifacts.sql_artifact_service import SQLArtifactService
except Exception:
    SQLArtifactService = None


class TestBaseCustomArtifactService:
    """Test the base custom artifact service class."""

    @pytest.mark.asyncio
    async def test_initialize_and_cleanup(self):
        """Test initialization and cleanup methods."""

        class TestService(BaseCustomArtifactService):
            async def _initialize_impl(self):
                pass

            async def _cleanup_impl(self):
                pass

            async def _save_artifact_impl(self, *, app_name, user_id, session_id, filename, artifact):
                pass

            async def _load_artifact_impl(self, *, app_name, user_id, session_id, filename, version=None):
                pass

            async def _list_artifact_keys_impl(self, *, app_name, user_id, session_id):
                pass

            async def _delete_artifact_impl(self, *, app_name, user_id, session_id, filename):
                pass

            async def _list_versions_impl(self, *, app_name, user_id, session_id, filename):
                pass

        service = TestService()
        assert not service._initialized

        # Test initialization
        await service.initialize()
        assert service._initialized

        # Test cleanup
        await service.cleanup()
        assert not service._initialized


class TestLocalFolderArtifactService:
    """Test the local folder artifact service."""

    @pytest.mark.asyncio
    async def test_initialization(self, temp_dir):
        """Test that the local folder service initializes correctly."""
        service = LocalFolderArtifactService(temp_dir)
        await service.initialize()
        assert service._initialized
        await service.cleanup()

    @pytest.mark.asyncio
    async def test_save_and_load_artifact(self, temp_dir, sample_text_blob):
        """Test saving and loading an artifact."""
        service = LocalFolderArtifactService(temp_dir)
        await service.initialize()

        try:
            # Save artifact
            version = await service.save_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                artifact=sample_text_blob
            )

            assert version == 0

            # Load artifact
            loaded_artifact = await service.load_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt"
            )

            assert loaded_artifact is not None
            assert loaded_artifact.inline_data is not None
            assert loaded_artifact.inline_data.data == sample_text_blob.inline_data.data
            assert loaded_artifact.inline_data.mime_type == sample_text_blob.inline_data.mime_type

        finally:
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_list_artifact_keys(self, temp_dir, sample_text_blob, sample_image_blob):
        """Test listing artifact keys."""
        service = LocalFolderArtifactService(temp_dir)
        await service.initialize()

        try:
            # Save multiple artifacts
            await service.save_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                artifact=sample_text_blob
            )

            await service.save_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.png",
                artifact=sample_image_blob
            )

            # List artifact keys
            keys = await service.list_artifact_keys(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session"
            )

            assert len(keys) == 2
            assert "test.txt" in keys
            assert "test.png" in keys

        finally:
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_delete_artifact(self, temp_dir, sample_text_blob):
        """Test deleting an artifact."""
        service = LocalFolderArtifactService(temp_dir)
        await service.initialize()

        try:
            # Save artifact
            await service.save_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                artifact=sample_text_blob
            )

            # Verify artifact exists
            loaded_artifact = await service.load_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt"
            )
            assert loaded_artifact is not None

            # Delete artifact
            await service.delete_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt"
            )

            # Verify artifact is deleted
            deleted_artifact = await service.load_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt"
            )
            assert deleted_artifact is None

        finally:
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_versioning(self, temp_dir, sample_text_blob):
        """Test artifact versioning."""
        service = LocalFolderArtifactService(temp_dir)
        await service.initialize()

        try:
            # Save first version
            version1 = await service.save_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                artifact=sample_text_blob
            )

            assert version1 == 0

            # Modify and save second version
            updated_blob_data = b"Updated content for the artifact."
            updated_blob = Blob(data=updated_blob_data, mime_type="text/plain")
            updated_artifact = Part(inline_data=updated_blob)

            version2 = await service.save_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                artifact=updated_artifact
            )

            assert version2 == 1

            # List versions
            versions = await service.list_versions(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt"
            )

            assert len(versions) == 2
            assert versions == [0, 1]

            # Load specific versions
            v0 = await service.load_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                version=0
            )

            v1 = await service.load_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                version=1
            )

            assert v0 is not None
            assert v1 is not None
            assert v0.inline_data.data == sample_text_blob.inline_data.data
            assert v1.inline_data.data == updated_blob_data

            # Load latest version (should be v1)
            latest = await service.load_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt"
            )

            assert latest is not None
            assert latest.inline_data.data == updated_blob_data

        finally:
            await service.cleanup()


import pytest as _pytest

class TestSQLArtifactService:
    """Test the SQL artifact service."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test that the SQL service initializes correctly."""
        if SQLArtifactService is None:
            _pytest.skip("SQLAlchemy not installed")
        service = SQLArtifactService("sqlite:///:memory:")
        await service.initialize()
        assert service._initialized
        await service.cleanup()

    @pytest.mark.asyncio
    async def test_save_and_load_artifact(self, sample_text_blob):
        """Test saving and loading an artifact."""
        if SQLArtifactService is None:
            _pytest.skip("SQLAlchemy not installed")
        service = SQLArtifactService("sqlite:///:memory:")
        await service.initialize()

        try:
            # Save artifact
            version = await service.save_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                artifact=sample_text_blob
            )

            assert version == 0

            # Load artifact
            loaded_artifact = await service.load_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt"
            )

            assert loaded_artifact is not None
            assert loaded_artifact.inline_data is not None
            assert loaded_artifact.inline_data.data == sample_text_blob.inline_data.data
            assert loaded_artifact.inline_data.mime_type == sample_text_blob.inline_data.mime_type

        finally:
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_list_artifact_keys(self, sample_text_blob, sample_image_blob):
        """Test listing artifact keys."""
        if SQLArtifactService is None:
            _pytest.skip("SQLAlchemy not installed")
        service = SQLArtifactService("sqlite:///:memory:")
        await service.initialize()

        try:
            # Save multiple artifacts
            await service.save_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                artifact=sample_text_blob
            )

            await service.save_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.png",
                artifact=sample_image_blob
            )

            # List artifact keys
            keys = await service.list_artifact_keys(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session"
            )

            assert len(keys) == 2
            assert "test.txt" in keys
            assert "test.png" in keys

        finally:
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_delete_artifact(self, sample_text_blob):
        """Test deleting an artifact."""
        service = SQLArtifactService("sqlite:///:memory:")
        await service.initialize()

        try:
            # Save artifact
            await service.save_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                artifact=sample_text_blob
            )

            # Verify artifact exists
            loaded_artifact = await service.load_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt"
            )
            assert loaded_artifact is not None

            # Delete artifact
            await service.delete_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt"
            )

            # Verify artifact is deleted
            deleted_artifact = await service.load_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt"
            )
            assert deleted_artifact is None

        finally:
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_versioning(self, sample_text_blob):
        """Test artifact versioning."""
        service = SQLArtifactService("sqlite:///:memory:")
        await service.initialize()

        try:
            # Save first version
            version1 = await service.save_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                artifact=sample_text_blob
            )

            assert version1 == 0

            # Modify and save second version
            updated_blob_data = b"Updated content for the artifact."
            updated_blob = Blob(data=updated_blob_data, mime_type="text/plain")
            updated_artifact = Part(inline_data=updated_blob)

            version2 = await service.save_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                artifact=updated_artifact
            )

            assert version2 == 1

            # List versions
            versions = await service.list_versions(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt"
            )

            assert len(versions) == 2
            assert versions == [0, 1]

            # Load specific versions
            v0 = await service.load_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                version=0
            )

            v1 = await service.load_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt",
                version=1
            )

            assert v0 is not None
            assert v1 is not None
            assert v0.inline_data.data == sample_text_blob.inline_data.data
            assert v1.inline_data.data == updated_blob_data

            # Load latest version (should be v1)
            latest = await service.load_artifact(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                filename="test.txt"
            )

            assert latest is not None
            assert latest.inline_data.data == updated_blob_data

        finally:
            await service.cleanup()
