"""
MongoDB Session Service Example
===============================

This example demonstrates how to use the MongoSessionService with Google ADK.

Note: This requires a running MongoDB instance.
"""

import asyncio
from google.genai import types
from google.adk.sessions.session import Session
from google.adk.events.event import Event

# Import our custom session service
from google_adk_extras.sessions import MongoSessionService


async def main():
    """Demonstrate MongoDB session service functionality."""
    
    print("=== MongoDB Session Service Example ===")
    
    try:
        # Initialize the MongoDB session service
        service = MongoSessionService("mongodb://localhost:27017", "adk_sessions_example")
        await service.initialize()
        print("Initialized MongoDB session service")
        
        # Create a session
        session = await service.create_session(
            app_name="example_app",
            user_id="user_123",
            state={"theme": "light", "language": "es"}
        )
        print(f"Created session: {session.id}")
        
        # Add an event to the session
        content = types.Content(parts=[types.Part.from_text(text="Hello from MongoDB!")])
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
        
        # List sessions
        sessions_response = await service.list_sessions(
            app_name="example_app",
            user_id="user_123"
        )
        print(f"Found {len(sessions_response.sessions)} sessions for user")
        
        # Clean up
        await service.cleanup()
        print("Cleaned up MongoDB session service")
        
    except Exception as e:
        print(f"MongoDB example skipped (requires running MongoDB): {e}")
    
    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())