---
title: Tutorial — OpenAPI Tool + Circuit Breaker
---

# Tutorial: OpenAPI Tool with Retries and Circuit Breaker

Goal

- Register an OpenAPI tool and execute via a strategy with retries and circuit breaker.

Outline

1) Create an `OpenApiToolExecutionStrategy` with custom timeouts and retry config.
2) Register the strategy in a `ToolExecutionStrategyManager`.
3) Use a Tool Registry to register an API tool or toolset.
4) Execute the tool through the registry or via the runner.

Tip: Use the tool registry’s health and usage APIs to monitor behavior.

Code

```python
from google_adk_extras.runners import EnhancedRunner
from google_adk_extras.runners.config import EnhancedRunConfig
from google_adk_extras.runners.strategies import (
    ToolExecutionStrategyManager,
    OpenApiToolExecutionStrategy,
)
from google_adk_extras.runners.registry.tool_registry import ToolRegistry

# Strategy manager with tuned OpenAPI behavior
mgr = ToolExecutionStrategyManager()
mgr.register_strategy(
    "openapi",
    OpenApiToolExecutionStrategy(
        timeout=45.0,
        connection_timeout=10.0,
        retry_config=EnhancedRunConfig().get_retry_config("openapi_tools"),
    ),
)

# Create a tool registry and register an OpenAPI tool (pseudo-tool for illustration)
tool_registry = ToolRegistry()
await tool_registry.start()

class WeatherApiTool:
    """Pseudo OpenAPI tool. In practice, point at your client class wrapping an OpenAPI spec."""
    name = "weather_api"
    async def __call__(self, *, location: str) -> str:
        # Call your HTTP client here
        return "Sunny"

await tool_registry.register_tool("weather", WeatherApiTool())

# Runner configured to use the registry and strategy manager
runner = EnhancedRunner(
    app_name="tools_demo",
    agent=my_agent,  # an ADK agent that calls tools
    session_service=..., artifact_service=..., memory_service=..., credential_service=...,
)
runner.tool_registry = tool_registry
runner.tool_strategy_manager = mgr

# Now when the agent invokes the tool named "weather_api", the OpenAPI strategy applies
```

Config via YAML

```yaml
# Merge into EnhancedRunConfig
tool_timeouts:
  openapi_tools: 60.0
  function_tools: 10.0
retry_policies:
  openapi_tools:
    max_attempts: 3
    strategy: exponential_backoff
    base_delay: 0.5
enable_circuit_breaker: true
circuit_breaker_config:
  failure_threshold: 3
  recovery_timeout: 15.0
  success_threshold: 2
```

Notes

- Use longer timeouts for OpenAPI tools than function tools.
- Keep retries modest to avoid thundering herds; prefer exponential backoff with jitter.
- Circuit breaker helps when dependencies flap; monitor failure rates and recovery windows.
