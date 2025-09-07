---
title: Using With Google ADK
---

# Using With Google ADK

This library is an extension on top of Google ADK. It keeps ADK’s mental model (agents, tools, sessions, memory, RunConfig) and adds production‑oriented pieces:

- Pluggable service backends (SQL, Redis, MongoDB, S3/Local) for sessions, memory, artifacts
- Credential services (OAuth2 providers, JWT, Basic) that plug into ADK flows
- EnhancedRunner and strategies (timeouts, retries, circuit breaker)
- Enhanced FastAPI integration for serving agents cleanly

ADK documentation

- Get Started: https://raw.githubusercontent.com/google/adk-docs/main/docs/get-started/index.md
- Runtime config (RunConfig): https://raw.githubusercontent.com/google/adk-docs/main/docs/runtime/runconfig.md
- Sessions & Memory: https://raw.githubusercontent.com/google/adk-docs/main/docs/sessions/index.md
- Tools (OpenAPI): https://raw.githubusercontent.com/google/adk-docs/main/docs/tools/openapi-tools.md

Where this library plugs in

- Services: swap ADK’s in‑memory defaults for persistent backends.
- Credentials: add a `credential_service` to your runner or FastAPI app.
- Runner config: layer EnhancedRunConfig on top of ADK’s RunConfig.
- Server: use `get_enhanced_fast_api_app` or `AdkBuilder` instead of CLI‑only flows.

Cheat sheet

- ADK dev UI: `adk web` → our FastAPI app also serves the UI if the assets are present.
- ADK API server: `adk api_server` → our FastAPI app is the programmable equivalent.
- ADK OpenAPI tools: define tools per ADK docs → our strategies add retries/CB/timeouts.
