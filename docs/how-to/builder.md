---
title: AdkBuilder (How‑To)
---

# AdkBuilder (How‑To)

Fluent builder to assemble services, agent loader/instances, and build a FastAPI app or Runner.

```python
from google_adk_extras import AdkBuilder
from google_adk_extras.credentials import GoogleOAuth2CredentialService

app = (
  AdkBuilder()
  .with_agents_dir("./agents")
  .with_session_service("sqlite:///sessions.db")
  .with_artifact_service("local://./artifacts")
  .with_memory_service("yaml://./memory")
  .with_credential_service(GoogleOAuth2CredentialService(
      client_id="...", client_secret="...", scopes=["openid", "email"]
  ))
  .with_web_ui(True)
  .with_agent_reload(True)
  .build_fastapi_app()
)
```

Notes

- URIs vs instances: use URIs for simple wiring, or pass pre‑built instances for advanced control.
- Programmatic agent insertion: `with_agent_instance(name, agent)` or `with_agents({..})`.

