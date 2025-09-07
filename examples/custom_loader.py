"""Programmatic agent registration with CustomAgentLoader.

This shows using in-memory agent instances instead of on-disk agent folders.
"""

from google_adk_extras import AdkBuilder, CustomAgentLoader
from google.adk.agents.base_agent import BaseAgent


class EchoAgent(BaseAgent):
    name = "echo"

    async def _run_async_impl(self, invocation_context):
        user_text = invocation_context.user_content.text if invocation_context.user_content else ""
        yield self.create_text_response(f"Echo: {user_text}")


loader = CustomAgentLoader()
loader.register_agent("echo_app", EchoAgent())

app = (
    AdkBuilder()
    .with_agent_loader(loader)
    .with_session_service("sqlite:///./sessions.db")
    .with_artifact_service("local://./artifacts")
    .with_memory_service("yaml://./memory")
    .build_fastapi_app()
)

