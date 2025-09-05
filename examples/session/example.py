"""
Session Services Example
========================

This example demonstrates how to use all custom session services with Google ADK.

The example shows:
1. Creating sessions with different storage backends
2. Adding events to sessions
3. Retrieving and listing sessions
4. Using sessions with Google ADK runners
"""

import asyncio
import tempfile
import os
from pathlib import Path

from google.genai import types
from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.adk.agents.simple_agent import SimpleAgent
from google.adk.runners.simple_runner import SimpleRunner

# Import our custom session services
from google_adk_extras.sessions import (
    SQLSessionService,
    MongoSessionService,
    RedisSessionService,
    YamlFileSessionService
)


async def demonstrate_session_services():
    """Demonstrate all custom session services."""
    
    # 1. SQL Session Service Example
    print("=== SQL Session Service Example ===")
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        tmp_file.close()
        try:
            sql_service = SQLSessionService(f"sqlite:///{tmp_file.name}")
            await sql_service.initialize()
            
            # Create a session
            session = await sql_service.create_session(
                app_name="example_app",
                user_id="user_123",
                state={"preferences": "dark_mode"}
            )
            print(f"Created SQL session: {session.id}")
            
            # Add an event
            content = types.Content(parts=[types.Part.from_text(text="Hello, world!")])
            event = Event(
                id="event_1",
                author="user",
                content=content,
                timestamp=1234567890.0
            )
            await sql_service.append_event(session, event)
            print("Added event to SQL session")
            
            # Retrieve the session
            retrieved_session = await sql_service.get_session(
                app_name="example_app",
                user_id="user_123",
                session_id=session.id
            )
            print(f"Retrieved SQL session with {len(retrieved_session.events)} events")
            
            await sql_service.cleanup()
        finally:
            os.unlink(tmp_file.name)
    
    # 2. MongoDB Session Service Example
    print("\n=== MongoDB Session Service Example ===")
    # Note: This requires a running MongoDB instance
    try:
        mongo_service = MongoSessionService("mongodb://localhost:27017", "adk_sessions_example")
        await mongo_service.initialize()
        
        # Create a session
        session = await mongo_service.create_session(
            app_name="example_app",
            user_id="user_123",
            state={"preferences": "light_mode"}
        )
        print(f"Created MongoDB session: {session.id}")
        
        # Add an event
        content = types.Content(parts=[types.Part.from_text(text="Hello from MongoDB!")])
        event = Event(
            id="event_2",
            author="user",
            content=content,
            timestamp=1234567891.0
        )
        await mongo_service.append_event(session, event)
        print("Added event to MongoDB session")
        
        # List sessions
        sessions_response = await mongo_service.list_sessions(
            app_name="example_app",
            user_id="user_123"
        )
        print(f"Found {len(sessions_response.sessions)} MongoDB sessions")
        
        await mongo_service.cleanup()
    except Exception as e:
        print(f"MongoDB example skipped (requires running MongoDB): {e}")
    
    # 3. Redis Session Service Example
    print("\n=== Redis Session Service Example ===")
    # Note: This requires a running Redis instance
    try:
        redis_service = RedisSessionService(host="localhost", port=6379, db=0)
        await redis_service.initialize()
        
        # Create a session
        session = await redis_service.create_session(
            app_name="example_app",
            user_id="user_123",
            state={"preferences": "auto_mode"}
        )
        print(f"Created Redis session: {session.id}")
        
        # Add an event
        content = types.Content(parts=[types.Part.from_text(text="Hello from Redis!")])
        event = Event(
            id="event_3",
            author="user",
            content=content,
            timestamp=1234567892.0
        )
        await redis_service.append_event(session, event)
        print("Added event to Redis session")
        
        await redis_service.cleanup()
    except Exception as e:
        print(f"Redis example skipped (requires running Redis): {e}")
    
    # 4. YAML File Session Service Example
    print("\n=== YAML File Session Service Example ===")
    with tempfile.TemporaryDirectory() as tmp_dir:
        yaml_service = YamlFileSessionService(tmp_dir)
        await yaml_service.initialize()
        
        # Create a session
        session = await yaml_service.create_session(
            app_name="example_app",
            user_id="user_123",
            state={"preferences": "system_mode"}
        )
        print(f"Created YAML session: {session.id}")
        
        # Add an event
        content = types.Content(parts=[types.Part.from_text(text="Hello from YAML files!")])
        event = Event(
            id="event_4",
            author="user",
            content=content,
            timestamp=1234567893.0
        )
        await yaml_service.append_event(session, event)
        print("Added event to YAML session")
        
        # List sessions
        sessions_response = await yaml_service.list_sessions(
            app_name="example_app",
            user_id="user_123"
        )
        print(f"Found {len(sessions_response.sessions)} YAML sessions")
        
        await yaml_service.cleanup()
    
    print("\n=== Session Services Example Complete ===")


async def demonstrate_session_with_runner():
    """Demonstrate using a session service with a Google ADK runner."""
    print("\n=== Session Service with Runner Example ===")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        tmp_file.close()
        try:
            # Create SQL session service
            session_service = SQLSessionService(f"sqlite:///{tmp_file.name}")
            await session_service.initialize()
            
            # Create a simple agent
            agent = SimpleAgent(name="example_agent")
            
            # Create runner with our custom session service
            runner = SimpleRunner(
                agent=agent,
                session_service=session_service
            )
            
            # Run a conversation
            response = await runner.run(
                app_name="runner_example",
                user_id="user_456",
                input_content=types.Content(parts=[types.Part.from_text(text="Hello, how are you?")])
            )
            print(f"Agent response: {response.content.parts[0].text}")
            
            # Check the session that was created
            sessions_response = await session_service.list_sessions(
                app_name="runner_example",
                user_id="user_456"
            )
            print(f"Created {len(sessions_response.sessions)} session(s) via runner")
            
            await session_service.cleanup()
        finally:
            os.unlink(tmp_file.name)
    
    print("=== Runner Example Complete ===")


async def main():
    """Run all session service examples."""
    await demonstrate_session_services()
    await demonstrate_session_with_runner()


if __name__ == "__main__":
    asyncio.run(main())