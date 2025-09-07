---
title: Performance & Caching
---

# Performance & Caching

EnhancedRunner

- Control concurrency via `max_concurrent_tools`; monitor with `get_performance_metrics()`.
- Use retries judiciously; prefer idempotent operations.

Registries

- Enable caching with sensible TTLs for tool/agent lookups.
- Health checks add overhead; tune `check_interval`.

Backends

- Use production databases with pooling.
- Keep artifact IO off the hot path where possible.

