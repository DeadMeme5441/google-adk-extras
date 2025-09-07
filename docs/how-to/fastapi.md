---
title: FastAPI Integration (How‑To)
---

# FastAPI Integration (How‑To)

Expose agents via FastAPI using the enhanced app factory or the fluent builder. This page covers:

- Parameters and supported service URIs
- Adding custom credential services
- Enabling A2A, CORS, tracing, and hot reload
- Tips for local/dev vs production

```python
from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app

app = get_enhanced_fast_api_app(
    agents_dir="./agents",
    session_service_uri="sqlite:///sessions.db",      # SQL (via ADK DatabaseSessionService)
    artifact_service_uri="gs://my-bucket",             # GCS artifact store (ADK)
    memory_service_uri="agentengine://my-engine",      # Vertex memory bank or rag:// for RAG
    allow_origins=["*"],
    web=True,
    reload_agents=True,
)
```

Features

- Supports custom `credential_service` (OAuth2/JWT/Basic).
- A2A support (optional) and ADK dev builder endpoints.
- Integrates `EnhancedAdkWebServer` to return `EnhancedRunner` for each app.

With AdkBuilder

```python
from google_adk_extras import AdkBuilder
from google_adk_extras.credentials import JWTCredentialService

app = (
    AdkBuilder()
    .with_agents_dir("./agents")
    .with_session_service("postgresql://user:pass@localhost/db")
    .with_artifact_service("gs://my-bucket")
    .with_memory_service("redis://localhost:6379")
    .with_credential_service(JWTCredentialService(secret="supersecret", issuer="my-app"))
    .with_cors(["https://my.site"])
    .with_web_ui(True)
    .with_a2a_protocol(True)
    .with_agent_reload(True)
    .build_fastapi_app()
)
```

Parameters

- `agents_dir` or `agent_loader`: where your ADK agents live or a custom loader instance.
- `session_service_uri`: e.g., `sqlite:///...`, `postgresql://...`, `agentengine://...` (ADK patterns).
- `artifact_service_uri`: e.g., `gs://bucket` (ADK GCS).
- `memory_service_uri`: e.g., `rag://corpus`, `agentengine://...` (ADK memory services) or omit for in-memory.
- `credential_service`: pass a credential service instance from this package (Google/GitHub/Microsoft/X OAuth2, JWT, Basic) or use ADK’s in-memory.
- `allow_origins`: CORS list.
- `web`: serve ADK UI assets if available.
- `a2a`: mount Agent-to-Agent routes for each agent in `agents_dir`.
- `reload_agents`: watch-and-reload during development.
- `trace_to_cloud`: enable Cloud Trace (OpenTelemetry export) if env is configured.

Service URIs (cheatsheet)

- Sessions: `sqlite:///db.db`, `postgresql://...`, `mongodb://...`, `redis://...`
- Memory: `agentengine://id`, `rag://corpus` (ADK), or use in-memory by default
- Artifacts: `gs://bucket` (ADK GCS) or in-memory by default
- Credentials (via AdkBuilder URI or instances): see Reference → Service URI Cheatsheet

Custom credential services

```python
from google_adk_extras.credentials import GoogleOAuth2CredentialService

cred = GoogleOAuth2CredentialService(
    client_id="...apps.googleusercontent.com",
    client_secret="...",
    scopes=["openid", "email"],
)

app = get_enhanced_fast_api_app(
    agents_dir="./agents",
    credential_service=cred,
)
```

Run locally

```bash
uvicorn main:app --reload --port 8000
```

Production tips

- Run multiple Uvicorn workers or Gunicorn + Uvicorn workers for concurrency.
- Prefer managed databases and object storage (pooling, IAM, TLS).
- Set precise timeouts/retries/circuit breaker in `EnhancedRunConfig` (see Concepts → Enhanced Runner).
- Limit CORS to known origins; enforce HTTPS; rotate OAuth/JWT secrets.
