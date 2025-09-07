---
title: Registries
---

# Registries

Agent and Tool registries provide hot‑swapping, dynamic loading, health monitoring, caching, and events.

## Agent Registry

- Extends `CustomAgentLoader` with events/health/caching
- Hot‑swap agents with validation

```python
from google_adk_extras.runners.registry import EnhancedAgentRegistry

areg = EnhancedAgentRegistry()
areg.register_agent("chat", my_agent)
assert "chat" in areg.list_agents()
```

## Tool Registry

- Registers tools and toolsets; integrates with strategies
- Tracks usage, errors, health; supports auth detection

```python
from google_adk_extras.runners.registry import EnhancedToolRegistry
from google.adk.tools.function_tool import FunctionTool

async def hello_tool(ctx):
    return "hello"

treg = EnhancedToolRegistry()
await treg.register_function_tool("hello", hello_tool)
```

## Configuration

Pydantic models for registry behavior (caching, health intervals, fallback strategies). See Configuration Reference for fields and defaults.

