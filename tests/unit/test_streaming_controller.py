import asyncio
import json
import pytest

from google.genai import types
from google.adk.events.event import Event
from google.adk.cli.adk_web_server import RunAgentRequest

from google_adk_extras.streaming import StreamingController, StreamingConfig


class _FakeRunner:
    async def run_async(self, *, user_id, session_id, new_message, state_delta=None, run_config=None):  # noqa: D401
        yield Event(author="agent", content=types.Content(parts=[types.Part(text="hi1")]))
        yield Event(author="agent", content=types.Content(parts=[types.Part(text="hi2")]))


@pytest.mark.asyncio
async def test_channel_bind_enqueue_and_broadcast():
    # Minimal session service stub compatible across ADK versions
    class _Session:
        def __init__(self, id: str, app_name: str, user_id: str):
            self.id = id
            self.app_name = app_name
            self.user_id = user_id
            self.events = []

    class _SessionServiceStub:
        def __init__(self):
            self._store = {}
        async def create_session(self, *, app_name: str, user_id: str, state=None, session_id=None):
            sid = session_id or "s-1"
            sess = _Session(sid, app_name, user_id)
            self._store[(app_name, user_id, sid)] = sess
            return sess
        async def get_session(self, *, app_name: str, user_id: str, session_id: str):
            return self._store.get((app_name, user_id, session_id))

    session_service = _SessionServiceStub()
    cfg = StreamingConfig(enable_streaming=True, ttl_seconds=60)
    controller = StreamingController(
        config=cfg,
        get_runner_async=lambda app_name: asyncio.sleep(0, result=_FakeRunner()),
        session_service=session_service,
    )
    controller.start()

    ch = await controller.open_or_bind_channel(channel_id="c1", app_name="app", user_id="u", session_id=None)
    q = controller.subscribe("c1", kind="sse")

    # Build request using channel session id
    req = RunAgentRequest(
        app_name="app",
        user_id="u",
        session_id=ch.session_id,
        new_message=types.Content(parts=[types.Part(text="hello")]),
        streaming=True,
    )
    await controller.enqueue("c1", req)

    # Expect at least one model event
    payload1 = await asyncio.wait_for(q.get(), timeout=5.0)
    j1 = json.loads(payload1)
    assert "author" in j1
