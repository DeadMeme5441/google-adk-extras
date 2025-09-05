"""
Redis Session Service Example
=============================

This example demonstrates how to use the RedisSessionService with Google ADK.

Note: This requires a running Redis instance.
"""

import asyncio
from google.genai import types
from google.adk.sessions.session import Session
from google.adk.events.event import Event

# Import our custom session service
from google_adk_extras.sessions import RedisSessionService


async def main():
    """Demonstrate Redis session service functionality."""
    
    print("=== Redis Session Service Example ===")
    
    try:
        # Initialize the Redis session service
        service = RedisSessionService(host="localhost", port=6379, db=0)
        await service.initialize()
        print("Initialized Redis session service")
        
        # Create a session
        session = await service.create_session(
            app_name="example_app",
            user_id="user_123",
            state={"theme": "auto", "language": "fr"}
        )
        print(f"Created session: {session.id}")
        
        # Add an event to the session
        content = types.Content(parts=[types.Part.from_text(text="Hello from Redis!")])
        event = Event(
            id="event_1",
            author="user",
            content=content,
            timestamp=1234567890.0
        )
        await service.append_event(session, event)
        print("Added event to session")
        
        # Retrieve the session
        retrieved_session = await service.get_session(
            app_name="example_app",
            user_id="user_123",
            session_id=session.id
        )
        print(f"Retrieved session with {len(retrieved_session.events)} events")
        print(f"Session state: {retrieved_session.state}")
        print(f"First event content: {retrieved_session.events[0].content.parts[0].text}")
        
        # Clean up
        await service.cleanup()
        print("Cleaned up Redis session service")
        
    except Exception as e:
        print(f"Redis example skipped (requires running Redis): {e}")
    
    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())