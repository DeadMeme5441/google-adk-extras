"""End-to-end tests for memory services simulating real-world scenarios."""

import pytest
import tempfile
import os
from datetime import datetime, timedelta

from google.genai import types
try:
    from google_adk_extras.memory import SQLMemoryService
except Exception:
    SQLMemoryService = None
try:
    from google_adk_extras.memory import YamlFileMemoryService
except Exception:
    YamlFileMemoryService = None
from google.adk.sessions.session import Session
from google.adk.events.event import Event


class TestMemoryServiceRealWorldScenarios:
    """End-to-end tests simulating real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_customer_support_conversation_memory(self):
        """Test memory service with a customer support conversation scenario."""
        if SQLMemoryService is None:
            pytest.skip("SQLAlchemy not installed")
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            tmp_file.close()
            try:
                service = SQLMemoryService(f"sqlite:///{tmp_file.name}")
                await service.initialize()
                
                # Simulate a customer support conversation
                conversation_events = [
                    # Customer initial inquiry
                    Event(
                        id="event1",
                        author="customer",
                        timestamp=datetime.now().timestamp(),
                        content=types.Content(parts=[types.Part.from_text(text="I'm having trouble with my account login")])
                    ),
                    # Support agent response
                    Event(
                        id="event2",
                        author="support_agent",
                        timestamp=datetime.now().timestamp() + 1,
                        content=types.Content(parts=[types.Part.from_text(text="I'd be happy to help you with your login issue. Can you tell me what error message you're seeing?")])
                    ),
                    # Customer provides more details
                    Event(
                        id="event3",
                        author="customer",
                        timestamp=datetime.now().timestamp() + 2,
                        content=types.Content(parts=[types.Part.from_text(text="It says 'Invalid credentials' but I'm sure my password is correct")])
                    ),
                    # Support agent investigates
                    Event(
                        id="event4",
                        author="support_agent",
                        timestamp=datetime.now().timestamp() + 3,
                        content=types.Content(parts=[types.Part.from_text(text="Let me check your account. It looks like your account might be locked due to multiple failed attempts. I'll unlock it for you now.")])
                    ),
                    # Issue resolved
                    Event(
                        id="event5",
                        author="support_agent",
                        timestamp=datetime.now().timestamp() + 4,
                        content=types.Content(parts=[types.Part.from_text(text="Your account has been unlocked. Please try logging in again.")])
                    ),
                    # Customer confirmation
                    Event(
                        id="event6",
                        author="customer",
                        timestamp=datetime.now().timestamp() + 5,
                        content=types.Content(parts=[types.Part.from_text(text="Great! I can log in now. Thank you for your help!")])
                    )
                ]
                
                session = Session(
                    id="support_session_001",
                    app_name="customer_support",
                    user_id="customer_12345",
                    events=conversation_events
                )
                
                # Add session to memory
                await service.add_session_to_memory(session)
                
                # Later, when the customer contacts support again, search for relevant history
                response = await service.search_memory(
                    app_name="customer_support",
                    user_id="customer_12345",
                    query="account login"
                )
                
                # Should find relevant memories about login issues
                assert len(response.memories) >= 1
                # Check that we found memories related to login
                login_memories = [m for m in response.memories if "login" in m.content.parts[0].text.lower()]
                assert len(login_memories) >= 1
                
                # Search for support agent interactions
                response = await service.search_memory(
                    app_name="customer_support",
                    user_id="customer_12345",
                    query="help you"
                )
                
                # Should find memories where support agent was involved
                assert len(response.memories) >= 1
                
                await service.cleanup()
            finally:
                os.unlink(tmp_file.name)

    @pytest.mark.asyncio
    async def test_personal_assistant_memory_with_multiple_sessions(self):
        """Test memory service with a personal assistant handling multiple sessions."""
        if YamlFileMemoryService is None:
            pytest.skip("pyyaml not installed")
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = YamlFileMemoryService(tmp_dir)
            await service.initialize()
            
            # Session 1: User asks about meeting schedule
            meeting_events = [
                Event(
                    id="event1",
                    author="user",
                    timestamp=datetime.now().timestamp(),
                    content=types.Content(parts=[types.Part.from_text(text="What meetings do I have scheduled for tomorrow?")])
                ),
                Event(
                    id="event2",
                    author="assistant",
                    timestamp=datetime.now().timestamp() + 1,
                    content=types.Content(parts=[types.Part.from_text(text="You have 3 meetings scheduled for tomorrow: 10am team sync, 2pm project review, and 4pm client call.")])
                )
            ]
            
            meeting_session = Session(
                id="session_meetings",
                app_name="personal_assistant",
                user_id="user_abc",
                events=meeting_events
            )
            
            # Session 2: User asks about project details
            project_events = [
                Event(
                    id="event3",
                    author="user",
                    timestamp=datetime.now().timestamp() + 1000,
                    content=types.Content(parts=[types.Part.from_text(text="Tell me about the Alpha project status")])
                ),
                Event(
                    id="event4",
                    author="assistant",
                    timestamp=datetime.now().timestamp() + 1001,
                    content=types.Content(parts=[types.Part.from_text(text="The Alpha project is 75% complete. The main deliverables are on track for the June 15th deadline.")])
                )
            ]
            
            project_session = Session(
                id="session_project",
                app_name="personal_assistant",
                user_id="user_abc",
                events=project_events
            )
            
            # Add both sessions to memory
            await service.add_session_to_memory(meeting_session)
            await service.add_session_to_memory(project_session)
            
            # Search for meeting-related information
            response = await service.search_memory(
                app_name="personal_assistant",
                user_id="user_abc",
                query="meetings tomorrow"
            )
            
            # Should find memories about meetings
            assert len(response.memories) >= 1
            meeting_memories = [m for m in response.memories if "meeting" in m.content.parts[0].text.lower()]
            assert len(meeting_memories) >= 1
            
            # Search for project-related information
            response = await service.search_memory(
                app_name="personal_assistant",
                user_id="user_abc",
                query="Alpha project"
            )
            
            # Should find memories about the Alpha project
            assert len(response.memories) >= 1
            project_memories = [m for m in response.memories if "alpha" in m.content.parts[0].text.lower()]
            assert len(project_memories) >= 1
            
            await service.cleanup()


if __name__ == "__main__":
    pytest.main([__file__])
