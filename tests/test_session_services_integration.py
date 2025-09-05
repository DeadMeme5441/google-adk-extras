#!/usr/bin/env python3
"""Comprehensive test for all session service implementations."""

import asyncio
import sys
import os
import tempfile
import shutil

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from google_adk_extras.sessions import (
    SQLSessionService,
    MongoSessionService,
    RedisSessionService,
    YamlFileSessionService
)


async def test_yaml_session_service():
    """Test the YAML file session service."""
    print("Testing YAML File Session Service...")
    
    # Create a temporary directory for test sessions
    temp_dir = tempfile.mkdtemp(prefix="adk_test_")
    
    try:
        # Initialize service
        service = YamlFileSessionService(temp_dir)
        await service.initialize()
        
        # Run tests
        await _run_session_service_tests(service, "yaml")
        
        # Cleanup
        await service.cleanup()
        shutil.rmtree(temp_dir)
        print("✓ YAML File Session Service tests passed")
        
    except Exception as e:
        # Cleanup on error
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        raise e


async def test_sql_session_service():
    """Test the SQL session service."""
    print("Testing SQL Session Service...")
    
    # Use SQLite in-memory database for testing
    service = SQLSessionService("sqlite:///:memory:")
    
    try:
        # Initialize service
        await service.initialize()
        
        # Run tests
        await _run_session_service_tests(service, "sql")
        
        # Cleanup
        await service.cleanup()
        print("✓ SQL Session Service tests passed")
        
    except Exception as e:
        # Cleanup on error
        try:
            await service.cleanup()
        except:
            pass
        raise e


async def _run_session_service_tests(service, service_type):
    """Run common tests for a session service."""
    # Create a session
    session = await service.create_session(
        app_name=f"test_app_{service_type}",
        user_id=f"test_user_{service_type}",
        state={"theme": "dark", "language": "en"}
    )
    
    # Verify session was created
    assert session.id is not None
    assert session.app_name == f"test_app_{service_type}"
    assert session.user_id == f"test_user_{service_type}"
    assert session.state == {"theme": "dark", "language": "en"}
    assert len(session.events) == 0
    
    # Retrieve the session
    retrieved_session = await service.get_session(
        app_name=f"test_app_{service_type}",
        user_id=f"test_user_{service_type}",
        session_id=session.id
    )
    
    # Verify retrieved session
    assert retrieved_session is not None
    assert retrieved_session.id == session.id
    assert retrieved_session.state == session.state
    assert len(retrieved_session.events) == 0
    
    # List sessions
    sessions_response = await service.list_sessions(
        app_name=f"test_app_{service_type}",
        user_id=f"test_user_{service_type}"
    )
    
    # Verify session listing
    assert len(sessions_response.sessions) == 1
    assert sessions_response.sessions[0].id == session.id
    # Note: Events should be empty in list response
    assert len(sessions_response.sessions[0].events) == 0
    
    # Delete session
    await service.delete_session(
        app_name=f"test_app_{service_type}",
        user_id=f"test_user_{service_type}",
        session_id=session.id
    )
    
    # Verify session was deleted
    deleted_session = await service.get_session(
        app_name=f"test_app_{service_type}",
        user_id=f"test_user_{service_type}",
        session_id=session.id
    )
    assert deleted_session is None


async def main():
    """Run all tests."""
    print("Running comprehensive session service tests...\\n")
    
    # Test YAML service
    await test_yaml_session_service()
    
    # Test SQL service
    await test_sql_session_service()
    
    print("\\nAll tests passed! ✓")


if __name__ == "__main__":
    asyncio.run(main())