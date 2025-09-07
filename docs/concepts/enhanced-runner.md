---
title: Enhanced Runner
---

# Enhanced Runner

Drop‑in replacement for ADK’s Runner with YAML‑driven configuration, strategy‑based tool execution, metrics, and rich error context.

Core features

- `EnhancedRunConfig` complements ADK’s `RunConfig` with per‑tool timeouts, retries, circuit breaker, A2A, and debug controls.
- Tool strategies: MCP, OpenAPI, Function with configurable timeouts, retries, and optional circuit breaker.
- Rich errors (`YamlSystemError`, `ToolExecutionError`) include YAML system context: agent/tool/session/user.
- Optional registries integration: Agent and Tool registries add health checks, events, and caching.

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

Debugging & metrics

```python
runner.get_debug_info()            # configuration and strategy wiring
runner.get_performance_metrics()   # counters, latencies, failures per tool type
```

Error model

```python
from google_adk_extras.runners.errors import ToolExecutionError

try:
    # execute tools via strategies
    ...
except ToolExecutionError as e:
    print(e.error_code, e.suggested_fixes)
```

YAML mapping (selected)

- `tool_timeouts.openapi_tools` → OpenAPI strategy timeout
- `tool_timeouts.function_tools` → Function tool strategy timeout
- `retry_policies.openapi_tools` → RetryConfig for OpenAPI strategy
- `enable_circuit_breaker` + `circuit_breaker_config` → Wrap strategies with CB
