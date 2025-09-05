"""
SQL Artifact Service Example
============================

This example demonstrates how to use the SQLArtifactService with Google ADK.
"""

import asyncio
import tempfile
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from google.genai import types

# Import our custom artifact service
from google_adk_extras.artifacts import SQLArtifactService


async def main():
    """Demonstrate SQL artifact service functionality."""
    
    print("=== SQL Artifact Service Example ===")
    
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        tmp_file.close()
        try:
            # Initialize the SQL artifact service
            service = SQLArtifactService(f"sqlite:///{tmp_file.name}")
            await service.initialize()
            print(f"Initialized SQL artifact service with database: {tmp_file.name}")
            
            # Save a text artifact
            text_content = "Hello, this is a sample text artifact!"
            # For SQL artifact service, we need to use inline_data
            text_blob = types.Blob(data=text_content.encode('utf-8'), mime_type="text/plain")
            text_part = types.Part(inline_data=text_blob)
            version = await service.save_artifact(
                app_name="example_app",
                user_id="user_123",
                session_id="session_456",
                filename="sample.txt",
                artifact=text_part
            )
            print(f"Saved text artifact with version: {version}")
            
            # Save a binary artifact
            binary_content = b"This is binary data for an artifact"
            binary_part = types.Part(inline_data=types.Blob(data=binary_content, mime_type="application/octet-stream"))
            version = await service.save_artifact(
                app_name="example_app",
                user_id="user_123",
                session_id="session_456",
                filename="binary.dat",
                artifact=binary_part
            )
            print(f"Saved binary artifact with version: {version}")
            
            # Load the text artifact
            loaded_artifact = await service.load_artifact(
                app_name="example_app",
                user_id="user_123",
                session_id="session_456",
                filename="sample.txt"
            )
            # For SQL artifact service, we need to decode the data
            text_content = loaded_artifact.inline_data.data.decode('utf-8')
            print(f"Loaded text artifact: {text_content}")
            
            # Load the binary artifact
            loaded_binary = await service.load_artifact(
                app_name="example_app",
                user_id="user_123",
                session_id="session_456",
                filename="binary.dat"
            )
            print(f"Loaded binary artifact size: {len(loaded_binary.inline_data.data)} bytes")
            
            # List artifact keys
            keys = await service.list_artifact_keys(
                app_name="example_app",
                user_id="user_123",
                session_id="session_456"
            )
            print(f"Artifact keys: {keys}")
            
            # List versions for text artifact
            versions = await service.list_versions(
                app_name="example_app",
                user_id="user_123",
                session_id="session_456",
                filename="sample.txt"
            )
            print(f"Versions for 'sample.txt': {versions}")
            
            # Clean up
            await service.cleanup()
            print("Cleaned up SQL artifact service")
            
        finally:
            # Remove the temporary database file
            os.unlink(tmp_file.name)
    
    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())