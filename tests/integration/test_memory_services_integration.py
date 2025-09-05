"""Integration tests for memory services."""

import pytest
import tempfile
import os
from datetime import datetime

from google.genai import types
from google_adk_extras.memory import (
    SQLMemoryService,
    YamlFileMemoryService,
)
from google.adk.sessions.session import Session
from google.adk.events.event import Event


class TestMemoryServiceIntegration:
    """Integration tests for memory services."""

    @pytest.mark.asyncio
    async def test_sql_memory_service_end_to_end(self):
        """Test SQL memory service end-to-end functionality."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            tmp_file.close()
            try:
                service = SQLMemoryService(f"sqlite:///{tmp_file.name}")
                await service.initialize()
                
                # Create a conversation session
                user_content = types.Content(parts=[types.Part.from_text(text="Tell me a joke")])
                assistant_content = types.Content(parts=[types.Part.from_text(text="Why don't scientists trust atoms? Because they make up everything!")])
                
                user_event = Event(
                    id="user_event",
                    author="user",
                    timestamp=datetime.now().timestamp(),
                    content=user_content
                )
                
                assistant_event = Event(
                    id="assistant_event",
                    author="assistant",
                    timestamp=datetime.now().timestamp() + 1,
                    content=assistant_content
                )
                
                session = Session(
                    id="joke_session",
                    app_name="chat_app",
                    user_id="user123",
                    events=[user_event, assistant_event]
                )
                
                # Add session to memory
                await service.add_session_to_memory(session)
                
                # Search for memories containing "joke"
                response = await service.search_memory(
                    app_name="chat_app",
                    user_id="user123",
                    query="joke"
                )
                
                assert len(response.memories) == 1
                memory = response.memories[0]
                assert memory.content.parts[0].text == "Tell me a joke"
                assert memory.author == "user"
                
                # Search for memories containing "scientists"
                response = await service.search_memory(
                    app_name="chat_app",
                    user_id="user123",
                    query="scientists"
                )
                
                assert len(response.memories) == 1
                memory = response.memories[0]
                assert "scientists" in memory.content.parts[0].text
                assert memory.author == "assistant"
                
                await service.cleanup()
            finally:
                os.unlink(tmp_file.name)

    @pytest.mark.asyncio
    async def test_yaml_file_memory_service_end_to_end(self):
        """Test YAML file memory service end-to-end functionality."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = YamlFileMemoryService(tmp_dir)
            await service.initialize()
            
            # Create a conversation session
            user_content = types.Content(parts=[types.Part.from_text(text="What's the weather like today?")])
            assistant_content = types.Content(parts=[types.Part.from_text(text="It's sunny and warm!")])
            
            user_event = Event(
                id="user_event",
                author="user",
                timestamp=datetime.now().timestamp(),
                content=user_content
            )
            
            assistant_event = Event(
                id="assistant_event",
                author="assistant",
                timestamp=datetime.now().timestamp() + 1,
                content=assistant_content
            )
            
            session = Session(
                id="weather_session",
                app_name="assistant_app",
                user_id="user456",
                events=[user_event, assistant_event]
            )
            
            # Add session to memory
            await service.add_session_to_memory(session)
            
            # Search for memories containing "weather"
            response = await service.search_memory(
                app_name="assistant_app",
                user_id="user456",
                query="weather"
            )
            
            assert len(response.memories) == 1
            memory = response.memories[0]
            assert "weather" in memory.content.parts[0].text
            assert memory.author == "user"
            
            # Search for memories containing "sunny"
            response = await service.search_memory(
                app_name="assistant_app",
                user_id="user456",
                query="sunny"
            )
            
            assert len(response.memories) == 1
            memory = response.memories[0]
            assert "sunny" in memory.content.parts[0].text
            assert memory.author == "assistant"
            
            await service.cleanup()


if __name__ == "__main__":
    pytest.main([__file__])