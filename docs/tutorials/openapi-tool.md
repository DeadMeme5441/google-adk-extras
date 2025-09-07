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

