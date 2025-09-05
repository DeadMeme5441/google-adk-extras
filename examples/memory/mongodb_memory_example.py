"""
MongoDB Memory Service Example
==============================

This example demonstrates how to use the MongoMemoryService with Google ADK.

Note: This requires a running MongoDB instance.
"""

import asyncio
from datetime import datetime

from google.genai import types
from google.adk.sessions.session import Session
from google.adk.events.event import Event

# Import our custom memory service
from google_adk_extras.memory import MongoMemoryService


async def main():
    """Demonstrate MongoDB memory service functionality."""
    
    print("=== MongoDB Memory Service Example ===")
    
    try:
        # Initialize the MongoDB memory service
        service = MongoMemoryService("mongodb://localhost:27017", "adk_memory_example")
        await service.initialize()
        print("Initialized MongoDB memory service")
        
        # Create a sample session with events
        conversation_events = [
            Event(
                id="event1",
                author="user",
                timestamp=datetime.now().timestamp(),
                content=types.Content(parts=[types.Part.from_text(text="What's the weather like today in New York?")])
            ),
            Event(
                id="event2",
                author="assistant",
                timestamp=datetime.now().timestamp() + 1,
                content=types.Content(parts=[types.Part.from_text(text="It's currently sunny and 75°F in New York City.")])
            ),
            Event(
                id="event3",
                author="user",
                timestamp=datetime.now().timestamp() + 2,
                content=types.Content(parts=[types.Part.from_text(text="Great! I'm planning to visit Central Park. Any recommendations?")])
            ),
        ]
        
        session = Session(
            id="weather_session_001",
            app_name="travel_assistant",
            user_id="traveler_67890",
            events=conversation_events
        )
        
        # Add session to memory
        await service.add_session_to_memory(session)
        print("Added session to MongoDB memory")
        
        # Search for relevant memories
        response = await service.search_memory(
            app_name="travel_assistant",
            user_id="traveler_67890",
            query="weather New York"
        )
        print(f"Found {len(response.memories)} relevant memories")
        if response.memories:
            print(f"First memory content: {response.memories[0].content.parts[0].text}")
        
        # Try a different search query
        response = await service.search_memory(
            app_name="travel_assistant",
            user_id="traveler_67890",
            query="Central Park"
        )
        print(f"Found {len(response.memories)} memories for 'Central Park'")
        if response.memories:
            print(f"First Central Park memory: {response.memories[0].content.parts[0].text}")
        
        # Clean up
        await service.cleanup()
        print("Cleaned up MongoDB memory service")
        
    except Exception as e:
        print(f"MongoDB example skipped (requires running MongoDB): {e}")
    
    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())