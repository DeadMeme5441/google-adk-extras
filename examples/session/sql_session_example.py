"""
SQL Session Service Example
===========================

This example demonstrates how to use the SQLSessionService with Google ADK.
"""

import asyncio
import tempfile
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from google.genai import types
from google.adk.sessions.session import Session
from google.adk.events.event import Event

# Import our custom session service
from google_adk_extras.sessions import SQLSessionService


async def main():
    """Demonstrate SQL session service functionality."""
    
    print("=== SQL Session Service Example ===")
    
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        tmp_file.close()
        try:
            # Initialize the SQL session service
            service = SQLSessionService(f"sqlite:///{tmp_file.name}")
            await service.initialize()
            print(f"Initialized SQL session service with database: {tmp_file.name}")
            
            # Create a session
            session = await service.create_session(
                app_name="example_app",
                user_id="user_123",
                state={"theme": "dark", "language": "en"}
            )
            print(f"Created session: {session.id}")
            
            # Add an event to the session
            content = types.Content(parts=[types.Part.from_text(text="Hello, world!")])
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
            print("Cleaned up SQL session service")
            
        finally:
            # Remove the temporary database file
            os.unlink(tmp_file.name)
    
    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())