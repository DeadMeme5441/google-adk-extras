---
title: FastAPI Integration (How‑To)
---

# FastAPI Integration (How‑To)

Expose agents via FastAPI using the enhanced app factory.

```python
from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app
app = get_enhanced_fast_api_app(
  agents_dir="./agents",
  session_service_uri="sqlite:///sessions.db",
  artifact_service_uri="local://./artifacts",
  memory_service_uri="yaml://./memory",
  allow_origins=["*"],
  web=True,
  reload_agents=True,
)
```

Features

- Supports custom `credential_service` (OAuth2/JWT/Basic).
- A2A support (optional) and ADK dev builder endpoints.
- Integrates `EnhancedAdkWebServer` to return `EnhancedRunner` for each app.

