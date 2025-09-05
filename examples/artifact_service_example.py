#!/usr/bin/env python3
"""Example of using custom artifact services."""

import asyncio
import sys
import os
import tempfile

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from google.genai import types
from google_adk_extras.artifacts import (
    SQLArtifactService,
    LocalFolderArtifactService
)


async def example_local_folder_artifact_service():
    """Example of using LocalFolderArtifactService."""
    print("=== Local Folder Artifact Service Example ===")
    
    # Create a temporary directory for artifacts
    temp_dir = tempfile.mkdtemp(prefix="adk_example_")
    
    # Initialize service
    service = LocalFolderArtifactService(temp_dir)
    
    try:
        # Initialize the service
        await service.initialize()
        print(f"✓ Service initialized with directory: {temp_dir}")
        
        # Create a text artifact
        text_data = b"This is a sample text file stored as an artifact."
        text_blob = types.Blob(data=text_data, mime_type="text/plain")
        text_artifact = types.Part(inline_data=text_blob)
        
        # Save the artifact
        version = await service.save_artifact(
            app_name="my_app",
            user_id="user123",
            session_id="session456",
            filename="sample.txt",
            artifact=text_artifact
        )
        print(f"✓ Saved text artifact with version: {version}")
        
        # Create an image artifact
        image_data = b"fake image data"  # In reality, this would be actual image bytes
        image_blob = types.Blob(data=image_data, mime_type="image/png")
        image_artifact = types.Part(inline_data=image_blob)
        
        # Save the image artifact
        image_version = await service.save_artifact(
            app_name="my_app",
            user_id="user123",
            session_id="session456",
            filename="sample.png",
            artifact=image_artifact
        )
        print(f"✓ Saved image artifact with version: {image_version}")
        
        # Load the text artifact
        loaded_artifact = await service.load_artifact(
            app_name="my_app",
            user_id="user123",
            session_id="session456",
            filename="sample.txt"
        )
        print(f"✓ Loaded text artifact: {loaded_artifact is not None}")
        
        if loaded_artifact and loaded_artifact.inline_data:
            print(f"  Content: {loaded_artifact.inline_data.data.decode('utf-8')}")
            print(f"  MIME type: {loaded_artifact.inline_data.mime_type}")
        
        # List all artifacts
        artifact_keys = await service.list_artifact_keys(
            app_name="my_app",
            user_id="user123",
            session_id="session456"
        )
        print(f"✓ Found {len(artifact_keys)} artifacts: {artifact_keys}")
        
        # List versions of text artifact
        versions = await service.list_versions(
            app_name="my_app",
            user_id="user123",
            session_id="session456",
            filename="sample.txt"
        )
        print(f"✓ Text artifact has {len(versions)} versions: {versions}")
        
        # Delete an artifact
        await service.delete_artifact(
            app_name="my_app",
            user_id="user123",
            session_id="session456",
            filename="sample.png"
        )
        print("✓ Deleted image artifact")
        
        # Verify deletion
        remaining_keys = await service.list_artifact_keys(
            app_name="my_app",
            user_id="user123",
            session_id="session456"
        )
        print(f"✓ Remaining artifacts: {remaining_keys}")
        
        # Cleanup
        await service.cleanup()
        print("✓ Service cleaned up")
        
    finally:
        # Clean up temporary directory
        import shutil
        shutil.rmtree(temp_dir)
        
    print("Local Folder Artifact Service example completed!\n")


async def example_sql_artifact_service():
    """Example of using SQLArtifactService."""
    print("=== SQL Artifact Service Example ===")
    
    # Initialize service with SQLite database
    service = SQLArtifactService("sqlite:///./example_artifacts.db")
    
    try:
        # Initialize the service
        await service.initialize()
        print("✓ SQL service initialized with SQLite database")
        
        # Create a document artifact
        doc_data = b"# Sample Document\n\nThis is a sample Markdown document."
        doc_blob = types.Blob(data=doc_data, mime_type="text/markdown")
        doc_artifact = types.Part(inline_data=doc_blob)
        
        # Save the artifact
        version = await service.save_artifact(
            app_name="docs_app",
            user_id="doc_user",
            session_id="doc_session",
            filename="README.md",
            artifact=doc_artifact
        )
        print(f"✓ Saved document artifact with version: {version}")
        
        # Load the artifact
        loaded_artifact = await service.load_artifact(
            app_name="docs_app",
            user_id="doc_user",
            session_id="doc_session",
            filename="README.md"
        )
        print(f"✓ Loaded document artifact: {loaded_artifact is not None}")
        
        if loaded_artifact and loaded_artifact.inline_data:
            print(f"  Content: {loaded_artifact.inline_data.data.decode('utf-8')[:50]}...")
            print(f"  MIME type: {loaded_artifact.inline_data.mime_type}")
        
        # List all artifacts
        artifact_keys = await service.list_artifact_keys(
            app_name="docs_app",
            user_id="doc_user",
            session_id="doc_session"
        )
        print(f"✓ Found {len(artifact_keys)} artifacts: {artifact_keys}")
        
        # Cleanup
        await service.cleanup()
        print("✓ SQL service cleaned up")
        
    finally:
        # Clean up database file
        import os
        if os.path.exists("example_artifacts.db"):
            os.remove("example_artifacts.db")
        
    print("SQL Artifact Service example completed!\n")


async def main():
    """Run examples."""
    # Run local folder example
    await example_local_folder_artifact_service()
    
    # Run SQL example
    await example_sql_artifact_service()
    
    print("All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())