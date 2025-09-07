---
title: Tutorial — Observability
---

# Tutorial: Observability

Make your deployment observable.

Topics

- Registries: health monitoring, events, cache stats
- Runner: performance metrics and debug info
- Tracing: enable Cloud Trace via `trace_to_cloud=True` in FastAPI app

Snippets

```python
metrics = runner.get_performance_metrics()
print(metrics)

stats = tool_registry.get_registry_stats()
print(stats)
```

Add logging, structured logs, and traces as needed for your environment.

