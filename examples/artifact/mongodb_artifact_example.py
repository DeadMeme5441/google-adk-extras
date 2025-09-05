"""
MongoDB Artifact Service Example
================================

This example demonstrates how to use the MongoArtifactService with Google ADK.

Note: This requires a running MongoDB instance.
"""

import asyncio
from google.genai import types

# Import our custom artifact service
from google_adk_extras.artifacts import MongoArtifactService


async def main():
    """Demonstrate MongoDB artifact service functionality."""
    
    print("=== MongoDB Artifact Service Example ===")
    
    try:
        # Initialize the MongoDB artifact service
        service = MongoArtifactService("mongodb://localhost:27017", "adk_artifacts_example")
        await service.initialize()
        print("Initialized MongoDB artifact service")
        
        # Save a text artifact
        text_content = "Hello, this is a sample text artifact stored in MongoDB!"
        text_part = types.Part.from_text(text=text_content)
        version = await service.save_artifact(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456",
            filename="mongodb_sample.txt",
            artifact=text_part
        )
        print(f"Saved text artifact with version: {version}")
        
        # Save a binary artifact
        binary_content = b"This is binary data stored in MongoDB"
        binary_part = types.Part(inline_data=types.Blob(data=binary_content, mime_type="application/octet-stream"))
        version = await service.save_artifact(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456",
            filename="mongodb_binary.dat",
            artifact=binary_part
        )
        print(f"Saved binary artifact with version: {version}")
        
        # Load the text artifact
        loaded_artifact = await service.load_artifact(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456",
            filename="mongodb_sample.txt"
        )
        print(f"Loaded text artifact: {loaded_artifact.parts[0].text}")
        
        # List artifact keys
        keys = await service.list_artifact_keys(
            app_name="example_app",
            user_id="user_123",
            session_id="session_456"
        )
        print(f"Artifact keys: {keys}")
        
        # Clean up
        await service.cleanup()
        print("Cleaned up MongoDB artifact service")
        
    except Exception as e:
        print(f"MongoDB example skipped (requires running MongoDB): {e}")
    
    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())