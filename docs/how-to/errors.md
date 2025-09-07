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
    info = e.get_debug_info()
    print(info)

Surfacing errors from strategies

```python
from google_adk_extras.runners.strategies import ToolExecutionStrategyManager
from google_adk_extras.runners.errors import ToolExecutionError

mgr = ToolExecutionStrategyManager()
try:
    await mgr.execute_tool(tool, context, ctx)
except ToolExecutionError as e:
    # include suggested fixes and tool type
    print(e.error_code, e.suggested_fixes)
```
```

Tips

- Prefer raising these errors in extensions for consistent UX.
- Log `get_debug_info()` in debug builds for rich context.
- Include `YamlSystemContext` (system, agent, tool, session, user) to accelerate ops triage.
