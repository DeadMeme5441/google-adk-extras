---
title: Configuration Reference
---

# Configuration Reference

## EnhancedRunConfig

YAML fields (selected):

- `streaming_mode`: ADK streaming mode (e.g., `NONE`)
- `max_llm_calls`: integer limit
- `tool_timeouts`: `{ mcp_tools, openapi_tools, function_tools, ... }`
- `retry_policies`: map of `{ name: { max_attempts, strategy, base_delay, ... } }`
- `a2a_config`: timeouts, retry, circuit breaker for A2A
- `enable_circuit_breaker`: boolean
- `enable_tool_registry` / `enable_agent_registry`: booleans
- `max_concurrent_tools`, `tool_execution_queue_size`
- `debug`: `{ enabled, trace_agent_flow, trace_tool_execution, performance_profiling, log_level }`

Example:

```yaml
max_llm_calls: 200
tool_timeouts:
  function_tools: 10.0
retry_policies:
  default:
    max_attempts: 3
debug:
  enabled: true
```

## RegistryConfig (Agent/Tool)

Common fields:

- `caching`: `{ enabled, default_ttl, cleanup_interval }`
- `health_monitoring`: `{ enabled, check_interval, failure_threshold, recovery_threshold }`
- `events`: `{ enabled, max_listeners, async_delivery }`
- `auto_startup`, `graceful_shutdown_timeout`

Tool registry extras:

- `strategy_fallback_chain`, `default_timeout`, `max_concurrent_executions`

