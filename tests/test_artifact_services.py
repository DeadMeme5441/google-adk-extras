#!/usr/bin/env python3
"""Simple test to verify artifact service implementations."""

import asyncio
import sys
import os
import tempfile
import shutil

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from google.genai import types
from custom_adk_services.artifacts import (
    SQLArtifactService,
    MongoArtifactService,
    LocalFolderArtifactService,
    S3ArtifactService
)


async def test_local_folder_artifact_service():
    """Test the local folder artifact service."""
    print("Testing Local Folder Artifact Service...")
    
    # Create a temporary directory for test artifacts
    temp_dir = tempfile.mkdtemp(prefix="adk_test_")
    
    try:
        # Initialize service
        service = LocalFolderArtifactService(temp_dir)
        await service.initialize()
        
        # Create a test artifact (simple text file)
        test_data = b"Hello, World! This is a test artifact."
        blob = types.Blob(data=test_data, mime_type="text/plain")
        artifact = types.Part(inline_data=blob)
        
        # Save artifact
        version = await service.save_artifact(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session",
            filename="test.txt",
            artifact=artifact
        )
        print(f"✓ Saved artifact with version: {version}")
        
        # Load artifact
        loaded_artifact = await service.load_artifact(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session",
            filename="test.txt"
        )
        print(f"✓ Loaded artifact: {loaded_artifact is not None}")
        
        # Verify data integrity
        if loaded_artifact and loaded_artifact.inline_data:
            assert loaded_artifact.inline_data.data == test_data
            assert loaded_artifact.inline_data.mime_type == "text/plain"
            print("✓ Data integrity verified")
        
        # List artifact keys
        keys = await service.list_artifact_keys(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session"
        )
        print(f"✓ Found artifact keys: {keys}")
        
        # List versions
        versions = await service.list_versions(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session",
            filename="test.txt"
        )
        print(f"✓ Found versions: {versions}")
        
        # Save another version
        updated_data = b"Updated content for the artifact."
        updated_blob = types.Blob(data=updated_data, mime_type="text/plain")
        updated_artifact = types.Part(inline_data=updated_blob)
        
        new_version = await service.save_artifact(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session",
            filename="test.txt",
            artifact=updated_artifact
        )
        print(f"✓ Saved updated artifact with version: {new_version}")
        
        # Load specific version
        loaded_v0 = await service.load_artifact(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session",
            filename="test.txt",
            version=0
        )
        print(f"✓ Loaded version 0: {loaded_v0 is not None}")
        
        # Load latest version (should be version 1)
        loaded_latest = await service.load_artifact(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session",
            filename="test.txt"
        )
        print(f"✓ Loaded latest version: {loaded_latest is not None}")
        
        # Verify latest version has updated content
        if loaded_latest and loaded_latest.inline_data:
            assert loaded_latest.inline_data.data == updated_data
            print("✓ Latest version has updated content")
        
        # Delete artifact
        await service.delete_artifact(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session",
            filename="test.txt"
        )
        print("✓ Deleted artifact")
        
        # Verify deletion
        deleted_artifact = await service.load_artifact(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session",
            filename="test.txt"
        )
        assert deleted_artifact is None
        print("✓ Artifact deletion verified")
        
        # Cleanup
        await service.cleanup()
        shutil.rmtree(temp_dir)
        print("✓ Local Folder Artifact Service tests passed")
        
    except Exception as e:
        # Cleanup on error
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        raise e


async def test_sql_artifact_service():
    """Test the SQL artifact service."""
    print("\nTesting SQL Artifact Service...")
    
    # Use SQLite in-memory database for testing
    service = SQLArtifactService("sqlite:///:memory:")
    
    try:
        # Initialize service
        await service.initialize()
        
        # Create a test artifact (simple text file)
        test_data = b"SQL test artifact content."
        blob = types.Blob(data=test_data, mime_type="text/plain")
        artifact = types.Part(inline_data=blob)
        
        # Save artifact
        version = await service.save_artifact(
            app_name="sql_test_app",
            user_id="sql_test_user",
            session_id="sql_test_session",
            filename="sql_test.txt",
            artifact=artifact
        )
        print(f"✓ Saved artifact with version: {version}")
        
        # Load artifact
        loaded_artifact = await service.load_artifact(
            app_name="sql_test_app",
            user_id="sql_test_user",
            session_id="sql_test_session",
            filename="sql_test.txt"
        )
        print(f"✓ Loaded artifact: {loaded_artifact is not None}")
        
        # Verify data integrity
        if loaded_artifact and loaded_artifact.inline_data:
            assert loaded_artifact.inline_data.data == test_data
            assert loaded_artifact.inline_data.mime_type == "text/plain"
            print("✓ Data integrity verified")
        
        # List artifact keys
        keys = await service.list_artifact_keys(
            app_name="sql_test_app",
            user_id="sql_test_user",
            session_id="sql_test_session"
        )
        print(f"✓ Found artifact keys: {keys}")
        
        # List versions
        versions = await service.list_versions(
            app_name="sql_test_app",
            user_id="sql_test_user",
            session_id="sql_test_session",
            filename="sql_test.txt"
        )
        print(f"✓ Found versions: {versions}")
        
        # Cleanup
        await service.cleanup()
        print("✓ SQL Artifact Service tests passed")
        
    except Exception as e:
        # Cleanup on error
        try:
            await service.cleanup()
        except:
            pass
        raise e


async def main():
    """Run all tests."""
    print("Running artifact service tests...\n")
    
    # Test local folder service
    await test_local_folder_artifact_service()
    
    # Test SQL service
    await test_sql_artifact_service()
    
    print("\nAll tests passed! ✓")


if __name__ == "__main__":
    asyncio.run(main())