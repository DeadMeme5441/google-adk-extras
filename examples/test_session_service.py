#!/usr/bin/env python3
"""Simple test to verify session service implementation."""

import asyncio
import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from google_adk_extras.sessions.yaml_file_session_service import YamlFileSessionService


async def test_yaml_session_service():
    """Test the YAML file session service."""
    print("Testing YAML File Session Service...")
    
    # Initialize service
    service = YamlFileSessionService("./test_sessions")
    
    try:
        # Initialize the service
        await service.initialize()
        print("✓ Service initialized")
        
        # Create a session
        session = await service.create_session(
            app_name="test_app",
            user_id="test_user",
            state={"theme": "dark", "language": "en"}
        )
        print(f"✓ Created session: {session.id}")
        
        # Retrieve the session
        retrieved_session = await service.get_session(
            app_name="test_app",
            user_id="test_user",
            session_id=session.id
        )
        print(f"✓ Retrieved session: {retrieved_session.id}")
        print(f"✓ Session state: {retrieved_session.state}")
        
        # List sessions
        sessions_response = await service.list_sessions(
            app_name="test_app",
            user_id="test_user"
        )
        print(f"✓ Found {len(sessions_response.sessions)} sessions")
        
        # Delete session
        await service.delete_session(
            app_name="test_app",
            user_id="test_user",
            session_id=session.id
        )
        print("✓ Deleted session")
        
        # Cleanup
        await service.cleanup()
        print("✓ Service cleaned up")
        
        print("\nAll tests passed! ✓")
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        # Cleanup on error
        try:
            await service.cleanup()
        except:
            pass
        raise


if __name__ == "__main__":
    asyncio.run(test_yaml_session_service())
