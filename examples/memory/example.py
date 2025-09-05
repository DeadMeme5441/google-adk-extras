"""
Memory Services Example
========================

This example demonstrates how to use all custom memory services with Google ADK.

The example shows:
1. Adding sessions to memory with different storage backends
2. Searching memory for relevant content
3. Using memory with Google ADK runners
"""

import asyncio
import tempfile
import os
from pathlib import Path
from datetime import datetime

from google.genai import types
from google.adk.sessions.session import Session
from google.adk.events.event import Event

# Import our custom memory services
from google_adk_extras.memory import (
    SQLMemoryService,
    MongoMemoryService,
    RedisMemoryService,
    YamlFileMemoryService
)


async def demonstrate_memory_services():
    """Demonstrate all custom memory services."""
    
    # Create sample sessions with events for memory storage
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
        Event(
            id="event4",
            author="assistant",
            timestamp=datetime.now().timestamp() + 3,
            content=types.Content(parts=[types.Part.from_text(text="Let me check your account. It looks like your account might be locked due to multiple failed attempts. I'll unlock it for you now.")])
        ),
    ]
    
    session = Session(
        id="support_session_001",
        app_name="customer_support",
        user_id="customer_12345",
        events=conversation_events
    )
    
    # 1. SQL Memory Service Example
    print("=== SQL Memory Service Example ===")
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        tmp_file.close()
        try:
            sql_service = SQLMemoryService(f"sqlite:///{tmp_file.name}")
            await sql_service.initialize()
            
            # Add session to memory
            await sql_service.add_session_to_memory(session)
            print("Added session to SQL memory")
            
            # Search for relevant memories
            response = await sql_service.search_memory(
                app_name="customer_support",
                user_id="customer_12345",
                query="account login"
            )
            print(f"Found {len(response.memories)} relevant memories in SQL memory")
            if response.memories:
                print(f"First memory content: {response.memories[0].content.parts[0].text}")
            
            await sql_service.cleanup()
        finally:
            os.unlink(tmp_file.name)
    
    # 2. MongoDB Memory Service Example
    print("\n=== MongoDB Memory Service Example ===")
    # Note: This requires a running MongoDB instance
    try:
        mongo_service = MongoMemoryService("mongodb://localhost:27017", "adk_memory_example")
        await mongo_service.initialize()
        
        # Add session to memory
        await mongo_service.add_session_to_memory(session)
        print("Added session to MongoDB memory")
        
        # Search for relevant memories
        response = await mongo_service.search_memory(
            app_name="customer_support",
            user_id="customer_12345",
            query="account login"
        )
        print(f"Found {len(response.memories)} relevant memories in MongoDB memory")
        
        await mongo_service.cleanup()
    except Exception as e:
        print(f"MongoDB example skipped (requires running MongoDB): {e}")
    
    # 3. Redis Memory Service Example
    print("\n=== Redis Memory Service Example ===")
    # Note: This requires a running Redis instance
    try:
        redis_service = RedisMemoryService(host="localhost", port=6379, db=0)
        await redis_service.initialize()
        
        # Add session to memory
        await redis_service.add_session_to_memory(session)
        print("Added session to Redis memory")
        
        # Search for relevant memories
        response = await redis_service.search_memory(
            app_name="customer_support",
            user_id="customer_12345",
            query="account login"
        )
        print(f"Found {len(response.memories)} relevant memories in Redis memory")
        
        await redis_service.cleanup()
    except Exception as e:
        print(f"Redis example skipped (requires running Redis): {e}")
    
    # 4. YAML File Memory Service Example
    print("\n=== YAML File Memory Service Example ===")
    with tempfile.TemporaryDirectory() as tmp_dir:
        yaml_service = YamlFileMemoryService(tmp_dir)
        await yaml_service.initialize()
        
        # Add session to memory
        await yaml_service.add_session_to_memory(session)
        print("Added session to YAML file memory")
        
        # Search for relevant memories
        response = await yaml_service.search_memory(
            app_name="customer_support",
            user_id="customer_12345",
            query="account login"
        )
        print(f"Found {len(response.memories)} relevant memories in YAML file memory")
        
        await yaml_service.cleanup()
    
    print("\n=== Memory Services Example Complete ===")


async def demonstrate_memory_search_patterns():
    """Demonstrate different memory search patterns."""
    print("\n=== Memory Search Patterns Example ===")
    
    # Create a more complex conversation for search testing
    complex_events = [
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
        Event(
            id="event4",
            author="assistant",
            timestamp=datetime.now().timestamp() + 3,
            content=types.Content(parts=[types.Part.from_text(text="Central Park is beautiful this time of year. I recommend visiting the Bethesda Fountain and the Central Park Zoo.")])
        ),
    ]
    
    session = Session(
        id="weather_session_001",
        app_name="travel_assistant",
        user_id="traveler_67890",
        events=complex_events
    )
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        tmp_file.close()
        try:
            sql_service = SQLMemoryService(f"sqlite:///{tmp_file.name}")
            await sql_service.initialize()
            
            # Add session to memory
            await sql_service.add_session_to_memory(session)
            
            # Try different search queries
            search_queries = [
                "weather New York",
                "Central Park",
                "recommendations",
                "temperature"
            ]
            
            for query in search_queries:
                response = await sql_service.search_memory(
                    app_name="travel_assistant",
                    user_id="traveler_67890",
                    query=query
                )
                print(f"Query '{query}' found {len(response.memories)} memories")
            
            await sql_service.cleanup()
        finally:
            os.unlink(tmp_file.name)
    
    print("=== Search Patterns Example Complete ===")


async def main():
    """Run all memory service examples."""
    await demonstrate_memory_services()
    await demonstrate_memory_search_patterns()


if __name__ == "__main__":
    asyncio.run(main())