---
title: Registries
---

# Registries

Agent and Tool registries provide hot‑swapping, dynamic loading, health monitoring, caching, and events. Use them for long‑running processes where you need to update logic without restarts.

## Agent Registry

- Extends loader behavior with events/health/caching
- Hot‑swap agents with validation and graceful handoff

```python
from google_adk_extras.runners.registry import EnhancedAgentRegistry

areg = EnhancedAgentRegistry()
areg.register_agent("chat", my_agent)
assert "chat" in areg.list_agents()
```

## Tool Registry

- Registers tools and toolsets; integrates with strategy manager
- Tracks usage, errors, and health; supports auth detection and fallbacks

```python
from google_adk_extras.runners.registry import EnhancedToolRegistry
from google.adk.tools.function_tool import FunctionTool

async def hello_tool(ctx):
    return "hello"

treg = EnhancedToolRegistry()
await treg.register_function_tool("hello", hello_tool)
```

## Configuration

Pydantic models expose:

- `caching`: enabled, default TTL, cleanup interval
- `health_monitoring`: enabled, check interval, failure/recovery thresholds
- `events`: delivery mode, listener limits

Tune health intervals for your environment. High‑frequency checks add overhead.
