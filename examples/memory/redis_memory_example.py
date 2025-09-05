"""
Redis Memory Service Example
============================

This example demonstrates how to use the RedisMemoryService with Google ADK.

Note: This requires a running Redis instance.
"""

import asyncio
from datetime import datetime

from google.genai import types
from google.adk.sessions.session import Session
from google.adk.events.event import Event

# Import our custom memory service
from google_adk_extras.memory import RedisMemoryService


async def main():
    """Demonstrate Redis memory service functionality."""
    
    print("=== Redis Memory Service Example ===")
    
    try:
        # Initialize the Redis memory service
        service = RedisMemoryService(host="localhost", port=6379, db=0)
        await service.initialize()
        print("Initialized Redis memory service")
        
        # Create a sample session with events
        conversation_events = [
            Event(
                id="event1",
                author="user",
                timestamp=datetime.now().timestamp(),
                content=types.Content(parts=[types.Part.from_text(text="Tell me a joke")])
            ),
            Event(
                id="event2",
                author="assistant",
                timestamp=datetime.now().timestamp() + 1,
                content=types.Content(parts=[types.Part.from_text(text="Why don't scientists trust atoms? Because they make up everything!")])
            ),
            Event(
                id="event3",
                author="user",
                timestamp=datetime.now().timestamp() + 2,
                content=types.Content(parts=[types.Part.from_text(text="Haha, that's funny! Tell me another one")])
            ),
        ]
        
        session = Session(
            id="joke_session_001",
            app_name="entertainment_app",
            user_id="user_54321",
            events=conversation_events
        )
        
        # Add session to memory
        await service.add_session_to_memory(session)
        print("Added session to Redis memory")
        
        # Search for relevant memories
        response = await service.search_memory(
            app_name="entertainment_app",
            user_id="user_54321",
            query="joke"
        )
        print(f"Found {len(response.memories)} relevant memories")
        if response.memories:
            print(f"First memory content: {response.memories[0].content.parts[0].text}")
        
        # Try a different search query
        response = await service.search_memory(
            app_name="entertainment_app",
            user_id="user_54321",
            query="funny"
        )
        print(f"Found {len(response.memories)} memories for 'funny'")
        if response.memories:
            print(f"First funny memory: {response.memories[0].content.parts[0].text}")
        
        # Clean up
        await service.cleanup()
        print("Cleaned up Redis memory service")
        
    except Exception as e:
        print(f"Redis example skipped (requires running Redis): {e}")
    
    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())