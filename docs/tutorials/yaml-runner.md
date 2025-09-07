---
title: Tutorial — YAML Runner Config
---

# Tutorial: YAML‑Driven Runner

Use `EnhancedRunConfig` loaded from YAML with environment interpolation.

Steps

1) Create `config.yaml` with runtime settings (timeouts, retries, debug).
2) Load with `ConfigurationSystem.load_config(EnhancedRunConfig, "config.yaml")`.
3) Pass `result.config` to `EnhancedRunner`.
4) Observe debug logs and error context on failures.

Example YAML

```yaml
streaming_mode: NONE
max_llm_calls: 200
tool_timeouts:
  function_tools: 10.0
  openapi_tools: 60.0
retry_policies:
  default:
    max_attempts: 3
debug:
  enabled: true
```

