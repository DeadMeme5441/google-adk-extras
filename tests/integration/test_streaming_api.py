import json
import asyncio
import pytest

from fastapi.testclient import TestClient
from google.genai import types
from google.adk.events.event import Event
from google.adk.cli.adk_web_server import RunAgentRequest

from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app
from google_adk_extras.custom_agent_loader import CustomAgentLoader


class _FakeRunner:
    async def run_async(self, *, user_id, session_id, new_message, state_delta=None, run_config=None):
        yield Event(author="agent", content=types.Content(parts=[types.Part(text="hello-1")]))
        yield Event(author="agent", content=types.Content(parts=[types.Part(text="hello-2")]))


def _build_app():
    # Use programmatic loader with no actual agents; we stub runner anyway
    loader = CustomAgentLoader()
    app = get_enhanced_fast_api_app(agent_loader=loader, web=False, enable_streaming=True)
    # Patch runner factory
    app.state.streaming_controller._get_runner_async = lambda app_name: asyncio.sleep(0, result=_FakeRunner())
    return app


def test_streaming_routes_mounted():
    app = _build_app()
    client = TestClient(app)
    # REST routes should appear in OpenAPI
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    paths = data.get("paths", {})
    assert "/stream/events/{channel_id}" in paths
    assert "/stream/send/{channel_id}" in paths

    # WebSocket routes do not appear in OpenAPI; verify mounted in router
    ws_paths = [getattr(r, "path", None) for r in app.router.routes if getattr(r, "name", "").startswith("ws_endpoint") or getattr(r, "path", "").startswith("/stream/ws/")]
    assert any(p and p.startswith("/stream/ws/") for p in ws_paths)


@pytest.mark.skip(reason="SSE streaming reading with TestClient can block; covered by unit tests")
def test_sse_streaming_and_send():
    pass
