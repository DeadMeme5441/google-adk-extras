---
title: Performance & Caching
---

# Performance & Caching

EnhancedRunner

- Control concurrency via `max_concurrent_tools`; monitor with `get_performance_metrics()`.
- Prefer idempotent tool operations when enabling retries/backoff.
- Avoid synchronous I/O in tool execution; keep tools async.

Registries

- Enable caching with sensible TTLs for tool/agent lookups.
- Health checks add overhead; tune `check_interval`.
- Defer expensive health probes to background tasks.

Backends

- Use production databases with pooling.
- Keep artifact IO off the hot path where possible.
- Size Redis memory and persistence (AOF/RDB) to your workload.
