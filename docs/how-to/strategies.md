---
title: Tool Strategies (How‑To)
---

# Tool Strategies (How‑To)

Configure execution strategies for MCP, OpenAPI, and function tools.

```python
from google_adk_extras.runners.strategies import (
  ToolExecutionStrategyManager,
  McpToolExecutionStrategy,
  OpenApiToolExecutionStrategy,
  FunctionToolExecutionStrategy,
)

mgr = ToolExecutionStrategyManager()
mgr.register_strategy("mcp", McpToolExecutionStrategy(timeout=45.0))
mgr.register_strategy("openapi", OpenApiToolExecutionStrategy(timeout=60.0))
mgr.register_strategy("function", FunctionToolExecutionStrategy(timeout=10.0))
```

Pass the manager to `EnhancedRunner` or let it create defaults from `EnhancedRunConfig`.

Retries & Circuit Breaker

- Each strategy supports per‑type timeouts and retry policies; CB is optional and recommended for external APIs.

