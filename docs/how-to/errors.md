---
title: Error Handling (How‑To)
---

# Error Handling (How‑To)

Enhanced errors preserve YAML system context for fast diagnosis.

Common errors

- `YamlSystemError`: base class with system/agent/tool/session/user context
- `ToolExecutionError`: tool‑specific failure with type, timing, suggestions
- `ConfigurationError`: issues while loading/validating configuration
- `RegistryError`: agent/tool registry problems

Example

```python
from google_adk_extras.runners.errors import YamlSystemError, YamlSystemContext

ctx = YamlSystemContext(system_name="my_system", current_agent="root")
try:
    raise YamlSystemError("Something failed", context=ctx)
except YamlSystemError as e:
    print(e.get_debug_info())
```

Tips

- Prefer raising these errors in extensions for consistent UX.
- Log `get_debug_info()` in debug builds for rich context.

