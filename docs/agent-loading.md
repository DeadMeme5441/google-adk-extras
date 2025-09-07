# Programmatic Agents

You don’t need on‑disk agent folders. Register agent instances directly.

```python
from google_adk_extras import AdkBuilder, CustomAgentLoader
from google.adk.agents.base_agent import BaseAgent

class EchoAgent(BaseAgent):
    name = "echo"
    async def _run_async_impl(self, ctx):
        text = ctx.user_content.text if ctx.user_content else ""
        yield self.create_text_response(f"Echo: {text}")

loader = CustomAgentLoader()
loader.register_agent("echo_app", EchoAgent())

app = (
  AdkBuilder()
  .with_agent_loader(loader)
  .with_session_service("sqlite:///./sessions.db")
  .build_fastapi_app()
)
```

Guidance
- Use programmatic loading for testing or dynamic agent assembly.
- Do not mix `with_agents_dir()` and registered instances in one builder.
