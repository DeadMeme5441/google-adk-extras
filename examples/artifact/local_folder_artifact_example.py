"""
Local Folder Artifact Service Example
=====================================

This example demonstrates how to use the LocalFolderArtifactService with Google ADK.
"""

import asyncio
import tempfile
from pathlib import Path

from google.genai import types

# Import our custom artifact service
from google_adk_extras.artifacts import LocalFolderArtifactService


async def main():
    """Demonstrate local folder artifact service functionality."""
    
    print("=== Local Folder Artifact Service Example ===")
    
    # Create a temporary directory for artifact files
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Initialize the local folder artifact service
        service = LocalFolderArtifactService(tmp_dir)
        await service.initialize()
        print(f"Initialized local folder artifact service with directory: {tmp_dir}")
        
        # Save a text artifact
        text_content = "Hello, this is a sample text artifact stored in local files!"
        text_part = types.Part.from_text(text=text_content)
        version = await service.save_artifact(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456",
            filename="local_sample.txt",
            artifact=text_part
        )
        print(f"Saved text artifact with version: {version}")
        
        # Save a binary artifact
        binary_content = b"This is binary data stored in local files"
        binary_part = types.Part(inline_data=types.Blob(data=binary_content, mime_type="application/octet-stream"))
        version = await service.save_artifact(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456",
            filename="local_binary.dat",
            artifact=binary_part
        )
        print(f"Saved binary artifact with version: {version}")
        
        # Load the text artifact
        loaded_artifact = await service.load_artifact(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456",
            filename="local_sample.txt"
        )
        print(f"Loaded text artifact: {loaded_artifact.parts[0].text}")
        
        # Load the binary artifact
        loaded_binary = await service.load_artifact(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456",
            filename="local_binary.dat"
        )
        print(f"Loaded binary artifact size: {len(loaded_binary.inline_data.data)} bytes")
        
        # List artifact keys
        keys = await service.list_artifact_keys(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456"
        )
        print(f"Artifact keys: {keys}")
        
        # List versions
        versions = await service.list_versions(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456",
            filename="local_sample.txt"
        )
        print(f"Versions for 'local_sample.txt': {versions}")
        
        # Clean up
        await service.cleanup()
        print("Cleaned up local folder artifact service")
    
    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())