---
title: Quickstart (FastAPI)
---

# Quickstart: Enhanced FastAPI

Serve your agents with a FastAPI app that uses EnhancedRunner and supports custom credential services.

```python
from fastapi import FastAPI
from google.adk.cli.utils.agent_loader import AgentLoader

from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app
from google_adk_extras.credentials import GoogleOAuth2CredentialService

# Directory with your ADK agents (agent.json/root_agent.yaml)
agents_dir = "./agents"

# Optional: custom credential service (Google OAuth2 shown)
cred = GoogleOAuth2CredentialService(
    client_id="your-client-id",
    client_secret="your-client-secret",
    scopes=["openid", "email", "profile"]
)

app: FastAPI = get_enhanced_fast_api_app(
    agents_dir=agents_dir,
    session_service_uri="sqlite:///sessions.db",
    artifact_service_uri="local://./artifacts",
    memory_service_uri="yaml://./memory",
    credential_service=cred,
    allow_origins=["*"],
    web=True,
    a2a=False,
    reload_agents=True,
)
```

Run locally:

```bash
uvicorn my_app:app --reload
```

What this shows

- Enhanced FastAPI wiring that respects custom credential services
- Uses EnhancedAdkWebServer under the hood to return EnhancedRunner per app
- Same ADK routes + optional dev builder endpoints

