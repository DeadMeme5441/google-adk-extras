"""Spin up an ADK FastAPI server on 127.0.0.1:8015 with in-memory services.

This script uses google_adk_extras.get_enhanced_fast_api_app with a simple
programmatic agent loader. It is intended only to inspect the OpenAPI schema
and enumerate endpoints exposed by the ADK web server.
"""

from typing import AsyncGenerator, Optional

from fastapi import FastAPI

from google.genai import types
from google.adk.events.event import Event
from google.adk.agents.base_agent import BaseAgent

from google_adk_extras.custom_agent_loader import CustomAgentLoader
from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app


class _DummyAgent(BaseAgent):
    """Minimal agent; not used for OpenAPI generation, but loadable if needed."""

    def __init__(self, name: str = "dummy"):
        super().__init__(name)

    async def run_async(self, ctx) -> AsyncGenerator[Event, None]:
        # Emit a trivial final event; unlikely to be executed in this script.
        content = types.Content(parts=[types.Part(text="ok")])
        yield Event(author=self.name, content=content)


def build_app() -> FastAPI:
    loader = CustomAgentLoader()
    app = get_enhanced_fast_api_app(
        agent_loader=loader,
        web=False,                 # no static UI
        enable_streaming=False,    # focus on ADK core endpoints
        allow_origins=["*"]
    )
    return app


app = build_app()
