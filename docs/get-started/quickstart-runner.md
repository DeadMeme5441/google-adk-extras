---
title: Quickstart (Runner)
---

# Quickstart: Enhanced Runner

Create and run an agent using the EnhancedRunner with services and credentials.

```python
from google.adk.agents.base_agent import BaseAgent
from google.genai import types

from google_adk_extras.runners import EnhancedRunner
from google_adk_extras.runners.config import EnhancedRunConfig
from google_adk_extras.runners.errors import YamlSystemContext
from google_adk_extras.sessions import SQLSessionService
from google_adk_extras.memory import SQLMemoryService
from google_adk_extras.artifacts import LocalFolderArtifactService
from google_adk_extras.credentials import JWTCredentialService

# Your agent (simplified example)
class EchoAgent(BaseAgent):
    async def _run_async_impl(self, *, user_id, session_id, new_message, state_delta=None, run_config=None):
        # Emit a single text reply
        yield types.Event(author="echo", content=types.Content(parts=[types.Part(text="Hello from EnhancedRunner!")]))

# Services
session_service = SQLSessionService("sqlite:///sessions.db")
memory_service = SQLMemoryService("sqlite:///memory.db")
artifact_service = LocalFolderArtifactService("./artifacts")
credential_service = JWTCredentialService(secret="supersecret")

# Enhanced config
config = EnhancedRunConfig.from_yaml_dict({
    "max_llm_calls": 100,
    "tool_timeouts": {"function_tools": 10.0},
    "retry_policies": {"default": {"max_attempts": 2}},
    "debug": {"enabled": True}
})

runner = EnhancedRunner(
    app_name="my_app",
    agent=EchoAgent(),
    session_service=session_service,
    artifact_service=artifact_service,
    memory_service=memory_service,
    credential_service=credential_service,
    enhanced_config=config,
    yaml_context=YamlSystemContext(system_name="demo")
)

# Run once
import asyncio
async def main():
    async for event in runner.run_async(
        user_id="u1",
        session_id="s1",
        new_message=types.Content(parts=[types.Part(text="Hi")])
    ):
        print(event)

asyncio.run(main())
```

What this shows

- Drop-in EnhancedRunner with services and credentials
- YAML-derived runtime config and debug context
- Async run producing ADK events

