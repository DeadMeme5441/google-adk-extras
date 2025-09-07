---
title: Configuration System
---

# Configuration System

Load runtime configuration from YAML/JSON/TOML/dicts/env/remote with interpolation and validation. This complements ADK’s `RunConfig` by allowing you to hydrate `EnhancedRunConfig` (timeouts/retries/CB) from external configuration.

```python
from google_adk_extras.configuration import ConfigurationSystem
from google_adk_extras.runners.config import EnhancedRunConfig

config_system = ConfigurationSystem()
result = config_system.load_config(EnhancedRunConfig, "config.yaml")
run_cfg = result.config
```

Environment interpolation supports:

- Shell style: `${VAR}`, with default `${VAR:default}`
- Python expressions: `${{ os.environ.get('X', 'fallback') }}`

Example YAML:

```yaml
services:
  session:
    type: sql
    connection_string: ${DATABASE_URL}
```

Validation

- Adapters return `validation_issues` with severity (error/warning/info)
- Strict mode can fail fast on errors; otherwise warn and continue
- Always validate untrusted input; prefer env and secret managers for credentials

Using with EnhancedRunConfig

```python
from google_adk_extras.configuration import ConfigurationSystem
from google_adk_extras.runners.config import EnhancedRunConfig

cfg = ConfigurationSystem().load_config(EnhancedRunConfig, {
  "tool_timeouts": {"openapi_tools": 60.0},
  "retry_policies": {"openapi_tools": {"max_attempts": 3, "strategy": "exponential_backoff"}},
  "enable_circuit_breaker": True,
})
runner_cfg = cfg.config
```
