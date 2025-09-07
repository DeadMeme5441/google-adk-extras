---
title: Enhanced Runner
---

# Enhanced Runner

Drop-in replacement for ADK’s Runner with YAML-driven configuration, tool strategies, and rich error context.

Core features

- `EnhancedRunConfig` extends ADK `RunConfig` (timeouts, retries, circuit breaker, A2A, debug)
- Tool execution strategies: MCP, OpenAPI, Function (timeouts + retries + optional CB)
- YAML system context in errors: agent/tool/session/user metadata for troubleshooting
- Registries integration (optional): Agent and Tool registries with health/events/caching

Create from YAML:

```python
from google_adk_extras.runners.config import EnhancedRunConfig

config = EnhancedRunConfig.from_yaml_dict({
  "streaming_mode": "NONE",
  "max_llm_calls": 200,
  "tool_timeouts": {"openapi_tools": 60.0, "function_tools": 10.0},
  "retry_policies": {"default": {"max_attempts": 3}},
  "debug": {"enabled": True}
})
```

Get debug info at runtime:

```python
runner.get_debug_info()
```

Errors include suggested fixes and YAML context (`YamlSystemError`, `ToolExecutionError`).

