#!/usr/bin/env python3
"""Example of using custom session services with Google ADK."""

import asyncio
import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from google.adk.runners import InMemoryRunner
from google.adk.sessions.session import Session
from google.adk.events.event import Event

from google_adk_extras.sessions.yaml_file_session_service import YamlFileSessionService


async def example_with_custom_session_service():
    """Example of using a custom session service with Google ADK."""
    print("=== Google ADK with Custom Session Service Example ===\n")
    
    # Create a custom session service
    session_service = YamlFileSessionService("./example_sessions")
    
    try:
        # Initialize the session service
        await session_service.initialize()
        
        # Create a session directly using our custom service
        session = await session_service.create_session(
            app_name="example_app",
            user_id="example_user",
            state={"theme": "dark", "language": "en"}
        )
        print(f"✓ Created session: {session.id}")
        
        # Simulate an event (in a real scenario, this would come from the agent)
        # For now, we'll create a simple event
        event = Event(
            invocation_id="test_invocation",
            author="user",
            content=None  # Simplified for this example
        )
        
        # Append the event to the session
        await session_service.append_event(session, event)
        print("✓ Appended event to session")
        
        # Retrieve the session to see what was stored
        retrieved_session = await session_service.get_session(
            app_name="example_app",
            user_id="example_user",
            session_id=session.id
        )
        
        if retrieved_session:
            print(f"\nSession details:")
            print(f"  ID: {retrieved_session.id}")
            print(f"  App Name: {retrieved_session.app_name}")
            print(f"  User ID: {retrieved_session.user_id}")
            print(f"  Number of events: {len(retrieved_session.events)}")
            print(f"  Last update time: {retrieved_session.last_update_time}")
            print(f"  State: {retrieved_session.state}")
        
        # List all sessions for this user
        sessions_response = await session_service.list_sessions(
            app_name="example_app",
            user_id="example_user"
        )
        
        print(f"\nFound {len(sessions_response.sessions)} sessions for this user")
        for s in sessions_response.sessions:
            print(f"  - Session ID: {s.id}")
        
        # Delete session
        await session_service.delete_session(
            app_name="example_app",
            user_id="example_user",
            session_id=session.id
        )
        print("✓ Deleted session")
        
    finally:
        # Clean up the session service
        await session_service.cleanup()
        
    print("\nExample completed successfully! ✓")


if __name__ == "__main__":
    asyncio.run(example_with_custom_session_service())