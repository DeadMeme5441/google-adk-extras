"""Examples of using custom session services."""

import asyncio
from google.adk.sessions.session import Session
from google.adk.events.event import Event

# Import custom session services
from google_adk_extras.sessions import (
    SQLSessionService,
    MongoSessionService,
    RedisSessionService,
    YamlFileSessionService
)


async def example_sql_session_service():
    """Example of using SQLSessionService."""
    print("=== SQL Session Service Example ===")
    
    # Initialize service with SQLite database
    service = SQLSessionService("sqlite:///./test_sessions.db")
    
    try:
        # Create a session
        session = await service.create_session(
            app_name="my_app",
            user_id="user123",
            state={"theme": "dark", "language": "en"}
        )
        print(f"Created session: {session.id}")
        
        # Retrieve the session
        retrieved_session = await service.get_session(
            app_name="my_app",
            user_id="user123",
            session_id=session.id
        )
        print(f"Retrieved session: {retrieved_session.id}")
        print(f"Session state: {retrieved_session.state}")
        
        # List sessions
        sessions_response = await service.list_sessions(
            app_name="my_app",
            user_id="user123"
        )
        print(f"Found {len(sessions_response.sessions)} sessions")
        
        # Delete session
        await service.delete_session(
            app_name="my_app",
            user_id="user123",
            session_id=session.id
        )
        print("Deleted session")
        
    finally:
        # Clean up
        await service.cleanup()


async def example_yaml_file_session_service():
    """Example of using YamlFileSessionService."""
    print("\n=== YAML File Session Service Example ===")
    
    # Initialize service with base directory
    service = YamlFileSessionService("./example_sessions")
    
    try:
        # Create a session
        session = await service.create_session(
            app_name="my_app",
            user_id="user123",
            state={"theme": "light", "language": "es"}
        )
        print(f"Created session: {session.id}")
        
        # Retrieve the session
        retrieved_session = await service.get_session(
            app_name="my_app",
            user_id="user123",
            session_id=session.id
        )
        print(f"Retrieved session: {retrieved_session.id}")
        print(f"Session state: {retrieved_session.state}")
        
        # List sessions
        sessions_response = await service.list_sessions(
            app_name="my_app",
            user_id="user123"
        )
        print(f"Found {len(sessions_response.sessions)} sessions")
        
        # Delete session
        await service.delete_session(
            app_name="my_app",
            user_id="user123",
            session_id=session.id
        )
        print("Deleted session")
        
    finally:
        # Clean up
        await service.cleanup()


async def main():
    """Run examples."""
    # Run SQL example
    await example_sql_session_service()
    
    # Run YAML file example
    await example_yaml_file_session_service()
    
    print("\nExamples completed!")


if __name__ == "__main__":
    asyncio.run(main())