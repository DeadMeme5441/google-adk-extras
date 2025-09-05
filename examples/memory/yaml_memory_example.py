"""
YAML File Memory Service Example
================================

This example demonstrates how to use the YamlFileMemoryService with Google ADK.
"""

import asyncio
import tempfile
from datetime import datetime

from google.genai import types
from google.adk.sessions.session import Session
from google.adk.events.event import Event

# Import our custom memory service
from google_adk_extras.memory import YamlFileMemoryService


async def main():
    """Demonstrate YAML file memory service functionality."""
    
    print("=== YAML File Memory Service Example ===")
    
    # Create a temporary directory for memory files
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Initialize the YAML file memory service
        service = YamlFileMemoryService(tmp_dir)
        await service.initialize()
        print(f"Initialized YAML file memory service with directory: {tmp_dir}")
        
        # Create a sample session with events
        conversation_events = [
            Event(
                id="event1",
                author="user",
                timestamp=datetime.now().timestamp(),
                content=types.Content(parts=[types.Part.from_text(text="What's the capital of France?")])
            ),
            Event(
                id="event2",
                author="assistant",
                timestamp=datetime.now().timestamp() + 1,
                content=types.Content(parts=[types.Part.from_text(text="The capital of France is Paris.")])
            ),
            Event(
                id="event3",
                author="user",
                timestamp=datetime.now().timestamp() + 2,
                content=types.Content(parts=[types.Part.from_text(text="Thanks! What about Germany?")])
            ),
        ]
        
        session = Session(
            id="geography_session_001",
            app_name="education_app",
            user_id="student_11111",
            events=conversation_events
        )
        
        # Add session to memory
        await service.add_session_to_memory(session)
        print("Added session to YAML file memory")
        
        # Search for relevant memories
        response = await service.search_memory(
            app_name="education_app",
            user_id="student_11111",
            query="capital France"
        )
        print(f"Found {len(response.memories)} relevant memories")
        if response.memories:
            print(f"First memory content: {response.memories[0].content.parts[0].text}")
        
        # Try a different search query
        response = await service.search_memory(
            app_name="education_app",
            user_id="student_11111",
            query="Paris"
        )
        print(f"Found {len(response.memories)} memories for 'Paris'")
        if response.memories:
            print(f"First Paris memory: {response.memories[0].content.parts[0].text}")
        
        # Clean up
        await service.cleanup()
        print("Cleaned up YAML file memory service")
    
    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())