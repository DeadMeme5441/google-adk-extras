---
title: Configuration System
---

# Configuration System

Load runtime configuration from YAML/JSON/TOML/dicts/env/remote with interpolation and validation.

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

- Adapter returns `validation_issues` with severity (error/warning/info)
- Strict mode can fail fast on errors

