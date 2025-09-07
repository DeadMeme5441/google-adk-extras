---
title: ADK Integration
---

# ADK Integration

ADK provides agents, tools, sessions/memory, and runtime configuration (RunConfig). This library does not replace those—it extends them.

Integration points

- Services: Drop‑in replacements for ADK’s session/memory/artifact services using SQL, Redis, MongoDB, S3/Local.
- Credentials: Plug credential services (OAuth2, JWT, Basic) into runners and the FastAPI server.
- Runner: `EnhancedRunner` augments ADK’s Runner with strategy‑driven tool execution and resilience.
- Config: `EnhancedRunConfig` complements `RunConfig` with per‑tool timeouts, retries, and circuit breakers.
- Server: `EnhancedAdkWebServer` and `get_enhanced_fast_api_app` wire ADK behavior into FastAPI, with proper credential handling.

Design goals

- Remain 100% compatible with core ADK concepts.
- Make production choices obvious: persistence, auth, retries, backoff, CB.
- Keep code‑first ergonomics (agents and strategies in code; config in YAML when helpful).

Links

- ADK Runtime config: https://raw.githubusercontent.com/google/adk-docs/main/docs/runtime/runconfig.md
- ADK Tools & OpenAPI: https://raw.githubusercontent.com/google/adk-docs/main/docs/tools/index.md
