---
title: Tutorial — YAML Runner Config
---

# Tutorial: YAML‑Driven Runner

Drive timeouts, retries, circuit breaker, and debug without changing code using `EnhancedRunConfig` loaded from YAML.

Example config

```yaml
# run.yaml
max_llm_calls: 200
tool_timeouts:
  function_tools: 10.0
  openapi_tools: 60.0
retry_policies:
  default:
    max_attempts: 3
    strategy: exponential_backoff
    base_delay: 0.5
  mcp_tools:
    max_attempts: 3
  openapi_tools:
    max_attempts: 3
enable_circuit_breaker: true
circuit_breaker_config:
  failure_threshold: 3
  recovery_timeout: 15.0
  success_threshold: 2
debug:
  enabled: true
  trace_agent_flow: true
```

Load and use

```python
from google_adk_extras.runners.config import EnhancedRunConfig
from google_adk_extras.runners import EnhancedRunner
from google_adk_extras.sessions import SQLSessionService
from google_adk_extras.memory import SQLMemoryService
from google_adk_extras.artifacts import LocalFolderArtifactService

# Services
session_service = SQLSessionService("sqlite:///sessions.db")
memory_service = SQLMemoryService("sqlite:///memory.db")
artifact_service = LocalFolderArtifactService("./artifacts")

# Load YAML config
import yaml
with open("run.yaml", "r") as f:
    yaml_cfg = yaml.safe_load(f)
config = EnhancedRunConfig.from_yaml_dict(yaml_cfg)

# Create runner
from google.adk.agents.base_agent import BaseAgent
from google.genai import types

class Echo(BaseAgent):
    async def _run_async_impl(self, *, user_id, session_id, new_message, state_delta=None, run_config=None):
        yield types.Event(author="echo", content=types.Content(parts=[types.Part(text="Hello!")]))

runner = EnhancedRunner(
    app_name="yaml_demo",
    agent=Echo(),
    session_service=session_service,
    artifact_service=artifact_service,
    memory_service=memory_service,
    enhanced_config=config,
)

# Run
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

Tips

- Keep retry policies idempotent (e.g., reads or safe POSTs) when possible.
- Use longer timeouts for OpenAPI tools than function tools.
- Enable circuit breaker only for external services that might flap.
