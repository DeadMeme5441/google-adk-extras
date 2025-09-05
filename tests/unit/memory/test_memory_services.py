"""Unit tests for custom memory services."""

import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock
import json
from datetime import datetime

from google.genai import types
from google_adk_extras.memory import (
    SQLMemoryService,
    MongoMemoryService,
    RedisMemoryService,
    YamlFileMemoryService,
)
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.sessions.session import Session
from google.adk.events.event import Event

# Import redis for mocking
try:
    import redis
except ImportError:
    redis = Mock()


class TestSQLMemoryService:
    """Tests for SQLMemoryService."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test SQL memory service initialization."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            tmp_file.close()
            try:
                service = SQLMemoryService(f"sqlite:///{tmp_file.name}")
                await service.initialize()
                assert service._initialized is True
                await service.cleanup()
            finally:
                os.unlink(tmp_file.name)

    @pytest.mark.asyncio
    async def test_add_session_and_search(self):
        """Test adding a session and searching memory."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            tmp_file.close()
            try:
                service = SQLMemoryService(f"sqlite:///{tmp_file.name}")
                await service.initialize()
                
                # Create a mock session with events
                content1 = types.Content(parts=[types.Part.from_text(text="Hello world")])
                content2 = types.Content(parts=[types.Part.from_text(text="How are you?")])
                
                event1 = Event(
                    id="event1",
                    author="user",
                    timestamp=1234567890.0,
                    content=content1
                )
                
                event2 = Event(
                    id="event2",
                    author="assistant",
                    timestamp=1234567891.0,
                    content=content2
                )
                
                session = Session(
                    id="test_session",
                    app_name="test_app",
                    user_id="test_user",
                    events=[event1, event2]
                )
                
                # Add session to memory
                await service.add_session_to_memory(session)
                
                # Search for memories
                response = await service.search_memory(
                    app_name="test_app",
                    user_id="test_user",
                    query="hello"
                )
                
                assert len(response.memories) == 1
                assert response.memories[0].content.parts[0].text == "Hello world"
                
                await service.cleanup()
            finally:
                os.unlink(tmp_file.name)


class TestMongoMemoryService:
    """Tests for MongoMemoryService."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test MongoDB memory service initialization."""
        # Patch the MongoClient to avoid actual connection
        from unittest.mock import patch
        with patch('google_adk_extras.memory.mongo_memory_service.MongoClient') as mock_mongo_client:
            # Mock the MongoDB client and database
            mock_client = Mock()
            mock_db = Mock()
            mock_collection = Mock()
            
            mock_mongo_client.return_value = mock_client
            mock_client.__getitem__ = Mock(return_value=mock_db)
            mock_db.__getitem__ = Mock(return_value=mock_collection)
            
            service = MongoMemoryService("mongodb://localhost:27017", "test_db")
            await service._initialize_impl()
            assert service.client is not None


class TestRedisMemoryService:
    """Tests for RedisMemoryService."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test Redis memory service initialization."""
        # Use a mock Redis client for testing
        service = RedisMemoryService("localhost", 6379, 0)
        
        # Mock the Redis client
        mock_client = Mock()
        mock_client.ping.return_value = True
        service.client = mock_client
        
        # Override the Redis client creation to use our mock
        try:
            original_redis = redis.Redis
            redis.Redis = Mock(return_value=mock_client)
        except AttributeError:
            # If redis is a mock, we can't replace it
            pass
        
        try:
            await service._initialize_impl()
            assert service.client is not None
        finally:
            # Restore the original Redis client if it exists
            try:
                redis.Redis = original_redis
            except AttributeError:
                pass


class TestYamlFileMemoryService:
    """Tests for YamlFileMemoryService."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test YAML file memory service initialization."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = YamlFileMemoryService(tmp_dir)
            await service.initialize()
            assert service._initialized is True
            await service.cleanup()

    @pytest.mark.asyncio
    async def test_add_session_and_search(self):
        """Test adding a session and searching memory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = YamlFileMemoryService(tmp_dir)
            await service.initialize()
            
            # Create a mock session with events
            content1 = types.Content(parts=[types.Part.from_text(text="Hello world")])
            content2 = types.Content(parts=[types.Part.from_text(text="How are you?")])
            
            event1 = Event(
                id="event1",
                author="user",
                timestamp=1234567890.0,
                content=content1
            )
            
            event2 = Event(
                id="event2",
                author="assistant",
                timestamp=1234567891.0,
                content=content2
            )
            
            session = Session(
                id="test_session",
                app_name="test_app",
                user_id="test_user",
                events=[event1, event2]
            )
            
            # Add session to memory
            await service.add_session_to_memory(session)
            
            # Search for memories
            response = await service.search_memory(
                app_name="test_app",
                user_id="test_user",
                query="hello"
            )
            
            assert len(response.memories) == 1
            assert response.memories[0].content.parts[0].text == "Hello world"
            
            await service.cleanup()


if __name__ == "__main__":
    pytest.main([__file__])