"""
SQL Memory Service Example
==========================

This example demonstrates how to use the SQLMemoryService with Google ADK.
"""

import asyncio
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from google.genai import types
from google.adk.sessions.session import Session
from google.adk.events.event import Event

# Import our custom memory service
from google_adk_extras.memory import SQLMemoryService


async def main():
    """Demonstrate SQL memory service functionality."""
    
    print("=== SQL Memory Service Example ===")
    
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        tmp_file.close()
        try:
            # Initialize the SQL memory service
            service = SQLMemoryService(f"sqlite:///{tmp_file.name}")
            await service.initialize()
            print(f"Initialized SQL memory service with database: {tmp_file.name}")
            
            # Create a sample session with events
            conversation_events = [
                Event(
                    id="event1",
                    author="user",
                    timestamp=datetime.now().timestamp(),
                    content=types.Content(parts=[types.Part.from_text(text="I'm having trouble with my account login")])
                ),
                Event(
                    id="event2",
                    author="assistant",
                    timestamp=datetime.now().timestamp() + 1,
                    content=types.Content(parts=[types.Part.from_text(text="I'd be happy to help you with your login issue. Can you tell me what error message you're seeing?")])
                ),
                Event(
                    id="event3",
                    author="user",
                    timestamp=datetime.now().timestamp() + 2,
                    content=types.Content(parts=[types.Part.from_text(text="It says 'Invalid credentials' but I'm sure my password is correct")])
                ),
            ]
            
            session = Session(
                id="support_session_001",
                app_name="customer_support",
                user_id="customer_12345",
                events=conversation_events
            )
            
            # Add session to memory
            await service.add_session_to_memory(session)
            print("Added session to SQL memory")
            
            # Search for relevant memories
            response = await service.search_memory(
                app_name="customer_support",
                user_id="customer_12345",
                query="account login"
            )
            print(f"Found {len(response.memories)} relevant memories")
            if response.memories:
                print(f"First memory content: {response.memories[0].content.parts[0].text}")
            
            # Try a different search query
            response = await service.search_memory(
                app_name="customer_support",
                user_id="customer_12345",
                query="password"
            )
            print(f"Found {len(response.memories)} memories for 'password'")
            if response.memories:
                print(f"First password-related memory: {response.memories[0].content.parts[0].text}")
            
            # Clean up
            await service.cleanup()
            print("Cleaned up SQL memory service")
            
        finally:
            # Remove the temporary database file
            os.unlink(tmp_file.name)
    
    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())