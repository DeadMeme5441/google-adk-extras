"""
Artifact Services Example
========================

This example demonstrates how to use all custom artifact services with Google ADK.

The example shows:
1. Saving artifacts with different storage backends
2. Loading artifacts by filename and version
3. Listing artifact keys and versions
4. Deleting artifacts
"""

import asyncio
import tempfile
import os
from pathlib import Path

from google.genai import types

# Import our custom artifact services
from google_adk_extras.artifacts import (
    SQLArtifactService,
    MongoArtifactService,
    LocalFolderArtifactService,
    S3ArtifactService
)


async def demonstrate_artifact_services():
    """Demonstrate all custom artifact services."""
    
    # Sample data for artifacts
    text_content = "Hello, this is a sample text artifact!"
    binary_content = b"This is binary data for an artifact"
    
    # 1. SQL Artifact Service Example
    print("=== SQL Artifact Service Example ===")
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        tmp_file.close()
        try:
            sql_service = SQLArtifactService(f"sqlite:///{tmp_file.name}")
            await sql_service.initialize()
            
            # Save an artifact
            text_part = types.Part.from_text(text=text_content)
            version = await sql_service.save_artifact(
                app_name="example_app",
                user_id="user_123",
                session_id="session_456",
                filename="sample.txt",
                artifact=text_part
            )
            print(f"Saved text artifact with version: {version}")
            
            # Save another version
            updated_text_part = types.Part.from_text(text=text_content + " (updated)")
            version = await sql_service.save_artifact(
                app_name="example_app",
                user_id="user_123",
                session_id="session_456",
                filename="sample.txt",
                artifact=updated_text_part
            )
            print(f"Saved updated text artifact with version: {version}")
            
            # Load latest version
            loaded_artifact = await sql_service.load_artifact(
                app_name="example_app",
                user_id="user_123",
                session_id="session_456",
                filename="sample.txt"
            )
            print(f"Loaded artifact text: {loaded_artifact.parts[0].text}")
            
            # Load specific version
            specific_artifact = await sql_service.load_artifact(
                app_name="example_app",
                user_id="user_123",
                session_id="session_456",
                filename="sample.txt",
                version=0
            )
            print(f"Loaded version 0 text: {specific_artifact.parts[0].text}")
            
            # List versions
            versions = await sql_service.list_versions(
                app_name="example_app",
                user_id="user_123",
                session_id="session_456",
                filename="sample.txt"
            )
            print(f"Available versions: {versions}")
            
            # List artifact keys
            keys = await sql_service.list_artifact_keys(
                app_name="example_app",
                user_id="user_123",
                session_id="session_456"
            )
            print(f"Artifact keys: {keys}")
            
            await sql_service.cleanup()
        finally:
            os.unlink(tmp_file.name)
    
    # 2. MongoDB Artifact Service Example
    print("\n=== MongoDB Artifact Service Example ===")
    # Note: This requires a running MongoDB instance
    try:
        mongo_service = MongoArtifactService("mongodb://localhost:27017", "adk_artifacts_example")
        await mongo_service.initialize()
        
        # Save an artifact
        binary_part = types.Part(inline_data=types.Blob(data=binary_content, mime_type="application/octet-stream"))
        version = await mongo_service.save_artifact(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456",
            filename="binary.dat",
            artifact=binary_part
        )
        print(f"Saved binary artifact with version: {version}")
        
        # Load the artifact
        loaded_artifact = await mongo_service.load_artifact(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456",
            filename="binary.dat"
        )
        print(f"Loaded binary artifact size: {len(loaded_artifact.inline_data.data)} bytes")
        
        await mongo_service.cleanup()
    except Exception as e:
        print(f"MongoDB example skipped (requires running MongoDB): {e}")
    
    # 3. Local Folder Artifact Service Example
    print("\n=== Local Folder Artifact Service Example ===")
    with tempfile.TemporaryDirectory() as tmp_dir:
        folder_service = LocalFolderArtifactService(tmp_dir)
        await folder_service.initialize()
        
        # Save an artifact
        text_part = types.Part.from_text(text=text_content)
        version = await folder_service.save_artifact(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456",
            filename="local_file.txt",
            artifact=text_part
        )
        print(f"Saved local artifact with version: {version}")
        
        # Load the artifact
        loaded_artifact = await folder_service.load_artifact(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456",
            filename="local_file.txt"
        )
        print(f"Loaded local artifact text: {loaded_artifact.parts[0].text}")
        
        # List artifact keys
        keys = await folder_service.list_artifact_keys(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456"
        )
        print(f"Local artifact keys: {keys}")
        
        await folder_service.cleanup()
    
    # 4. S3 Artifact Service Example
    print("\n=== S3 Artifact Service Example ===")
    # Note: This requires AWS credentials and S3 bucket
    try:
        # You would need to provide actual AWS credentials and bucket name
        s3_service = S3ArtifactService(
            bucket_name="your-bucket-name",
            region_name="us-west-2"
        )
        await s3_service.initialize()
        print("S3 service initialized (requires AWS credentials)")
        await s3_service.cleanup()
    except Exception as e:
        print(f"S3 example skipped (requires AWS credentials): {e}")
    
    print("\n=== Artifact Services Example Complete ===")


async def main():
    """Run all artifact service examples."""
    await demonstrate_artifact_services()


if __name__ == "__main__":
    asyncio.run(main())