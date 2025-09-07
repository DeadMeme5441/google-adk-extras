---
title: Quickstart (FastAPI)
---

# Quickstart: Enhanced FastAPI

Expose your ADK agents over FastAPI with custom services and credentials. Two ways are supported:

- Direct: `get_enhanced_fast_api_app` (closest to ADK’s original function)
- Fluent: `AdkBuilder` (compose services via URIs or instances)

Prerequisites

- Python 3.12+
- `pip install google-adk-extras uvicorn`
- Optional backends depending on what you wire up (e.g., SQLAlchemy, redis, pymongo, boto3)

Direct usage

```python
# main.py — Direct (enhanced) FastAPI app
from fastapi import FastAPI
from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app
from google_adk_extras.credentials import GoogleOAuth2CredentialService

cred = GoogleOAuth2CredentialService(
    client_id="...apps.googleusercontent.com",
    client_secret="...",
    scopes=["openid", "email", "profile"],
)

app: FastAPI = get_enhanced_fast_api_app(
    agents_dir="./agents",                  # Folder with ADK agents
    session_service_uri="sqlite:///sessions.db",
    artifact_service_uri="gs://my-bucket",  # or: local://./artifacts
    memory_service_uri="yaml://./memory",   # or: redis://..., mongodb://...
    credential_service=cred,                 # Optional custom credentials
    allow_origins=["*"],
    web=True,                                # Serve ADK web UI if assets available
    a2a=False,                               # Enable Agent-to-Agent protocol when needed
    reload_agents=True,                      # Hot reload during dev
)

# Run: uvicorn main:app --reload
```

AdkBuilder approach

```python
# app_builder.py — Fluent builder
from google_adk_extras import AdkBuilder
from google_adk_extras.credentials import GoogleOAuth2CredentialService

app = (
    AdkBuilder()
    .with_agents_dir("./agents")
    .with_session_service("sqlite:///sessions.db")
    .with_artifact_service("gs://my-bucket")         # or local://, s3://, sql://, mongodb://
    .with_memory_service("yaml://./memory")
    .with_credential_service(GoogleOAuth2CredentialService(
        client_id="...apps.googleusercontent.com",
        client_secret="...",
        scopes=["openid", "email", "profile"],
    ))
    .with_web_ui(True)
    .with_agent_reload(True)
    .build_fastapi_app()
)

# Run: uvicorn app_builder:app --reload
```

Agents directory

- Create `./agents/<app_name>/agent.json` to register an agent with ADK’s loader, or use `AdkBuilder.with_agent_instance(...)` to avoid a filesystem layout for prototypes.

Enable A2A (optional)

```python
app = get_enhanced_fast_api_app(
    agents_dir="./agents",
    a2a=True,  # mounts A2A routes per agent in the directory
)
```

What you get

- Enhanced FastAPI wiring that respects custom credential services
- Uses `EnhancedAdkWebServer` under the hood to return `EnhancedRunner`
- Same ADK routes + optional dev builder endpoints and (optionally) A2A
