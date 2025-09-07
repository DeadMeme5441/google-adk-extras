# Quickstarts

This page mirrors the `examples/` folder with copy‑paste starters.

## FastAPI App

```python
from google_adk_extras import AdkBuilder

app = (
    AdkBuilder()
    .with_agents_dir("./agents")
    .with_session_service("sqlite:///./sessions.db")
    .with_artifact_service("local://./artifacts")
    .with_memory_service("yaml://./memory")
    .with_web_ui(True)
    .with_agent_reload(True)
    .build_fastapi_app()
)
```

Run: `uvicorn app:app --reload`.

## Runner

```python
runner = (
    AdkBuilder()
    .with_agents_dir("./agents")
    .with_session_service("sqlite:///./sessions.db")
    .with_memory_service("yaml://./memory")
    .with_artifact_service("local://./artifacts")
    .build_runner("my_agent")
)
```

## Programmatic Agents

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
    .with_artifact_service("local://./artifacts")
    .with_memory_service("yaml://./memory")
    .build_fastapi_app()
)
```

